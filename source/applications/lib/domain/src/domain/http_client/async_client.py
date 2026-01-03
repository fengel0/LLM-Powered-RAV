from typing import Any, AsyncGenerator, Protocol
from core.result import Result
from domain.http_client.model import HttpResponse


class AsyncHttpClient(Protocol):
    async def get(
        self,
        url: str,
        header: dict[str, str],
    ) -> Result[HttpResponse]: ...

    async def post(
        self, url: str, header: dict[str, str], json: dict[str, Any] | None = None
    ) -> Result[HttpResponse]: ...

    async def put(
        self, url: str, header: dict[str, str], json: dict[str, Any] | None = None
    ) -> Result[HttpResponse]: ...

    async def delete(
        self, url: str, header: dict[str, str]
    ) -> Result[HttpResponse]: ...

    async def stream(
        self, url: str, header: dict[str, str], json: dict[str, Any] | None = None
    ) -> Result[AsyncGenerator[str, None]]: ...
