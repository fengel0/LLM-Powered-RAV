from typing import Any
from domain.rag.model import Node
from pydantic import BaseModel, Field


class RequestDoc(BaseModel):
    content: str | list[str]
    metadata: dict[str, str]


class RequestEmbed(BaseModel):
    source_bucket: str
    filenames: list[str]
    metadata: dict[str, str]


class RetrievedNote(BaseModel):
    content: str
    score: float
    metadata: dict[str, str]


class ChatMessage(BaseModel):
    role: str
    content: str
    retrieved_notes: list[RetrievedNote] | None = Field(
        default=None,
        description="List of retrieved documents with scores and metadata (for RAG)",
    )


class ChatCompletionRequest(BaseModel):
    model: str
    messages: list[ChatMessage]
    stream: bool = False
    max_tokens: int | None = None
    temperature: float | None = None
    config_id: str | None = None
    project_id: str | None = None


class QueryRequest(BaseModel):
    query: str
    enable_reranker: bool
    config_id: str | None = None
    project_id: str | None = None


class QueryResposne(BaseModel):
    nodes: list[Node]


class ChatChoice(BaseModel):
    index: int
    message: ChatMessage
    finish_reason: str


class ChatCompletionResponse(BaseModel):
    id: str
    object: str
    created: int
    model: str
    choices: list[ChatChoice]


# Optional: OpenAI standard error response format
class OpenAIError(BaseModel):
    object: str = "error"
    message: str
    type: str
    param: str | None = None
    code: str | None = None


summary = "OpenAI-compatible chat completion endpoint using custom RAG backend"


class ModelData(BaseModel):
    id: str
    name: str
    object: str = "model"
    created: int
    owned_by: str


class ModelList(BaseModel):
    object: str = "list"
    data: list[ModelData]


class DeltaMessage(BaseModel):
    role: str | None = None
    content: str | None = None


class ChatChoiceChunk(BaseModel):
    index: int
    delta: DeltaMessage
    finish_reason: str | None = None
    nodes: list[Any] | None = None


class ChatCompletionChunk(BaseModel):
    id: str
    object: str = "chat.completion.chunk"
    created: int
    model: str
    choices: list[ChatChoiceChunk]
