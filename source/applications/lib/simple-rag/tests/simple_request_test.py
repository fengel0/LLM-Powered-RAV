# tests/test_rag_qdrant_queries.py
import logging
from domain_test.enviroment import llm, rerank, embedding, test_containers

from core.logger import init_logging
from llama_index_extension.embedding import CustomEmbedding
from llama_index_extension.simple_builder import (
    LlamaIndexSimpleBuilder,
    LlamaIndexSimpleBuilderConfig,
)
from testcontainers.qdrant import QdrantContainer
from llama_index.core.data_structs.data_structs import Node
from simple_rag.llama_index_rag import LlamaIndexRAG

from text_embedding.proto import EmbeddingClientConfig, GrpcEmbeddClient
from text_embedding.async_client import CohereHttpRerankerClient, CohereRerankerConfig
from rest_client.async_client import OTELAsyncHTTPClient

from llama_index_extension.build_components import (
    LlamaIndexVectorStoreSessionConfig,
    LlamaIndexVectorStoreSession,
    LLamaIndexHolder,
    LlamaIndexRAGConfig,
)

from domain_test.rag.test_rag import TestDBRAGQueries

init_logging("INFO")
logger = logging.getLogger(__name__)

# ------------------------------- config -------------------------------- #
collection = "qdrant_collection"
top_n_count_dens = 2
top_n_count_sparse = 2
top_n_count_reranker = 5


class TestQdrantSimpleRAGQueries(TestDBRAGQueries):
    __test__ = True

    qdrant: QdrantContainer

    # ---------------------------- lifecycle ----------------------------- #
    def setup_method_sync(self, test_name: str):
        # Start Qdrant ephemeral container
        self.qdrant = (
            QdrantContainer(image=test_containers.QDRANT_VERSION)
            .with_exposed_ports(6333)
            .with_exposed_ports(6334)
        )
        self.qdrant.start()

        # Prepare vector DB config using exposed ports
        self._vdb_cfg = LlamaIndexVectorStoreSessionConfig(
            qdrant_host=self.qdrant.get_container_host_ip(),
            qdrant_port=int(self.qdrant.get_exposed_port(6333)),
            qdrant_api_key=None,
            qdrant_grpc_port=int(self.qdrant.get_exposed_port(6334)),
            qdrant_prefer_grpc=True,
            collection=collection,
            batch_size=20,
        )

        self._rag_cfg = LlamaIndexRAGConfig(
            base_url=llm.OPENAI_HOST,
            api_key=llm.OPENAI_HOST_KEY,
        )

    async def setup_method_async(self, test_name: str):
        LlamaIndexVectorStoreSession.create(config=self._vdb_cfg)  # type: ignore

        LLamaIndexHolder.create(  # type: ignore
            config=self._rag_cfg,
        )

        cfg = LlamaIndexSimpleBuilderConfig(
            llm_model=llm.OPENAI_MODEL,
            top_n_count_dens=top_n_count_dens,
            top_n_count_sparse=top_n_count_sparse,
            top_n_count_reranker=top_n_count_reranker,
            temperatur=0.4,
            context_window=128000,
            embedding=GrpcEmbeddClient(
                address=embedding.EMBEDDING_HOST,
                is_secure=False,
                config=EmbeddingClientConfig(
                    normalize=True,
                    truncate=True,
                    truncate_direction="right",
                    prompt_name_doc=None,
                    prompt_name_query=None,
                ),
            ),
            reranker=CohereHttpRerankerClient(
                base_url=rerank.RERANKER_HOST,
                api_key=rerank.RERANKER_API_KEY,
                http=OTELAsyncHTTPClient(),
                config=CohereRerankerConfig(model=rerank.MODEL_RERANKER),
            ),
        )

        self.rag_llm = LlamaIndexRAG(chat_builder=LlamaIndexSimpleBuilder(config=cfg))

        # Seed two small nodes for the tests to retrieve
        result = await (
            LLamaIndexHolder.Instance()
            .get_index(
                embedding_model=CustomEmbedding(cfg.embedding),
                sparse_model=cfg.sparse_model,
                top_k_dense=5,
                top_k_sparse=5,
            )
            .ainsert_nodes(
                nodes=[
                    Node(
                        text="Ich mag Eiscreme",
                        metadata={"other": "test", "count": 3},
                    ),
                    Node(
                        text="Ich mag Bratwurst",
                        metadata={"other": "lol", "count": 5},
                    ),
                    Node(
                        text="Ich mag Musik",
                        metadata={"other": "lol", "count": 5},
                    ),
                    Node(
                        text="Ich mag Gurken",
                        metadata={"other": "lol", "count": 5},
                    ),
                    Node(
                        text="Ich mag Roster",
                        metadata={"other": "lol", "count": 5},
                    ),
                    Node(
                        text="Ich mag Debian",
                        metadata={"other": "lol", "count": 5},
                    ),
                ]
            )
        )
        # ainsert_nodes may return None in some versions; just log presence
        logger.info("Seeded nodes for tests: %s", str(result))

    def teardown_method_sync(self, test_name: str):
        try:
            self.qdrant.stop()
        finally:
            try:
                from core.singelton import SingletonMeta

                SingletonMeta.clear_all()
            except Exception:
                pass

    async def teardown_method_async(self, test_name: str):
        # nothing async to shut down here
        pass
