from typing import Protocol, runtime_checkable

from domain.text_embedding.model import (
    EmbeddingRequestDto,
    EmbeddingResponseDto,
    RerankRequestDto,
    RerankResponseDto,
)
from core.result import Result


@runtime_checkable
class RerankerClient(Protocol):
    def rerank(self, request: RerankRequestDto) -> Result[RerankResponseDto]: ...


@runtime_checkable
class AsyncRerankerClient(Protocol):
    async def rerank(self, request: RerankRequestDto) -> Result[RerankResponseDto]: ...


@runtime_checkable
class EmbeddClient(Protocol):
    def embed(
        self, request: EmbeddingRequestDto
    ) -> Result[EmbeddingResponseDto | list[list[float]]]: ...
    def embed_doc(
        self, text: str | list[str]
    ) -> Result[EmbeddingResponseDto | list[list[float]]]: ...
    def embed_query(
        self, text: str | list[str]
    ) -> Result[EmbeddingResponseDto | list[list[float]]]: ...


@runtime_checkable
class AsyncEmbeddClient(Protocol):
    async def embed(
        self, request: EmbeddingRequestDto
    ) -> Result[EmbeddingResponseDto | list[list[float]]]: ...
    async def embed_doc(
        self, text: str | list[str]
    ) -> Result[EmbeddingResponseDto | list[list[float]]]: ...
    async def embed_query(
        self, text: str | list[str]
    ) -> Result[EmbeddingResponseDto | list[list[float]]]: ...
