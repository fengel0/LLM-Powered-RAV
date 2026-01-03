from core.result import Result
from domain.hippo_rag.model import (
    ConfidenceCheck,
    DocumentCollection,
    Edge,
    OpenIEResult,
    Row,
    QuerySolution,
    NerRawOutput,
    SimilarNodes,
    Triple,
    TripleRawOutput,
    Node,
)

from typing import (
    Protocol,
    runtime_checkable,
)


@runtime_checkable
class LLMReranker(Protocol):

    """
    HippoRAG Reranker Interface for Ranking Triple/Facts
    """

    async def rerank(
        self,
        query: str,
        candidate_items: list[Triple],
        candidate_indices: list[int],
        len_after_rerank: int | None = None,
        model: str | None = None,
    ) -> Result[tuple[list[int], list[Triple], ConfidenceCheck]]: ...


@runtime_checkable
class GraphDBInterface(Protocol):

    """
    HippoRAG GraphDB Interface

    """


    async def delete_vertices(self, verticies: list[str]) -> Result[None]: ...

    async def get_vs_map(
        self,
    ) -> Result[dict[str, Node]]: ...

    async def get_edges_of_node(self, hash_id: str) -> Result[list[Edge]]: ...

    async def get_vs_map_index(
        self,
    ) -> Result[dict[str, int]]: ...

    async def get_node_by_hash(self, hash_id: str) -> Result[Node | None]: ...

    async def get_not_existing_nodes(
        self,
        hash_ids: list[str],
    ) -> Result[list[str]]: ...
    async def get_values_from_attributes(self, key: str) -> Result[list[str]]: ...

    async def get_chunk_node_connection_for_entity(
        self,
        hash_id: str,
        allowed_chunks: list[str] = [],
    ) -> Result[list[Node]]: ...

    async def add_nodes(self, nodes: list[Node]) -> Result[None]: ...
    async def add_edges(self, edges: list[Edge]) -> Result[None]: ...

    async def get_node_count(self) -> Result[int]: ...

    async def personalized_pagerank(
        self,
        seeds: dict[str, float],
        damping: float,
        top_k: int,
        directed: bool = True,
        allowed_hash_ids: list[str] | None = None,
    ) -> Result[dict[str, float]]: ...



@runtime_checkable
class OpenIEInterface(Protocol):

    """
    HippoRAG OpenIE Interface
    Open Information Extraction
    In the case of HippoRAG will it extract Triple with subject, predicate, object.
    """



    # single-chunk ops
    async def ner(
        self,
        chunk_key: str,
        passage: str,
        metadata: dict[str, int | float | str] | None = None,
    ) -> Result[NerRawOutput]: ...
    async def triple_extraction(
        self,
        chunk_key: str,
        passage: str,
        named_entities: list[str],
        metadata: dict[str, int | float | str] | None = None,
    ) -> Result[TripleRawOutput]: ...
    async def openie(
        self,
        chunk_key: str,
        passage: str,
        metadata: dict[str, int | float | str] | None = None,
    ) -> Result[OpenIEResult]: ...

    # batch op
    async def batch_openie(
        self,
        chunks: dict[str, str],
        metadata: dict[str, int | float | str] | None = None,
    ) -> Result[tuple[dict[str, NerRawOutput], dict[str, TripleRawOutput]]]: ...


