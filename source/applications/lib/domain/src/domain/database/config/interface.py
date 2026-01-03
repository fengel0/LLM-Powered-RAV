from typing import Any, Generic, Protocol, TypeVar, runtime_checkable

from core.result import Result
from pydantic import BaseModel

from domain.database.config.model import (
    Config,
    RAGConfig,
    RagEmbeddingConfig,
    RagRetrievalConfig,
)


T = TypeVar("T", bound=BaseModel)


@runtime_checkable
class ConfigDatabase(Generic[T], Protocol):
    """
    Generic Config Database Interface.
    does not expose update functionality, because for documentation changes in a config should result in just a new config
    """
    async def get_config_by_hash(self, hash: str) -> Result[T | None]: ...
    async def get_config_by_id(self, id: str) -> Result[T | None]: ...
    async def create_config(self, obj: T) -> Result[T]: ...
    async def fetch_all(self) -> Result[list[T]]: ...


class SystemConfigDatabase(ConfigDatabase[Config[T]], Generic[T]):

    """
    RAG System Config Interface.
    """

    async def fetch_by_config_type(
        self, config_type: str
    ) -> Result[dict[str, Any]]: ...


class RAGRetrivalConfigDatabase(ConfigDatabase[RagRetrievalConfig]):
    """
    RAG Retrival Config Interface.
    Stores the Retrieval Config Information
    """
    ...


class RAGEmbeddingConfigDatabase(ConfigDatabase[RagEmbeddingConfig]):
    """
    RAG Embedding Config Interface.
    Stores the Embedding Config Information
    """
    ...


class RAGConfigDatabase(ConfigDatabase[RAGConfig]):
    """
    RAG Config Interface.
    Stores the RAG Config Information those are a combination of Embedding and Retrieval Config
    """
    ...
