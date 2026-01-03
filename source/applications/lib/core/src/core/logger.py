import threading
import importlib.util

from typing import Callable
from opentelemetry import trace
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor, LogExporter
from core.singelton import BaseSingleton
from opentelemetry.sdk.trace import SpanProcessor, TracerProvider
from pydantic import BaseModel
from opentelemetry.sdk.resources import SERVICE_NAME, SERVICE_VERSION, Resource
from opentelemetry.sdk.trace.export import BatchSpanProcessor
import logging

from opentelemetry._logs import set_logger_provider
from opentelemetry import metrics

from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter

from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler

from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    MetricReader,
    PeriodicExportingMetricReader,
)
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

logger = logging.getLogger(__name__)


class ColorFormatter(logging.Formatter):
    COLORS = {
        "DEBUG": "\033[94m",
        "INFO": "\033[92m",
        "WARNING": "\033[93m",
        "ERROR": "\033[91m",
        "CRITICAL": "\033[1;91m",
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord):
        level_color = self.COLORS.get(
            record.levelname.replace(self.RESET, ""), self.RESET
        )
        record.levelname = f"{level_color}{record.levelname}{self.RESET}"

        # Append trace/span ID if available
        if hasattr(record, "trace_id") and record.trace_id:
            record.msg = (
                f"{record.msg} [trace_id={record.trace_id} span_id={record.span_id}]"
            )

        return super().format(record)


class OpenTelemetryLogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord):
        span = trace.get_current_span()
        context = span.get_span_context()
        if context and context.is_valid:
            record.trace_id = f"{context.trace_id:032x}"
            record.span_id = f"{context.span_id:016x}"
        else:
            record.trace_id = None
            record.span_id = None
        return True


class OTELConfig(BaseModel):
    title: str
    version: str
    otel_host: str
    otel_metric_host: str
    otel_log_host: str
    insecure: bool


LoggingFunctions = Callable[[str, OTELConfig | None], None]


class OTELProvider(BaseSingleton):

    """
    OpenTelemetry singleton that configures tracing, metrics and logging for the
    whole application.

    • **Singleton** – only one instance is created (protected by a thread lock).
    • **Resource** – built from the supplied ``OTELConfig`` (service name & version).
    • **Logging** – ``LoggerProvider`` with an OTLP exporter, attached to the root
      ``logging`` logger.
    • **Metrics** – ``MeterProvider`` with a periodic OTLP metric exporter.
    • **Tracing** – ``TracerProvider`` with a batch OTLP span exporter.
    • **Auto‑instrumentation** – for each optional dependency listed in
      ``INSTRUMENTORS`` the corresponding OpenTelemetry instrumentor is imported
      and ``instrument()`` is called; missing packages are silently skipped.

    **Supported libraries for auto‑instrumentation**

    - ``httpx``
    - ``requests``
    - ``ollama``
    - ``qdrant_client``
    - ``openai``
    - ``llama_index``
    - ``sqlalchemy``
    """


    trace_provider: TracerProvider
    log_provider: LoggerProvider
    meter_provider: MeterProvider

    log_export: LogExporter
    service_name: str

    span_processor: SpanProcessor
    reader: MetricReader

    def _init_once(self, config: OTELConfig):
        self.service_name = config.title
        self.resource = Resource.create(
            {SERVICE_NAME: config.title, SERVICE_VERSION: config.version}
        )

        # --- Logging
        self.log_provider = LoggerProvider(resource=self.resource)
        self.log_exporter = OTLPLogExporter(
            endpoint=config.otel_log_host, insecure=config.insecure
        )
        self.log_provider.add_log_record_processor(
            BatchLogRecordProcessor(self.log_exporter)
        )
        self.handler = LoggingHandler(logger_provider=self.log_provider)
        logging.getLogger().addHandler(self.handler)
        set_logger_provider(self.log_provider)

        # --- Metrics
        self.reader = PeriodicExportingMetricReader(
            OTLPMetricExporter(
                endpoint=config.otel_metric_host, insecure=config.insecure
            )
        )
        self.meter_provider = MeterProvider(
            resource=self.resource, metric_readers=[self.reader]
        )
        metrics.set_meter_provider(self.meter_provider)

        # --- Trace
        self.trace_provider = TracerProvider(resource=self.resource)
        self.span_processor = BatchSpanProcessor(
            OTLPSpanExporter(endpoint=config.otel_host, insecure=config.insecure)
        )
        self.trace_provider.add_span_processor(self.span_processor)
        trace.set_tracer_provider(self.trace_provider)
        # (target dependency, instrumentor module, instrumentor class)
        INSTRUMENTORS = [
            ("httpx", "opentelemetry.instrumentation.httpx", "HTTPXClientInstrumentor"),
            (
                "requests",
                "opentelemetry.instrumentation.requests",
                "RequestsInstrumentor",
            ),
            ("ollama", "opentelemetry.instrumentation.ollama", "OllamaInstrumentor"),
            (
                "qdrant_client",
                "opentelemetry.instrumentation.qdrant",
                "QdrantInstrumentor",
            ),
            ("openai", "opentelemetry.instrumentation.openai", "OpenAIInstrumentor"),
            (
                "llama_index",
                "opentelemetry.instrumentation.llama_index",
                "LlamaIndexInstrumentor",
            ),
            (
                "sqlalchemy",
                "opentelemetry.instrumentation.sqlalchemy",
                "SQLAlchemyInstrumentor",
            ),
        ]

        for dep_name, instr_mod_path, instr_cls_name in INSTRUMENTORS:
            if importlib.util.find_spec(dep_name) is None:
                logger.info(
                    "Skipping instrumentation for %s (dependency missing)", dep_name
                )
                continue
            try:
                instr_mod = importlib.import_module(instr_mod_path)
            except ImportError:
                logger.info(
                    "Skipping instrumentation for %s (instrumentor package '%s' missing)",
                    dep_name,
                    instr_mod_path,
                )
                continue
            try:
                getattr(instr_mod, instr_cls_name)().instrument()
                logger.debug("Instrumentation for %s succeeded", dep_name)
            except Exception:
                logger.warning("Instrumentation for %s failed", dep_name)


def init_logging(
    log_level: str = "INFO",
    config: OTELConfig | None = None,
    logger_additions: list[LoggingFunctions] = [],
):

    if config:
        OTELProvider.create(config)

    # Set up logger
    handler = logging.StreamHandler()
    handler.setFormatter(
        ColorFormatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    if config:
        handler.addFilter(OpenTelemetryLogFilter())

    logger = logging.getLogger()
    logger.setLevel(log_level.upper())
    logger.addHandler(handler)
    logger.debug("Colored logging with OpenTelemetry context initialized")
    for logger_addition in logger_additions:
        logger_addition(log_level, config)


def disable_local_logging():
    root_logger = logging.getLogger()
    for h in list(root_logger.handlers):
        if isinstance(h, logging.StreamHandler) and isinstance(
            h.formatter, ColorFormatter
        ):
            root_logger.removeHandler(h)
