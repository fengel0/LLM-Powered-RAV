from dataclasses import dataclass
from enum import Enum
from typing import Any, AsyncGenerator
from pydantic import BaseModel

from domain.text_embedding.interface import AsyncRerankerClient, EmbeddClient


class RoleType(Enum):
    User = "user"
    Assistent = "assistant"
    System = "system"


class Message(BaseModel):
    message: str
    role: RoleType


class Node(BaseModel):
    id: str
    content: str
    similarity: float
    metadata: dict[str, Any]


@dataclass
class RAGEmbeddingConfigOverride: ...


@dataclass
class RAGRetrivalConfigOverride: ...


@dataclass
class RAGConfigOverride:
    retrival_config: RAGRetrivalConfigOverride
    embedding_config: RAGEmbeddingConfigOverride


@dataclass
class SimpleEmbeddingConfig(RAGEmbeddingConfigOverride):
    embedding: EmbeddClient


@dataclass
class SimpleRetrivalConfig(RAGRetrivalConfigOverride):
    llm_model: str
    system_prompt: str
    query_wrapper_prompt: str
    top_n_count_reranker: int
    top_n_count_dens: int
    top_n_count_sparse: int
    temperatur: float
    rerank_client: AsyncRerankerClient


@dataclass
class SubQuestionRetrivalConfig(SimpleRetrivalConfig):
    llm_model: str
    system_prompt: str
    top_n_count_reranker: int
    top_n_count_dens: int
    top_n_count_sparse: int
    temperatur: float
    system_prompt: str
    sub_query_prompt: str
    condense_queston_prompt: str
    qa_prompt: str
    query_wrapper_prompt: str
    rerank_client: AsyncRerankerClient


@dataclass
class HippoRAGEmbeddingConfigOverride(RAGEmbeddingConfigOverride):
    embedding: EmbeddClient


@dataclass
class HippoRAGRetrivalConfigOverride(RAGRetrivalConfigOverride):
    llm_model: str
    temperatur: float
    retrieval_top_k: int
    linking_top_k: int
    passage_node_weight: float
    chunks_to_retrieve_ppr_seed: int
    qa_top_k: int
    damping: float
    directional_ppr: bool


@dataclass
class RAGResponse:
    nodes: list[Node]
    message: str | None
    generator: AsyncGenerator[str, None] | None

    @staticmethod
    def create_stream_response(generator: AsyncGenerator[str, None], nodes: list[Node]):
        return RAGResponse(nodes=nodes, generator=generator, message=None)

    @staticmethod
    def create_simple_response(message: str, nodes: list[Node]):
        return RAGResponse(nodes=nodes, generator=None, message=message)


class Conversation(BaseModel):
    messages: list[Message]
    model: str
