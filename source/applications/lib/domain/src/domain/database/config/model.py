from __future__ import annotations
from pydantic import BaseModel
import json
import hashlib
from typing import Any, Generic, Literal, TypeVar


T = TypeVar("T", bound=BaseModel)


class MODEL_KEY:
    EMBEDDING_MODEL = "EMBEDDING_MODEL"
    RERANK_MODEL = "RERANK_MODEL"
    LLM_MODEL = "LLM_MODEL"


class PROMPT_KEY:
    SYSTEM_PROMPT = "SYSTEM_PROMPT"


class ConfigInterface(BaseModel):
    id: str
    hash: str = ""

    def compute_config_hash(self) -> str: ...


class Config(ConfigInterface, Generic[T]):
    """Complete, reference-able configuration for one system variant."""

    data: T

    def compute_config_hash(self) -> str:
        serialized = json.dumps(self.data.model_dump(), sort_keys=True)
        hash = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        self.hash = hash
        return hash


class RagEmbeddingConfig(ConfigInterface):
    chunk_size: int
    chunk_overlap: int
    models: dict[str, str]
    addition_information: dict[str, Any]

    def compute_config_hash(self) -> str:
        serialized = json.dumps(self.model_dump(exclude={"hash", "id"}), sort_keys=True)
        hash = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        self.hash = hash
        return hash


class RagRetrievalConfig(ConfigInterface):
    generator_model: str
    temp: float
    prompts: dict[str, str]
    addition_information: dict[str, Any]

    def compute_config_hash(self) -> str:
        serialized = json.dumps(self.model_dump(exclude={"hash", "id"}), sort_keys=True)
        hash = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        self.hash = hash
        return hash


RAGConfigType = Literal["subquestion", "hybrid", "hippo-rag"]


class RAGConfigTypeE:
    SUBQUESTION = "subquestion"
    HYBRID = "hybrid"
    HIPPO_RAG = "hippo-rag"


class RAGConfig(ConfigInterface):
    name: str
    config_type: RAGConfigType
    embedding: RagEmbeddingConfig
    retrieval_config: RagRetrievalConfig

    def compute_config_hash(self) -> str:
        self.hash = f"{self.embedding.compute_config_hash()}-{self.retrieval_config.compute_config_hash()}"
        return self.hash


class EvaluationConfig(BaseModel):
    name: str
    model: str
    prompts: dict[str, str]


class GradingServiceConfig(BaseModel):
    system_name: str
    system_prompt_completness: str
    system_prompt_completness_context: str
    system_prompt_correctnes: str
    model: str
    temp: float
