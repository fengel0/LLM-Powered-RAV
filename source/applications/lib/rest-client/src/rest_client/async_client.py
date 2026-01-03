import logging
import httpx
import time
from typing import AsyncGenerator, Optional, Any
from opentelemetry import trace
from opentelemetry.propagate import inject
from opentelemetry.trace import set_span_in_context, Status, StatusCode
from core.result import Result
from domain.http_client.model import HttpResponse
from domain.http_client.async_client import AsyncHttpClient
from opentelemetry import metrics

logger = logging.getLogger(__name__)


class OTELAsyncHTTPClient(AsyncHttpClient):
    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout
        self.tracer = trace.get_tracer("OTELAsyncHTTPClient")
        meter = metrics.get_meter("otel_http_client")

        self.request_duration_histogram = meter.create_histogram(
            name="http.client.request.duration",
            unit="s",
            description="Duration of HTTP client requests",
        )

    async def _request(
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

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                try:
                    response = await client.request(
                        method=method.upper(),
                        url=url,
                        headers=headers,
                        json=json,
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

                except httpx.RequestError as e:
                    logger.error(e, exc_info=True)
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

    async def get(self, url: str, header: dict[str, str]) -> Result[HttpResponse]:
        return await self._request("GET", url, header)

    async def post(
        self, url: str, header: dict[str, str], json: Optional[dict[str, Any]] = None
    ) -> Result[HttpResponse]:
        return await self._request("POST", url, header, json)

    async def put(
        self, url: str, header: dict[str, str], json: Optional[dict[str, Any]] = None
    ) -> Result[HttpResponse]:
        return await self._request("PUT", url, header, json)

    async def delete(self, url: str, header: dict[str, str]) -> Result[HttpResponse]:
        return await self._request("DELETE", url, header)

    async def stream(
        self, url: str, header: dict[str, str], json: dict[str, Any] | None = None
    ) -> Result[AsyncGenerator[str, None]]:
        """
        Open a streaming HTTP request and yield text chunks as they arrive.

        - Uses POST when a JSON payload is provided, otherwise GET.
        - Keeps the connection and span alive for the whole iteration.
        - Records a single duration metric for the entire stream.
        - Raises exceptions during iteration so callers can handle retries upstream.
        """
        method = "POST" if json is not None else "GET"
        base_headers = header.copy()

        async def _gen() -> AsyncGenerator[str, None]:
            # Start span when the stream actually begins, so timing is accurate.
            with self.tracer.start_as_current_span(
                f"http.stream {method.lower()} {url}"
            ) as span:
                context = set_span_in_context(span)
                inject(base_headers, context=context)
                start = time.time()

                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    try:
                        async with client.stream(
                            method=method,
                            url=url,
                            headers=base_headers,
                            json=json,
                        ) as response:
                            # Set standard HTTP attributes
                            span.set_attribute("http.method", method)
                            span.set_attribute("http.url", url)
                            span.set_attribute("http.status_code", response.status_code)

                            # Fail fast on non-2xx
                            response.raise_for_status()

                            # Stream text chunks; upstream can do its own line/JSON buffering.
                            async for chunk in response.aiter_text():
                                if chunk:
                                    yield chunk

                            # End-of-stream: record total duration
                            duration = time.time() - start
                            self.request_duration_histogram.record(
                                duration,
                                {
                                    "http.method": method,
                                    "http.status_code": response.status_code,
                                    "http.url": url,
                                },
                            )

                    except Exception as e:
                        duration = time.time() - start
                        span.record_exception(e)
                        span.set_status(Status(StatusCode.ERROR, str(e)))
                        self.request_duration_histogram.record(
                            duration,
                            {
                                "http.method": method,
                                "http.status_code": getattr(
                                    getattr(e, "response", None), "status_code", 0
                                ),
                                "http.url": url,
                                "error": "true",
                            },
                        )
                        # Surface the error to the caller consuming the generator
                        raise

        return Result.Ok(_gen())
