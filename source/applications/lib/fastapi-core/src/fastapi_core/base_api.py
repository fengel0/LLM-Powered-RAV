from abc import ABC, abstractmethod

import logging


from fastapi import FastAPI, Request

from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from opentelemetry.instrumentation.asgi import OpenTelemetryMiddleware
from opentelemetry import trace

from prometheus_fastapi_instrumentator import Instrumentator

# from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.cors import CORSMiddleware


from core.model import NotFoundException

from pydantic import BaseModel
from starlette.responses import JSONResponse
from starlette.types import StatefulLifespan, StatelessLifespan

# from util import PrometheusMiddleware
from fastapi_core.util import PrometheusOTLPMiddleware

logger = logging.getLogger(__name__)


class HealthState(BaseModel):
    status: str
    title: str
    version: str


class OTELConfig(BaseModel):
    otel_host: str
    otel_metric_host: str
    otel_log_host: str
    insecure: bool


class CorsConfig(BaseModel):
    allow_credentials: bool = False
    allow_origins: list[str] = ["*"]
    allow_methods: list[str] = ["*"]
    allow_headers: list[str] = ["*"]


Lifespan = StatefulLifespan[FastAPI] | StatelessLifespan[FastAPI]


class BaseAPI(ABC):
    title: str
    version: str
    app: FastAPI
    cors_app: CORSMiddleware
    root_path: str
    tracer: trace.Tracer

    def __init__(
        self,
        title: str,
        version: str,
        cors_config: CorsConfig = CorsConfig(),
        lifespan: Lifespan | None = None,
        root_path: str = "",
    ):
        self.tracer = trace.get_tracer(f"API-{title}-{version}")
        self.root_path = root_path
        with self.tracer.start_as_current_span("app-start-up"):
            self.title = title
            self.version = version
            self.app = FastAPI(
                title=title, version=version, lifespan=lifespan, root_path=root_path
            )
            self._register_metrics()
            self._register_health_endpoint()
            self._register_api_paths()
            self._register_error_handling()
            self.cors_app = CORSMiddleware(
                app=self.app,
                allow_origins=cors_config.allow_origins,
                allow_credentials=cors_config.allow_credentials,
                allow_methods=cors_config.allow_methods,
                allow_headers=cors_config.allow_headers,
            )
            # self.app.add_middleware()
            logger.info(f"started service {self.title} with version {self.version}")

    @abstractmethod
    def _register_api_paths(self): ...

    def _register_health_endpoint(self):
        @self.app.get("/health", summary="Health Check")
        async def health() -> HealthState:  # type: ignore
            return HealthState(status="ok", title=self.title, version=self.version)

    def _register_metrics(self):
        self.prometheus = Instrumentator()
        self.prometheus.instrument(self.app).expose(self.app, endpoint="/metrics")
        self.app.add_middleware(PrometheusOTLPMiddleware, app_name=self.title)
        self.app.add_middleware(OpenTelemetryMiddleware)
        # self.app.add_route("/metrics", metrics)
        FastAPIInstrumentor.instrument_app(self.app)

    def _register_error_handling(self):
        @self.app.exception_handler(Exception)
        async def global_err_handler(request: Request, exc: Exception):
            """Translate common Python errors into HTTP responses."""
            if isinstance(exc, ValueError):
                status, detail = 400, f"Invalid input: {exc}"
            elif isinstance(exc, KeyError):
                status, detail = 400, f"Missing key: {exc}"
            elif isinstance(exc, NotFoundException):
                status, detail = 404, str(exc)
            elif isinstance(exc, PermissionError):
                status, detail = 403, f"Permission denied: {exc}"
            else:
                # Log unexpected errors; don't leak details to the client
                logger.exception("Unhandled server error", exc_info=exc)
                status, detail = 500, "Internal server error"
                request.headers

            resp = JSONResponse(status_code=status, content={"detail": detail})
            return resp

    def get_app(self) -> FastAPI | CORSMiddleware:
        return self.cors_app
