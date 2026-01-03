from dataclasses import dataclass
from typing import cast
from core.hash import compute_mdhash_id

from llama_index.vector_stores.qdrant.base import MetadataFilters
from llama_index_extension.embedding import CustomEmbedding, EmbeddClient
from opentelemetry import trace
import logging

from domain.rag.model import Node
from domain.rag.indexer.model import Document
from llama_index.core.schema import NodeRelationship, TextNode
from llama_index.core.vector_stores.types import (
    FilterCondition,
    FilterOperator,
    MetadataFilter,
)
from llama_index.core import Document as Response, VectorStoreIndex
from qdrant_client.http import models

from core.result import Result
from domain.rag.indexer.interface import AsyncDocumentIndexer, DocumentSplitter


from llama_index_extension.build_components import (
    LLamaIndexHolder,
    LlamaIndexVectorStoreSession,
)
from text_embedding.async_client import AsyncRerankerClient

logger = logging.getLogger(__name__)


@dataclass
class LlamaIndexVectorStoreConfig:
    embedding: EmbeddClient
    reranker: AsyncRerankerClient
    top_n_count_dens: int
    top_n_count_sparse: int
    top_n_count_reranker: int
    sparse_model: str = "Qdrant/bm25"


class LlamaIndexVectorStore(AsyncDocumentIndexer):
    """
    implementation of the VectorDatabase interface using LlamaIndex.
    """

    _note_splitter: DocumentSplitter

    def __init__(
        self, note_splitter: DocumentSplitter, config: LlamaIndexVectorStoreConfig
    ):
        self._note_splitter = note_splitter
        self._config = config
        self.embedding = CustomEmbedding(self._config.embedding)
        self.reranker = LLamaIndexHolder.Instance().get_custom_reranker(
            self._config.reranker, self._config.top_n_count_reranker
        )
        self.tracer = trace.get_tracer("LlamaIndexVectorStore")

    async def create_document(
        self, doc: Document, collection: str | None = None
    ) -> Result[None]:
        with self.tracer.start_as_current_span("store-document-in-indexer-db"):
            try:
                nodes_split = self._note_splitter.split_documents(doc=doc)
                nodes_to_insert: list[TextNode] = []
                llama_index_nodes: list[TextNode] = [
                    TextNode(text=node.content) for node in nodes_split
                ]

                index = VectorStoreIndex.from_vector_store(  # type: ignore
                    vector_store=LlamaIndexVectorStoreSession.Instance().get_database(
                        collection=collection,
                        sparse_model=self._config.sparse_model,
                        top_k_dense=1,
                        top_k_sparse=1,
                    ),
                    embed_model=self.embedding,
                )

                vector_store = LlamaIndexVectorStoreSession.Instance().get_database(
                    collection=collection,
                    sparse_model=self._config.sparse_model,
                    top_k_dense=1,
                    top_k_sparse=1,
                )

                for i, node in enumerate(llama_index_nodes):
                    node.metadata = nodes_split[i].metadata
                    node.metadata["hash"] = compute_mdhash_id(node.text)

                for i in range(1, len(llama_index_nodes)):
                    prev_node, node = llama_index_nodes[i - 1], llama_index_nodes[i]
                    node.relationships[NodeRelationship.PREVIOUS] = (
                        prev_node.as_related_node_info()
                    )
                    prev_node.relationships[NodeRelationship.NEXT] = (
                        node.as_related_node_info()
                    )

                if LlamaIndexVectorStoreSession.Instance().is_database_init(
                    collection=collection
                ):
                    for node in llama_index_nodes:
                        result = await vector_store.aget_nodes(
                            filters=MetadataFilters(
                                filters=[
                                    MetadataFilter(
                                        key="hash", value=node.metadata["hash"]
                                    )
                                ]
                            )
                        )
                        if len(result) == 0:
                            nodes_to_insert.append(node)
                else:
                    nodes_to_insert = [node for node in llama_index_nodes]

                index.insert_nodes(nodes=nodes_to_insert)
                logger.info(f"inster {len(nodes_to_insert)} nodes")
                logger.info(f"stored {doc.id}")
                return Result.Ok(None)
            except Exception as e:
                logging.getLogger(__name__).error(f"{e}", exc_info=True)
                return Result.Err(e)

    async def update_document(
        self, doc: Document, collection: str | None = None
    ) -> Result[None]:
        with self.tracer.start_as_current_span("update-document"):
            delete_result = await self.delete_document(
                doc_id=doc.id, collection=collection
            )
            if delete_result.is_error():
                return delete_result.propagate_exception()

            # Create new nodes
            return await self.create_document(doc, collection=collection)

    async def delete_document(
        self, doc_id: str, collection: str | None = None
    ) -> Result[None]:
        with self.tracer.start_as_current_span("delete-document"):
            try:
                client = LlamaIndexVectorStoreSession.get_instance().get_qdrant_client()
                config = LlamaIndexVectorStoreSession.get_instance().get_config()

                # Get all point IDs associated with the document id
                points, _ = await client.scroll(
                    collection_name=collection or config.collection,
                    scroll_filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="file_id",
                                match=models.MatchValue(value=doc_id),
                            )
                        ]
                    ),
                    with_payload=False,
                )

                point_ids = [point.id for point in points]
                if point_ids:
                    await client.delete(
                        collection_name=collection or config.collection,
                        points_selector=models.PointIdsList(points=point_ids),
                    )

                logging.getLogger(__name__).info(
                    f"Deleted document {doc_id} from indexer store"
                )
                return Result.Ok(None)
            except Exception as e:
                logging.getLogger(__name__).error(
                    f"Failed to delete document {doc_id}: {e}", exc_info=True
                )
                return Result.Err(e)

    async def find_similar_nodes(
        self,
        query: str,
        metadata: dict[str, list[str] | list[int] | list[float]] | None = None,
        collection: str | None = None,
    ) -> Result[list[Node]]:
        with self.tracer.start_as_current_span("query-for-notes"):
            try:
                if metadata is None:
                    metadata = {}
                metadata_filters = MetadataFilters(filters=[])

                for key in metadata.keys():
                    for value in metadata[key]:
                        metadata_filters.filters.append(
                            MetadataFilter(
                                key=key, value=value, operator=FilterOperator.EQ
                            )
                        )

                metadata_filters.condition = FilterCondition.OR

                index = VectorStoreIndex.from_vector_store(  # type: ignore
                    vector_store=LlamaIndexVectorStoreSession.Instance().get_database(
                        collection=collection,
                        sparse_model=self._config.sparse_model,
                        top_k_sparse=self._config.top_n_count_sparse,
                        top_k_dense=self._config.top_n_count_dens,
                    ),
                    embed_model=self.embedding,
                )

                query_engine = index.as_query_engine(  # type: ignore
                    llm=None,
                    similarity_top_k=self._config.top_n_count_sparse
                    + self._config.top_n_count_dens,
                    sparse_top_k=self._config.top_n_count_sparse
                    + self._config.top_n_count_dens,
                    node_postprocessors=[self.reranker],
                    vector_store_query_mode="hybrid",
                    filter=metadata_filters,
                )

                result = await query_engine.aquery(query)
                response: Response = cast(Response, result)

                llama_index_nodes = response.source_nodes

                nodes = [
                    Node(
                        id=node.id_,
                        content=node.text,
                        metadata=node.metadata,
                        similarity=node.get_score(raise_error=False),
                    )
                    for node in llama_index_nodes
                ]
                return Result.Ok(nodes)

            except Exception as e:
                logger.error(f"{e}", exc_info=True)
                return Result.Err(e)

    async def does_object_with_metadata_exist(
        self, metadata: dict[str, str | int | float], collection: str | None = None
    ) -> Result[bool]:
        with self.tracer.start_as_current_span("check-if-object-exists"):
            try:
                client = LlamaIndexVectorStoreSession.get_instance().get_qdrant_client()
                config = LlamaIndexVectorStoreSession.get_instance().get_config()
                if not await client.collection_exists(collection or config.collection):
                    return Result.Ok(False)

                qdrant_nodes, _ = await client.scroll(
                    collection_name=collection or config.collection,
                    scroll_filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key=key,
                                match=models.MatchValue(value=metadata[key]),
                            )
                            for key in metadata.keys()
                        ]
                    ),
                )
                return Result.Ok(len(qdrant_nodes) > 0)
            except Exception as e:
                logger.error(f"{e}", exc_info=True)
                return Result.Err(e)
