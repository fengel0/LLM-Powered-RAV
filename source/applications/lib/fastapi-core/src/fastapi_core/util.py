import time
from typing import Tuple, Iterable

from opentelemetry import metrics, trace
from opentelemetry.trace import set_span_in_context
from opentelemetry.metrics import Observation
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Match
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR
from starlette.types import ASGIApp

from prometheus_client import REGISTRY, Counter, Gauge, Histogram
from prometheus_client.openmetrics.exposition import (
    CONTENT_TYPE_LATEST,
    generate_latest,
)

# ---------------------------------------------------------------------------
# Prometheus client metrics (unchanged, still exposed at /metrics)
# ---------------------------------------------------------------------------
INFO = Gauge("fastapi_app_info", "FastAPI application information.", ["app_name"])
REQUESTS = Counter(
    "fastapi_requests_total",
    "Total count of requests by method and path.",
    ["method", "path", "app_name"],
)
RESPONSES = Counter(
    "fastapi_responses_total",
    "Total count of responses by method, path and status codes.",
    ["method", "path", "status_code", "app_name"],
)
REQUESTS_PROCESSING_TIME = Histogram(
    "fastapi_requests_duration_seconds",
    "Histogram of requests processing time by path (in seconds)",
    ["method", "path", "app_name"],
)
EXCEPTIONS = Counter(
    "fastapi_exceptions_total",
    "Total count of exceptions raised by path and exception type",
    ["method", "path", "exception_type", "app_name"],
)
REQUESTS_IN_PROGRESS = Gauge(
    "fastapi_requests_in_progress",
    "Gauge of requests by method and path currently being processed",
    ["method", "path", "app_name"],
)


# ---------------------------------------------------------------------------
# Middleware that mirrors the Prometheus metrics into OpenTelemetry metrics
# ---------------------------------------------------------------------------
class PrometheusOTLPMiddleware(BaseHTTPMiddleware):
    """Middleware that updates Prometheus *and* records equivalent
    OpenTelemetry metrics using the **same** attribute/label names.

    In addition to request/response metrics, this version also exposes the
    constant *fastapi_app_info* metric through OTel via an ObservableGauge.
    """

    def __init__(self, app: ASGIApp, app_name: str = "fastapi-app") -> None:
        super().__init__(app)
        self.app_name = app_name

        # Prometheus one‑shot app info gauge
        INFO.labels(app_name=self.app_name).inc()

        # ------------------------------------------------------------
        # OpenTelemetry instruments mirroring the Prometheus ones
        # ------------------------------------------------------------
        meter = metrics.get_meter(app_name)

        # Constant app info gauge via ObservableGauge
        self._info_attrs = {"app_name": self.app_name}

        def _info_callback(_: metrics.CallbackOptions) -> Iterable[Observation]:  # noqa: D401,E501
            return [Observation(1, self._info_attrs)]

        meter.create_observable_gauge(
            name="fastapi_app_info",
            description="FastAPI application information.",
            unit="1",
            callbacks=[_info_callback],
        )

        # Requests counters / histograms / etc.
        self.req_counter = meter.create_counter(
            name="fastapi_requests_total",
            description="Total count of requests by method and path.",
            unit="1",
        )
        self.resp_counter = meter.create_counter(
            name="fastapi_responses_total",
            description="Total count of responses by method, path and status codes.",
            unit="1",
        )
        self.latency_hist = meter.create_histogram(
            name="fastapi_requests_duration_seconds",
            description="Histogram of requests processing time by path (in seconds)",
            unit="s",
        )
        self.in_flight = meter.create_up_down_counter(
            name="fastapi_requests_in_progress",
            description="Gauge of requests currently being processed",
            unit="1",
        )
        self.exc_counter = meter.create_counter(
            name="fastapi_exceptions_total",
            description="Total count of exceptions raised by path and exception type",
            unit="1",
        )

    # ---------------------------------------------------------------------
    # Request lifecycle
    # ---------------------------------------------------------------------
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        method = request.method
        path, handled = self._matched_path(request)

        if not handled:
            return await call_next(request)

        attrs = {"method": method, "path": path, "app_name": self.app_name}

        # ── in‑flight tracking ────────────────────────────────────────────
        REQUESTS_IN_PROGRESS.labels(**attrs).inc()
        self.in_flight.add(1, attrs)

        REQUESTS.labels(**attrs).inc()
        self.req_counter.add(1, attrs)

        start = time.perf_counter()

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception as exc:
            status_code = HTTP_500_INTERNAL_SERVER_ERROR
            exc_attrs = attrs | {"exception_type": type(exc).__name__}
            EXCEPTIONS.labels(**exc_attrs).inc()
            self.exc_counter.add(1, exc_attrs)
            raise
        finally:
            duration = time.perf_counter() - start

            # Capture current span context for exemplar
            span = trace.get_current_span()
            span_ctx = set_span_in_context(span)

            # Prometheus histogram with manual exemplar
            REQUESTS_PROCESSING_TIME.labels(**attrs).observe(
                duration,
                exemplar={
                    "TraceID": trace.format_trace_id(span.get_span_context().trace_id)
                },
            )

            # OpenTelemetry histogram – exemplar attached automatically via context
            self.latency_hist.record(duration, attrs, context=span_ctx)

            resp_attrs = attrs | {"status_code": status_code}
            RESPONSES.labels(**resp_attrs).inc()
            self.resp_counter.add(1, resp_attrs)

            REQUESTS_IN_PROGRESS.labels(**attrs).dec()
            self.in_flight.add(-1, attrs)

    # ---------------------------------------------------------------------
    # Helper to map concrete path to templated route (/users/42 → /users/{id})
    # ---------------------------------------------------------------------
    @staticmethod
    def _matched_path(request: Request) -> Tuple[str, bool]:
        for route in request.app.routes:
            match, _ = route.matches(request.scope)
            if match is Match.FULL:
                return route.path, True
        return request.url.path, False


# ----------------------------------------------------------------------------
# /metrics endpoint for Prometheus scraping (unchanged)
# ----------------------------------------------------------------------------


def metrics_endpoint(_: Request) -> Response:  # noqa: D401
    """Return Prometheus/OpenMetrics text format for scraping."""
    return Response(
        generate_latest(REGISTRY), headers={"Content-Type": CONTENT_TYPE_LATEST}
    )

