# tests/test_rag_qdrant_queries.py
import logging

import hippo_rag_database.model as db_model
from core.logger import init_logging
from database.session import DatabaseConfig, PostgresSession
from openai_client.async_openai import ConfigOpenAI, OpenAIAsyncLLM
from domain_test.vector.vector_test import TestDBVectorStore
from hippo_rag.indexer import HippoRAGIndexer, IndexerConfig
from hippo_rag.openie import AsyncOpenIE, OpenIEConfig
from hippo_rag_database.state_holder import PostgresDBStateStore
from hippo_rag_graph.graph_implementation import (
    Neo4jConfig,
    Neo4jGraphDB,
    Neo4jSession,
    Neo4jSessionConfig,
)
from hippo_rag_vectore_store.vector_store import (
    HippoRAGVectorStoreSession,
    QdrantConfig,
    QdrantEmbeddingStore,
    QdrantEmbeddingStoreConfig,
)
from qdrant_client.models import Distance
from testcontainers.neo4j import Neo4jContainer
from testcontainers.postgres import PostgresContainer
from testcontainers.qdrant import QdrantContainer
from text_embedding.proto import EmbeddingClientConfig, GrpcEmbeddClient
from text_splitter.node_splitter import (
    AdvancedSentenceSplitter,
    NodeSplitterConfig,
)

from domain_test.enviroment import llm, embedding, test_containers

init_logging("INFO")
logger = logging.getLogger(__name__)

# ------------------------------- config -------------------------------- #
collection = "qdrant_collection"
top_n_count_dens = 5
top_n_count_sparse = 5
top_n_count_reranker = 5


NEO4J_USER = "neo4j"
NEO4J_PASS = "ThisIsSomeDummyPassw0rd!"


class TestHippoRAGIndexer(TestDBVectorStore):
    __test__ = True

    qdrant: QdrantContainer
    neo4j: Neo4jContainer
    postgres: PostgresContainer

    # ---------------------------- lifecycle ----------------------------- #
    def setup_method_sync(self, test_name: str):
        self.postgres = PostgresContainer(
            image=test_containers.POSTGRES_VERSION,
            username="test",
            password="test",
            dbname="test_db",
        )
        self.postgres.start()

        # Start Qdrant ephemeral container
        self.qdrant = (
            QdrantContainer(image=test_containers.QDRANT_VERSION)
            .with_exposed_ports(6333)
            .with_exposed_ports(6334)
        )
        self.qdrant.start()

        self.neo4j = Neo4jContainer(
            image=test_containers.NEO4J_VERSION,
            username=NEO4J_USER,
            password=NEO4J_PASS,
        )
        self.neo4j.with_env("NEO4J_PLUGINS", '["apoc","graph-data-science"]').with_env(
            "NEO4J_apoc_export_file_enabled", "true"
        ).with_env("NEO4J_apoc_import_file_enabled", "true").with_env(
            "NEO4J_apoc_import_file_use__neo4j__config", "true"
        )
        self.neo4j.with_exposed_ports(7687, 7474)
        self.neo4j.start()

        host = self.neo4j.get_container_host_ip()
        bolt_port = int(self.neo4j.get_exposed_port(7687))
        self.neo4j_uri = f"bolt://{host}:{bolt_port}"

        self.db_config = DatabaseConfig(
            host=self.postgres.get_container_host_ip(),
            port=str(self.postgres.get_exposed_port(self.postgres.port)),
            database_name="test_db",
            username="test",
            password="test",
        )

    async def setup_method_async(self, test_name: str):
        self.postgres_session = PostgresSession.create(  # type: ignore[assignment]
            config=self.db_config,
            models=[db_model],
        )
        await self.postgres_session.start()
        await self.postgres_session.migrations()

        neo4j_session = Neo4jSession.create(  # type: ignore[attr-defined]
            Neo4jSessionConfig(uri=self.neo4j_uri, user=NEO4J_USER, password=NEO4J_PASS)
        )
        await neo4j_session.start()

        cfg_ent = QdrantEmbeddingStoreConfig(
            collection="test",
            dim=embedding.EMBEDDING_SIZE,
            distance=Distance.COSINE,  # or Distance.COSINE
            namespace="entity",
        )
        cfg_chunk = QdrantEmbeddingStoreConfig(
            collection="test",
            dim=embedding.EMBEDDING_SIZE,
            distance=Distance.COSINE,  # or Distance.COSINE
            namespace="chunk",
        )
        cfg_link = QdrantEmbeddingStoreConfig(
            collection="test",
            dim=embedding.EMBEDDING_SIZE,
            distance=Distance.COSINE,  # or Distance.COSINE
            namespace="facts",
        )
        llm_client = OpenAIAsyncLLM(
            ConfigOpenAI(
                model=llm.OPENAI_MODEL,
                max_tokens=8192,
                api_key=llm.OPENAI_HOST_KEY,
                timeout=60,
                temperature=0.5,
                context_cutoff=int(128_000 * 0.90),
                base_url=llm.OPENAI_HOST,
            )
        )

        db = Neo4jGraphDB(
            Neo4jConfig(
                database="neo4j",  # normal version does not allow diffrent databases so it is hard coded
                node_label="Node",
                rel_type="LINKS",
                ppr_implementation="neo4j-gds",
            )
        )
        await db.start()

        cfg_qdrant = QdrantConfig(
            host=self.qdrant.get_container_host_ip(),
            prefere_grpc=True,
            grpc_port=self.qdrant.get_exposed_port(6334),
            port=self.qdrant.get_exposed_port(6333),
        )
        # (Re)create session for each store to ensure isolation by collection
        HippoRAGVectorStoreSession.create(config=cfg_qdrant)

        embedder = GrpcEmbeddClient(
            address=embedding.EMBEDDING_HOST,
            is_secure=False,
            config=EmbeddingClientConfig(
                normalize=True,
                truncate=False,
                truncate_direction="right",
                prompt_name_doc="",
                prompt_name_query="",
            ),
        )

        self.vector_store = HippoRAGIndexer(
            text_splitter=AdvancedSentenceSplitter(
                config=NodeSplitterConfig(
                    chunk_size=128,
                    chunk_overlap=64,
                    default_language="en",
                )
            ),
            vector_store_entity=QdrantEmbeddingStore(cfg_ent, embedder=embedder),
            vector_store_fact=QdrantEmbeddingStore(cfg_link, embedder=embedder),
            vector_store_chunk=QdrantEmbeddingStore(cfg_chunk, embedder=embedder),
            graph=db,
            openie=AsyncOpenIE(llm=llm_client, config=OpenIEConfig()),
            state_store=PostgresDBStateStore(),
            config=IndexerConfig(
                synonymy_edge_topk=5,
                synonymy_edge_sim_threshold=0.9,
                number_of_parallel_requests=1,
            ),
        )

    def teardown_method_sync(self, test_name: str):
        try:
            self.qdrant.stop()
            self.postgres.stop()
            self.neo4j.stop()
        finally:
            try:
                from core.singelton import SingletonMeta

                SingletonMeta.clear_all()
            except Exception:
                pass

    async def teardown_method_async(self, test_name: str):
        # nothing async to shut down here
        await Neo4jSession.Instance().shutdown()
        await PostgresSession.Instance().shutdown()
