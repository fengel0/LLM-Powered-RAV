import logging
from domain.text_embedding.interface import (
    AsyncRerankerClient,
)
from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.core.llms.function_calling import FunctionCallingLLM
from llama_index.core.postprocessor.types import BaseNodePostprocessor
from llama_index.core.schema import BaseNode
from llama_index.core.vector_stores.types import (
    BasePydanticVectorStore,
)
from llama_index.vector_stores.qdrant import QdrantVectorStore

from llama_index.vector_stores.qdrant.base import VectorStoreQueryResult
from qdrant_client import AsyncQdrantClient, QdrantClient


from core.singelton import BaseSingleton
from llama_index.core import (
    VectorStoreIndex,  # type: ignore
)
from pydantic import BaseModel

from llama_index_extension.llm import OpenAI
from llama_index_extension.reranker import CustomRerankerClient
from llama_index_extension.vector_store_session import (
    LlamaIndexVectorStoreSessionConfig,
)

logger = logging.getLogger(__name__)


class LlamaIndexRAGConfig(BaseModel):
    api_key: str = "dummy"
    base_url: str | None = None
    timeout: float = 60.0


class LLamaIndexHolder(BaseSingleton):
    _indexes: dict[str, VectorStoreIndex]
    _default_index_key = "default"
    _config: LlamaIndexRAGConfig

    def _init_once(self, config: LlamaIndexRAGConfig):
        self._config = config

    def get_index(
        self,
        embedding_model: BaseEmbedding,
        sparse_model: str,
        top_k_sparse: int,
        top_k_dense: int,
        collection: str | None = None,
    ) -> VectorStoreIndex:
        return VectorStoreIndex.from_vector_store(  # type: ignore
            vector_store=LlamaIndexVectorStoreSession.Instance().get_database(
                collection=collection,
                sparse_model=sparse_model,
                top_k_dense=top_k_dense,
                top_k_sparse=top_k_sparse,
            ),
            embed_model=embedding_model or self._embedding_model,
            use_async=True,
        )

    def get_custom_reranker(
        self, reranker: AsyncRerankerClient, top_n_count_reranker: int
    ) -> BaseNodePostprocessor:
        return CustomRerankerClient(top_n=top_n_count_reranker, async_client=reranker)

    def get_llm(
        self, model: str, temperatur: float, context_window: int
    ) -> FunctionCallingLLM:
        return OpenAI(
            temperature=temperatur,
            model=model,
            api_base=self._config.base_url,
            timeout=self._config.timeout,
            context_window=context_window,
            api_key=self._config.api_key,
        )