@runtime_checkable
class EmbeddingStoreInterface(Protocol):

    """
    HippoRAG EmbeddingStore Interface
    naming is still the same as in the Original implementation.
    """

    # --- write / update ---
    async def insert_strings(
        self,
        texts: list[str],
    ) -> Result[None]: ...
    async def is_doc_already_inserted(
        self, texts: list[str]
    ) -> Result[dict[str, str]]: ...
    async def delete(self, hash_ids: list[str]) -> Result[None]: ...
    async def delete_store(self, collection: str) -> Result[None]: ...

    async def get_missing_string_hash_ids(
        self, texts: list[str]
    ) -> Result[dict[str, Row]]: ...

    async def get_row(self, hash_id: str) -> Result[Row]: ...
    async def get_rows(self, hash_ids: list[str]) -> Result[dict[str, Row]]: ...

    async def get_all_texts(self) -> Result[set[str]]: ...
    async def get_all_ids(self) -> Result[list[str]]: ...
    async def get_all_id_to_rows(
        self, collection: str | None = None
    ) -> Result[dict[str, Row]]: ...

    async def move_all_ids_to_new_collection(
        self, hash_ids: list[str], collection: str
    ) -> Result[None]: ...

    #
    async def query(
        self,
        query: str,
        top_k: int | None = None,
        collection: str | None = None,
        allowd__point_ids: list[str] | None = None,
    ) -> Result[list[SimilarNodes]]: ...

    async def knn_by_ids(
        self,
        query_ids: list[str],
        top_k: int,
        min_similarity: float = 0.0,
        allowd__point_ids: list[str] | None = None,
        collection: str | None = None,
    ) -> Result[dict[str, list[SimilarNodes]]]: ...


@runtime_checkable
class StateStore(Protocol):


    """
    HippoRAG StateStore Interface
    The Class that implements this interface will store all information about the Documents handle by HippoRAG.
    This contains
        - stored Chunks with Metadata
        - extracted Tripel and Entities for faster Look

    """

    # triple
    async def triples_to_docs(self, triples: Triple) -> Result[list[str]]: ...

    # chunks
    async def ent_node_to_chunk(self, ent_node: str) -> Result[list[str]]: ...
    async def ent_node_count(self) -> Result[int]: ...

    # chunks with openie info
    async def delete_chunks(self, hash_ids: list[str]) -> Result[None]: ...
    async def load_openie_info(
        self, offset: int = 0, chunk_size: int = 1024
    ) -> Result[DocumentCollection]: ...
    async def load_openie_info_with_metadata(
        self, metadata: dict[str, list[str] | list[int] | list[float]]
    ) -> Result[DocumentCollection]: ...

    async def fetch_not_existing_documents(
        self, hash_ids: list[str]
    ) -> Result[list[str]]: ...
    async def store_openie_info(
        self, documents: DocumentCollection
    ) -> Result[None]: ...

    async def fetch_chunks_by_ids(
        self, hash_ids: list[str]
    ) -> Result[DocumentCollection]: ...


@runtime_checkable
class IndexerInterface(Protocol):

    """
    HippoRAG Indexer Interface
    A lesser Version of the AsyncDocumentIndexerInterface
    It just exists to be more or less compatible with the original implementation.
    """

    async def index(
        self, docs: list[str], metadata: dict[str, str | int | float] | None = None
    ) -> Result[None]: ...
    async def delete(self, docs: list[str]) -> Result[None]: ...


@runtime_checkable
class HippoRAGInterface(Protocol):
    """Structural interface for the current HippoRAG implementation (underscored methods)."""

    # -------- Public retrieval / QA --------------------------------------------
    async def retrieve(
        self,
        queries: list[str],
        metadata: dict[str, list[str] | list[int] | list[float]],
    ) -> Result[list[QuerySolution]]: ...
    async def rag_qa(
        self,
        queries: list[str] | list[QuerySolution],
        metadata: dict[str, list[str] | list[int] | list[float]],
    ) -> Result[tuple[list[QuerySolution], list[str]]]: ...

    async def retrieve_dpr(
        self,
        queries: list[str],
        metadata: dict[str, list[str] | list[int] | list[float]],
    ) -> Result[list[QuerySolution]]: ...
    async def rag_qa_dpr(
        self,
        queries: list[str] | list[QuerySolution],
        metadata: dict[str, list[str] | list[int] | list[float]],
    ) -> Result[tuple[list[QuerySolution], list[str]]]: ...
