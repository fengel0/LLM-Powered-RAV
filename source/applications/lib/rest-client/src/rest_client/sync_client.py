import requests
import time
from typing import Optional, Any
from opentelemetry import trace
from opentelemetry.propagate import inject
from opentelemetry.trace import set_span_in_context, Status, StatusCode
from core.result import Result
from domain.http_client.model import HttpResponse
from domain.http_client.sync_client import SyncHttpClient

from opentelemetry import metrics


class OTELSyncHTTPClient(SyncHttpClient):
    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout
        self.tracer = trace.get_tracer("OTELSyncHTTPClient")
        meter = metrics.get_meter("otel_http_client")

        self.request_duration_histogram = meter.create_histogram(
            name="http.client.request.duration",
            unit="s",
            description="Duration of HTTP client requests",
        )

    def _request(
        self,
        method: str,
        url: str,
        header: dict[str, str],
        json: Optional[dict[str, Any]] = None,
    ) -> Result[HttpResponse]:
        headers = header.copy()
        with self.tracer.start_as_current_span(f"http.{method.lower()} {url}") as span:
            context = set_span_in_context(span)
            inject(headers, context=context)
            start = time.time()

            try:
                response = requests.request(
                    method=method.upper(),
                    url=url,
                    json=json,
                    headers=headers,
                    timeout=self.timeout,
                )
                duration = time.time() - start
                self.request_duration_histogram.record(
                    duration,
                    {
                        "http.method": method.upper(),
                        "http.status_code": response.status_code,
                        "http.url": url,
                    },
                )

                try:
                    body = response.json()
                except ValueError:
                    body = response.text

                return Result.Ok(
                    HttpResponse(
                        status_code=response.status_code,
                        headers=dict(response.headers),
                        body=body,
                    )
                )

            except requests.RequestException as e:
                duration = time.time() - start
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                self.request_duration_histogram.record(
                    duration,
                    {
                        "http.method": method.upper(),
                        "http.status_code": getattr(e.response, "status_code", 0),
                        "http.url": url,
                        "error": "true",
                    },
                )
                return Result.Err(e)

    def get(self, url: str, header: dict[str, str]) -> Result[HttpResponse]:
        return self._request("GET", url, header)

    def post(
        self, url: str, header: dict[str, str], json: Optional[dict[str, Any]] = None
    ) -> Result[HttpResponse]:
        return self._request("POST", url, header, json)

    def put(
        self, url: str, header: dict[str, str], json: Optional[dict[str, Any]] = None
    ) -> Result[HttpResponse]:
        return self._request("PUT", url, header, json)

    def delete(self, url: str, header: dict[str, str]) -> Result[HttpResponse]:
        return self._request("DELETE", url, header)