class LlamaIndexVectorStoreSession(BaseSingleton):
    """
    LlamaIndexVectorStoreSession is a singleton class that holds the database instance.
    Allows to reuse the same database instance across the application.
    """

    _instance = None
    _vector_stores: dict[str, QdrantVectorStore]
    _config: LlamaIndexVectorStoreSessionConfig | None = None
    _client: QdrantClient | None = None
    _aclient: AsyncQdrantClient | None = None

    def _init_once(self, config: LlamaIndexVectorStoreSessionConfig):
        from llama_index.core import Settings

        Settings.llm = None  # type: ignore
        self._client = QdrantClient(host=config.qdrant_host, port=config.qdrant_port)
        self._aclient = AsyncQdrantClient(
            host=config.qdrant_host, port=config.qdrant_port
        )
        self._vector_stores = {}
        self._config = config

    def _build_vector_store(
        self, collection: str, sparse_model: str, top_k_sparse: int, top_k_dense: int
    ) -> QdrantVectorStore:
        assert self._config is not None, "Session not initialised."
        assert self._aclient is not None, "Session not initialised."

        def relative_score_fusion(
            dense_result: VectorStoreQueryResult,
            sparse_result: VectorStoreQueryResult,
            alpha: float = 0.5,  # passed in from the query engine
            top_k: int = 2,  # passed in from the query engine i.e. similarity_top_k
        ) -> VectorStoreQueryResult:
            if (dense_result.nodes is None or len(dense_result.nodes) == 0) and (
                sparse_result.nodes is None or len(sparse_result.nodes) == 0
            ):
                return VectorStoreQueryResult(nodes=None, similarities=None, ids=None)
            elif sparse_result.nodes is None or len(sparse_result.nodes) == 0:
                return dense_result
            elif dense_result.nodes is None or len(dense_result.nodes) == 0:
                return sparse_result

            assert dense_result.similarities
            assert dense_result.nodes
            assert sparse_result.similarities
            assert sparse_result.nodes

            sparse_result_tuples = list(
                zip(sparse_result.similarities, sparse_result.nodes)
            )
            sparse_result_tuples.sort(key=lambda x: x[0], reverse=True)

            dense_result_tuples = list(
                zip(dense_result.similarities, dense_result.nodes)
            )
            dense_result_tuples.sort(key=lambda x: x[0], reverse=True)

            sparse_result_tuples = sparse_result_tuples[:top_k_sparse]
            dense_result_tuples = dense_result_tuples[:top_k_dense]

            logger.info(f"dense elements {len(dense_result_tuples)}")
            logger.info(f"dense elements {[x.node_id for _, x in dense_result_tuples]}")
            logger.info(f"sparse elements {len(sparse_result_tuples)}")
            logger.info(
                f"sparse elements {[x.node_id for _, x in sparse_result_tuples]}"
            )

            # track nodes in both results
            all_nodes_dict = {x.node_id: x for _, x in dense_result_tuples}
            for _, node in sparse_result_tuples:
                if node.node_id not in all_nodes_dict:
                    all_nodes_dict[node.node_id] = node

            sparse_similarities = [x[0] for x in sparse_result_tuples]
            sparse_per_node = {}
            if len(sparse_similarities) > 0:
                max_sparse_sim = max(sparse_similarities)
                min_sparse_sim = min(sparse_similarities)
                if max_sparse_sim == min_sparse_sim:
                    sparse_similarities = [max_sparse_sim] * len(sparse_similarities)
                else:
                    sparse_similarities = [
                        (x - min_sparse_sim) / (max_sparse_sim - min_sparse_sim)
                        for x in sparse_similarities
                    ]
                sparse_per_node = {
                    sparse_result_tuples[i][1].node_id: x
                    for i, x in enumerate(sparse_similarities)
                }

            # normalize dense similarities from 0 to 1
            dense_similarities = [x[0] for x in dense_result_tuples]
            dense_per_node = {}
            if len(dense_similarities) > 0:
                max_dense_sim = max(dense_similarities)
                min_dense_sim = min(dense_similarities)
                if max_dense_sim == min_dense_sim:
                    dense_similarities = [max_dense_sim] * len(dense_similarities)
                else:
                    dense_similarities = [
                        (x - min_dense_sim) / (max_dense_sim - min_dense_sim)
                        for x in dense_similarities
                    ]
                dense_per_node = {
                    dense_result_tuples[i][1].node_id: x
                    for i, x in enumerate(dense_similarities)
                }

            # fuse the scores
            fused_similarities: list[tuple[float, BaseNode]] = []
            for node_id in all_nodes_dict:
                sparse_sim = sparse_per_node.get(node_id, 0)
                dense_sim = dense_per_node.get(node_id, 0)
                fused_sim = alpha * (sparse_sim + dense_sim)
                fused_similarities.append((fused_sim, all_nodes_dict[node_id]))

            fused_similarities.sort(key=lambda x: x[0], reverse=True)

            return VectorStoreQueryResult(
                nodes=[x[1] for x in fused_similarities],
                similarities=[x[0] for x in fused_similarities],
                ids=[x[1].node_id for x in fused_similarities],
            )

        return QdrantVectorStore(
            collection,
            client=self._client,
            aclient=self._aclient,
            enable_hybrid=True,
            fastembed_sparse_model=sparse_model,
            batch_size=self._config.batch_size,
            # hybrid_fusion_fn=relative_score_fusion,  # type: ignore
            use_async=True,
        )

    @staticmethod
    def get_instance() -> "LlamaIndexVectorStoreSession":
        return LlamaIndexVectorStoreSession()

    def get_database(
        self,
        sparse_model: str,
        top_k_sparse: int,
        top_k_dense: int,
        collection: str | None = None,
    ) -> BasePydanticVectorStore:
        """
        Return a VectorStore for `collection`.

        * If `collection` is omitted, the default collection from the config
          is returned (preserves original behaviour).
        * If `collection` has never been requested before, it is created and cached.
        """
        if collection is None:
            assert self._config is not None, (
                "Session not initialised – missing default collection."
            )
            collection = self._config.collection

        return self._build_vector_store(
            collection=collection,
            sparse_model=sparse_model,
            top_k_sparse=top_k_sparse,
            top_k_dense=top_k_dense,
        )

    def is_database_init(self, collection: str | None = None) -> bool:
        assert self._config
        collection_value = collection or self._config.collection
        if collection_value not in self._vector_stores.keys():
            return False
        return self._vector_stores[collection_value]._collection_initialized  # type: ignore

    def get_config(self) -> LlamaIndexVectorStoreSessionConfig:
        assert self._config is not None, "Database is not initialized."
        return self._config

    def get_qdrant_client(self) -> AsyncQdrantClient:
        assert self._aclient is not None, "Database is not initialized."
        return self._aclient

    async def close(self) -> None:
        if self._aclient:
            await self._aclient.close()
