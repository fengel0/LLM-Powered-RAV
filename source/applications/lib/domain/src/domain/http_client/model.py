from typing import Any
from pydantic import BaseModel


class HttpResponse(BaseModel):
    status_code: int
    headers: dict[str, str] = {}
    body: Any
