from sys import api_version
from traceloop.sdk import Traceloop
from core.logger import OTELConfig, OTELProvider


def llama_index_logging(log_level: str, config: OTELConfig | None):
    if config:
        otel_provider = OTELProvider.Instance()
        Traceloop.init(
            app_name=otel_provider.service_name,
            api_endpoint=config.otel_host,
            logging_exporter=otel_provider.log_exporter,
        )
