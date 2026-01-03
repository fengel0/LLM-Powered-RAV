from pydantic import BaseModel
from domain.file_converter.model import Page


class Document(BaseModel):
    id: str
    content: str | list[Page]
    metadata: dict[str, int | float | str]


class SplitNode(BaseModel):
    id: str
    content: str
    metadata: dict[str, int | float | str]
