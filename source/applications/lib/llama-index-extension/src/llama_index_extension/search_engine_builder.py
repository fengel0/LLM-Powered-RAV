from dataclasses import dataclass
from core.result import Result
from typing import cast
from llama_index.core import Document as Response
from domain.rag.model import Node
import logging
from domain.rag.model import (
    AsyncRerankerClient,
)
from domain.text_embedding.interface import EmbeddClient
from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.core.llms.function_calling import FunctionCallingLLM
from llama_index.core.postprocessor.types import BaseNodePostprocessor
from llama_index.core.vector_stores.types import (
    FilterCondition,
    FilterOperator,
    MetadataFilter,
    MetadataFilters,
)

from llama_index_extension.build_components import LLamaIndexHolder
from llama_index_extension.embedding import CustomEmbedding
from llama_index_extension.mock_llm import MockLLM


logger = logging.getLogger(__name__)


@dataclass
class LlamaIndexSearchEngineConfig:
    reranker: AsyncRerankerClient | None
    embedding: EmbeddClient

    top_n_count_reranker: int
    top_n_count_dens: int
    top_n_count_sparse: int

    sparse_model: str = "Qdrant/bm25"


class LlamaIndexSearchEngine:
    reranker: BaseNodePostprocessor | None
    embedding: BaseEmbedding
    llm: FunctionCallingLLM

    def __init__(self, config: LlamaIndexSearchEngineConfig) -> None:
        self.config = config
        if self.config.reranker:
            self.reranker = LLamaIndexHolder.Instance().get_custom_reranker(
                self.config.reranker, self.config.top_n_count_reranker
            )
        else:
            self.reranker = None
        self.embedding = CustomEmbedding(self.config.embedding)

    async def query(
        self,
        query: str,
        metadata_filters: dict[str, list[str] | list[int] | list[float]] | None = None,
        collection: str | None = None,
    ) -> Result[list[Node]]:
        metadata_filters = metadata_filters if metadata_filters else {}
        filters = MetadataFilters(filters=[])
        for key in metadata_filters.keys():
            for value in metadata_filters[key]:
                filters.filters.append(
                    MetadataFilter(key=key, value=value, operator=FilterOperator.EQ)
                )
        filters.condition = FilterCondition.OR

        top_k_dens = self.config.top_n_count_dens
        top_k_sparse = self.config.top_n_count_sparse

        reranker = self.reranker
        embbedder = self.embedding

        query_engine = (
            LLamaIndexHolder.Instance()
            .get_index(
                collection=collection,
                embedding_model=embbedder,
                sparse_model=self.config.sparse_model,
                top_k_sparse=top_k_sparse,
                top_k_dense=top_k_dens,
            )
            .as_query_engine(  # type: ignore
                llm=MockLLM(context_window=128000),
                similarity_top_k=top_k_dens,
                sparse_top_k=top_k_sparse,
                node_postprocessors=[self.reranker] if reranker else [],
                vector_store_query_mode="hybrid",
                filters=filters,
                use_async=True,
            )
        )

        result = await query_engine.aquery(query)
        response: Response = cast(Response, result)

        llama_index_nodes = response.source_nodes

        nodes: list[Node] = [
            Node(
                id=node.id_,
                content=node.text,
                metadata=node.metadata,
                similarity=node.get_score(raise_error=False),
            )
            for node in llama_index_nodes
        ]
        return Result.Ok(nodes)
