import unittest
from typing import Any, List

from domain_test.file_converter.client_test import TestFileConverterServiceClient
from core.result import Result
from domain.http_client.model import HttpResponse
from domain.http_client.async_client import AsyncHttpClient
from file_converter_client.async_client import (
    FileConverterServiceClientImpl,
    FileConverterConfig,
)

# ---------------------------------------------------------------------------
# Mock HTTP clients
# ---------------------------------------------------------------------------


class MockSuccessHttpClient(AsyncHttpClient):
    """Return a well‑formed response body that matches the latest DTOs."""

    async def put(  # type: ignore[override]
        self,
        url: str,
        header: dict[str, str],
        json: dict[str, Any] | None = None,
    ) -> Result[HttpResponse]:
        # Two pages – first with two fragments (image + text), second empty
        body: List[dict[str, Any]] = [
            {
                "page_number": 1,
                "fragments": [
                    {
                        "filename": "img1.png",
                        "fragement_number": 0,
                        "fragement_type": "IMAGE",
                    },
                    {
                        "filename": "",
                        "fragement_number": 1,
                        "fragement_type": "TEXT",
                    },
                ],
            },
            {
                "page_number": 2,
                "fragments": [],
            },
        ]

        return Result.Ok(
            HttpResponse(
                status_code=200,
                headers={"content-type": "application/json"},
                body=body,
            )
        )

    # The remaining HTTP verbs are unused in this client – keep them as stubs

    async def get(self, url: str, header: dict[str, str]):  # type: ignore[override]
        ...

    async def post(  # type: ignore[override]
        self,
        url: str,
        header: dict[str, str],
        json: dict[str, Any] | None = None,
    ): ...

    async def delete(self, url: str, header: dict[str, str]):  # type: ignore[override]
        ...


class MockFailureHttpClient(AsyncHttpClient):
    """Simulate an upstream failure (e.g. network / 5xx error)."""

    async def put(  # type: ignore[override]
        self,
        url: str,
        header: dict[str, str],
        json: dict[str, Any] | None = None,
    ) -> Result[HttpResponse]:
        return Result.Err(Exception("Network error"))

    async def get(self, url: str, header: dict[str, str]):  # type: ignore[override]
        ...

    async def post(  # type: ignore[override]
        self,
        url: str,
        header: dict[str, str],
        json: dict[str, Any] | None = None,
    ): ...

    async def delete(self, url: str, header: dict[str, str]):  # type: ignore[override]
        ...


class MockInvalidBodyHttpClient(AsyncHttpClient):
    """Return a 200 but with a body that **cannot** be parsed into PageLite."""

    async def put(  # type: ignore[override]
        self,
        url: str,
        header: dict[str, str],
        json: dict[str, Any] | None = None,
    ) -> Result[HttpResponse]:
        return Result.Ok(
            HttpResponse(
                status_code=200,
                headers={"content-type": "application/json"},
                body="not-a-list",  # Pydantic will choke on this
            )
        )

    async def get(self, url: str, header: dict[str, str]):  # type: ignore[override]
        ...

    async def post(  # type: ignore[override]
        self,
        url: str,
        header: dict[str, str],
        json: dict[str, Any] | None = None,
    ): ...

    async def delete(self, url: str, header: dict[str, str]):  # type: ignore[override]
        ...


# ---------------------------------------------------------------------------
# Test‑suite
# ---------------------------------------------------------------------------


class TestFileConverterServiceClientImpl(TestFileConverterServiceClient):
    """Verify that the async client handles *happy* and *unhappy* paths."""

    __test__ = True

    def setup_method_sync(self, test_name: str):
        if "test_convert_file_success" == test_name:
            config = FileConverterConfig(host="http://mock")
            self.client = FileConverterServiceClientImpl(
                config, MockSuccessHttpClient()
            )
            return
        if "test_convert_file_failure" == test_name:
            config = FileConverterConfig(host="http://mock")
            self.client = FileConverterServiceClientImpl(
                config, MockFailureHttpClient()
            )
            return
        if "test_convert_file_invalid_body" == test_name:
            config = FileConverterConfig(host="http://mock")
            self.client = FileConverterServiceClientImpl(
                config, MockInvalidBodyHttpClient()
            )
            return

        raise Exception(f"No Client implementation for {test_name}")
