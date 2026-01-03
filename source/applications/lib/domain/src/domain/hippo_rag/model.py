from dataclasses import dataclass
from typing import Any, Literal
from pydantic import BaseModel, Field


Triple = tuple[str, str, str]

Namespace = Literal["chunk", "fact", "entity"]


class GraphInfo(BaseModel):
    num_phrase_nodes: int
    num_passage_nodes: int
    num_total_nodes: int
    num_extracted_triples: int
    num_triples_with_passage_node: int
    num_synonymy_triples: int
    num_total_triples: int


class RerankLog(BaseModel):
    facts_before_rerank: list[Triple]
    facts_after_rerank: list[Triple]


class ConfidenceCheck(BaseModel):
    confidence: str | None = None


class Document(BaseModel):
    idx: str
    passage: str
    extracted_entities: list[str]
    extracted_triples: list[Triple]
    metadata: dict[str, str | int | float]


class DocumentCollection(BaseModel):
    docs: list[Document]


class SimilarNodes(BaseModel):
    id: str
    score: float
    payload: str


NodeType = Literal["entity", "chunk"]


class Node(BaseModel):
    hash_id: str
    content: str
    node_type: NodeType


@dataclass
class IndexReport:
    new_chunks: int
    new_entities: int
    new_facts: int
    graph_edges_added: int
    warnings: list[str]


@dataclass
class DeleteReport:
    chunks_deleted: int
    entities_deleted: int
    facts_deleted: int
    graph_edges_removed: int
    warnings: list[str]


class Edge(BaseModel):
    src: str
    dst: str
    weight: float


class TripleRawOutput(BaseModel):
    chunk_id: str
    response: str | None
    triples: list[Triple]
    metadata: dict[str, int | str | float]


class NerRawOutput(BaseModel):
    chunk_id: str
    response: str | None
    unique_entities: list[str]
    metadata: dict[str, Any]


class LinkingOutput(BaseModel):
    score: float
    type: Literal["node", "dpr"]


class Row(BaseModel):
    hash_id: str
    content: str


@dataclass
class Chunk:
    id: str
    content: str
    score: float
    metadata: dict[str, str | int | float]


@dataclass
class QuerySolution:
    question: str
    docs: list[Chunk]
    answer: str | None = None


class ChunkInfo(BaseModel):
    """Metadata the batch API expects per chunk."""

    num_tokens: int
    content: str
    chunk_order: list[tuple[Any]]
    full_doc_ids: list[str]


class OpenIEResult(BaseModel):
    """Return shape of OpenIE.openie(...)"""

    ner: NerRawOutput
    triplets: TripleRawOutput
