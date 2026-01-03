from typing import Any, Protocol, runtime_checkable
from core.result import Result
from domain.http_client.model import HttpResponse


@runtime_checkable
class SyncHttpClient(Protocol):
    def get(self, url: str, header: dict[str, str]) -> Result[HttpResponse]: ...

    def post(
        self,
        url: str,
        header: dict[str, str],
        json: dict[str, Any] | None = None,
    ) -> Result[HttpResponse]: ...

    def put(
        self, url: str, header: dict[str, str], json: dict[str, Any] | None = None
    ) -> Result[HttpResponse]: ...

    def delete(
        self,
        url: str,
        header: dict[str, str],
    ) -> Result[HttpResponse]: ...
