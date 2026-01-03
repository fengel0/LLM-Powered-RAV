from pydantic import BaseModel, RootModel


class RerankRequestDto(BaseModel):
    query: str
    raw_scores: bool
    return_text: bool
    texts: list[str]
    truncate: bool
    truncation_direction: str


class RerankResponseElement(BaseModel):
    index: int
    score: float
    text: str


class RerankResponseDto(RootModel[list[RerankResponseElement]]): ...


class EmbeddingRequestDto(BaseModel):
    inputs: str | list[str]
    normalize: bool
    prompt_name: str | None
    truncate: bool
    truncation_direction: str


class EmbeddingResponseDto(RootModel[list[float]]): ...
