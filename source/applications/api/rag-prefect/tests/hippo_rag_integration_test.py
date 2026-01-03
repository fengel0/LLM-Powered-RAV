# tests/test_e2e_env_provisioning.py
from __future__ import annotations

import logging
import os
from typing import Any
from unittest.mock import patch

from domain.database.config.model import (
    RAGConfig,
    RagEmbeddingConfig,
    RagRetrievalConfig,
)
from openai_client.async_openai import ConfigOpenAI, OpenAIAsyncLLM

import config_database.model as config_models
import fact_store_database.model as fact_models
import hippo_rag_database.model as hippo_rag_models
import project_database.model as project_models

# DB models your service actually touches
import validation_database.model as validation_models
from core.config_loader import ConfigLoaderImplementation, ConfigProvisioner
from core.logger import disable_local_logging
from core.singelton import SingletonMeta
from database.session import DatabaseConfig, PostgresSession
from deployment_base.enviroment.hippo_rag import (
    CHUNKS_TO_RETRIEVE_PPR_SEED,
    DAMPING,
    PASSAGE_NODE_WEIGHT,
    PPR_DIRECTED,
    QA_TOP_N,
    TOP_N_HIPPO_RAG,
    TOP_N_LINKINIG,
)
from deployment_base.enviroment.hippo_rag import (
    SETTINGS as HIPPO_RAG_SETTINGS,
)
from deployment_base.enviroment.log_env import (
    LOG_LEVEL,
    OTEL_ENABLED,
    OTEL_HOST,
    OTEL_INSECURE,
)
from deployment_base.enviroment.log_env import (
    SETTINGS as LOG_SETTINGS,
)
from deployment_base.enviroment.neo4j_env import (
    NEO4J_HOST,
    NEO4J_PASSWORD,
    NEO4J_USER,
)
from deployment_base.enviroment.neo4j_env import (
    SETTINGS as NEO4J_SETTINGS,
)
from deployment_base.enviroment.openai_env import (
    MAX_TOKENS,
    OPENAI_HOST,
    OPENAI_MODEL,
)
from deployment_base.enviroment.openai_env import (
    SETTINGS as OPENAI_SETTINGS,
)
from deployment_base.enviroment.postgres_env import (
    POSTGRES_DATABASE,
    POSTGRES_HOST,
    POSTGRES_PASSWORD,
    POSTGRES_PORT,
    POSTGRES_USER,
)
from deployment_base.enviroment.postgres_env import (
    SETTINGS as POSTGRES_SETTINGS,
)
from deployment_base.enviroment.qdrant_env import (
    QDRANT_API_KEY,
    QDRANT_GRPC_PORT,
    QDRANT_HOST,
    QDRANT_PORT,
    QDRANT_PREFER_GRPC,
    VECTOR_COLLECTION,
)
from deployment_base.enviroment.qdrant_env import (
    SETTINGS as QDRANT_SETTINGS,
)
from deployment_base.enviroment.text_embedding import (
    EMBEDDING_DOC_PROMPT_NAME,
    EMBEDDING_HOST,
    EMBEDDING_MODEL,
    EMBEDDING_QUERY_PROMPT_NAME,
    EMBEDDING_SIZE,
    EMEDDING_NORMALIZE,
    IS_EMBEDDING_HOST_SECURE,
    TRUNCATE,
    TRUNCATE_DIRECTION,
)
from deployment_base.enviroment.text_embedding import (
    SETTINGS_ALL as TEXT_EMBEDDING_SETTINGS,
)
from deployment_base.enviroment.vllm_reranker import RERANK_HOST
from deployment_base.enviroment.vllm_reranker import SETTINGS as RERANK_SETTINGS

# ----- settings keys -----
# Hippo / pipeline bits used inline
from domain.rag.indexer.model import Document
from domain.rag.interface import Conversation
from domain.rag.model import Message, RoleType
from domain_test import AsyncTestBase
from domain_test.enviroment import embedding, llm, rerank, test_containers
from hippo_rag.implementation import HippoRAG
from hippo_rag.indexer import HippoRAGIndexer, IndexerConfig
from hippo_rag.openie import AsyncOpenIE, OpenIEConfig
from hippo_rag_database.state_holder import PostgresDBStateStore
from hippo_rag_graph.graph_implementation import Neo4jConfig, Neo4jGraphDB
from hippo_rag_vectore_store.vector_store import (
    QdrantEmbeddingStore,
    QdrantEmbeddingStoreConfig,
)
from qdrant_client.models import Distance
from rag_pipline_service.usecase.rag import RAGUsecase
from rag_prefect.application_startup import RAGPrefectApplication
from rag_prefect.settings import (
    EMBEDD_CONFIG_TO_USE,
    PARALLEL_REQUESTS,
    RAG_TYPE,
    SETTINGS,
)
from testcontainers.neo4j import Neo4jContainer
from testcontainers.postgres import PostgresContainer
from testcontainers.qdrant import QdrantContainer
from text_embedding.proto import EmbeddingClientConfig, GrpcEmbeddClient
from text_splitter.node_splitter import (
    AdvancedSentenceSplitter,
    NodeSplitterConfig,
)

from tests.application_startup import (
    SYNONYME_EDEGE_TOP_N,
    SYNONYMY_EDGE_SIM_THRESHOLD,
    TEMPERATUR,
    RAGConfigTypeE,
)

# ----- retrieval configs (unchanged content trimmed only where obvious) -----
SIMPLE_CONFIG = {
    "id": "83716762-7485-4316-a93f-f75d6df507c7",
    "stored_config": {
        "name": "hybrid-retrival",
        "model": "gemma3:27b",
        "prompts": {
            "SYSTEM_PROMPT": "You are a Retrieval-Augmented Generation assistant.\n..."
        },
        "retrieval": {
            "strategy": "bm25+dense",
            "metadata": {
                "CHUNK_SIZE": 512,
                "EMEDD_MODEL": "Qwen/Qwen3-Embedding-0.6B",
                "RERANK_MODEL": "Alibaba-NLP/gte-multilingual-reranker-base",
                "CHUNK_OVERLAP": 64,
                "TOP_N_COUNT_DENSE": 10,
                "VECTOR_BATCH_SIZE": 20,
                "TOP_N_COUNT_SPARSE": 10,
                "TOP_N_COUNT_RERANKER": 10,
            },
            "index_name": None,
        },
        "reasoning": {
            "approach": "direct",
            "temperature": 0.5,
            "context_window": 8192,
            "chain_of_thought": False,
        },
    },
}
SUB_CONFIG = {
    "id": "bd6c8c38-005c-428f-aff9-b0d74cce610c",
    "stored_config": {
        "name": "hybrid-retrival",
        "model": "qwen3:32b",
        "prompts": {
            "QA_PROMPT": "Query: {query_str}\nContext information ...",
            "SUB_QUER_PROMPT": "Given a user question ...",
            "SUB_SYSTEM_PROMPT": "You are an expert Q&A system ...",
            "QUERY_WRAPPER_PROMPT": "Context information is below ...",
            "CONDENSE_QUESTON_PROMPT": "Given a conversation ...",
        },
        "retrieval": {
            "strategy": "dense_per_subq",
            "metadata": {
                "CHUNK_SIZE": 512,
                "EMEDD_MODEL": "Qwen/Qwen3-Embedding-0.6B",
                "RERANK_MODEL": "Alibaba-NLP/gte-multilingual-reranker-base",
                "CHUNK_OVERLAP": 64,
                "TOP_N_COUNT_DENSE": 10,
                "VECTOR_BATCH_SIZE": 20,
                "TOP_N_COUNT_SPARSE": 10,
                "TOP_N_COUNT_RERANKER": 10,
            },
            "index_name": None,
        },
        "reasoning": {
            "approach": "subanswer_merge",
            "temperature": 0.5,
            "context_window": 8192,
            "chain_of_thought": False,
        },
    },
}
GRAPH_CONFIG = {
    "id": "bd6c8c38-005c-428f-aff9-b0d74cce610c",
    "stored_config": {
        "name": "hybrid-retrival",
        "model": "gemma3:4b",
        "prompts": {
            "QA_PROMPT": "Query: {query_str}\nContext information ...",
            "SUB_QUER_PROMPT": "Given a user question ...",
            "SUB_SYSTEM_PROMPT": "You are an expert Q&A system ...",
            "QUERY_WRAPPER_PROMPT": "Context information is below ...",
            "CONDENSE_QUESTON_PROMPT": "Given a conversation ...",
        },
        "retrieval": {
            "strategy": "dense_per_subq",
            "metadata": {
                "TOP_N_HIPPO_RAG": 10,
                "TOP_N_LINKINIG": 10,
                "PASSAGE_NODE_WEIGHT": 0.5,
                "QA_TOP_N": 10,
                "DAMPING": 0.5,
                "EMEDD_MODEL": "Qwen/Qwen3-Embedding-0.6B",
                "RERANK_MODEL": "Alibaba-NLP/gte-multilingual-reranker-base",
                "PPR_DIRECTED": "false",
            },
            "index_name": None,
        },
        "reasoning": {
            "approach": "subanswer_merge",
            "temperature": 0.5,
            "context_window": 8192,
            "chain_of_thought": False,
        },
    },
}

logger = logging.getLogger(__name__)

NEO4J_USER_DEFAULT = "neo4j"
NEO4J_PASS_DEFAULT = "password"


class TestRagPrefectProvisioning(AsyncTestBase):
    __test__ = True

    # ------------------------ class-level (containers) ------------------------
    @classmethod
    def setup_class_sync(cls):
        # Postgres
        cls._pg = PostgresContainer(
            image=test_containers.POSTGRES_VERSION,
            username="test",
            password="test",
            dbname="test_db",
        ).start()
        cls._pg_host = cls._pg.get_container_host_ip()
        cls._pg_port = str(cls._pg.get_exposed_port(5432))

        # Qdrant
        cls._qdrant = (
            QdrantContainer(image=test_containers.QDRANT_VERSION)
            .with_exposed_ports(6333)
            .with_exposed_ports(6334)
            .start()
        )
        cls._q_host = cls._qdrant.get_container_host_ip()
        cls._q_http = str(cls._qdrant.get_exposed_port(6333))
        cls._q_grpc = str(cls._qdrant.get_exposed_port(6334))

        # Neo4j
        cls._neo4j = (
            Neo4jContainer(
                image=test_containers.NEO4J_VERSION,
                username=NEO4J_USER_DEFAULT,
                password=NEO4J_PASS_DEFAULT,
            )
            .with_env("NEO4J_PLUGINS", '["apoc","graph-data-science"]')
            .with_env("NEO4J_apoc_export_file_enabled", "true")
            .with_env("NEO4J_apoc_import_file_enabled", "true")
            .with_env("NEO4J_apoc_import_file_use__neo4j__config", "true")
            .with_exposed_ports(7687, 7474)
            .start()
        )
        cls._neo_host = cls._neo4j.get_container_host_ip()
        cls._neo_bolt = str(cls._neo4j.get_exposed_port(7687))

        logger.info("Postgres, Qdrant, Neo4j started for rag-prefect e2e.")

    @classmethod
    def teardown_class_sync(cls):
        # Stop containers (best-effort)
        for c in (
            getattr(cls, "_neo4j", None),
            getattr(cls, "_qdrant", None),
            getattr(cls, "_pg", None),
        ):
            try:
                if c:
                    c.stop()
            except Exception as e:
                logger.warning("Failed to stop container: %s", e)

    # ------------------------ per-test setup/teardown -------------------------
    async def setup_method_async(self, test_name: str):
        # fresh DB schema each test
        cfg = DatabaseConfig(
            host=self._pg_host,
            port=self._pg_port,
            database_name="test_db",
            username="test",
            password="test",
        )
        try:
            PostgresSession._instances.clear()  # type: ignore[attr-defined]
        except Exception:
            pass

        PostgresSession.create(
            config=cfg,
            models=[
                validation_models,
                config_models,
                project_models,
                hippo_rag_models,
                fact_models,
            ],
        )
        s = PostgresSession.Instance()
        await s.start()
        await s.migrations()
        await s.shutdown()

        # Prefect enviroment to avoid ephemeral API/logging noise
        self._prefect_env = {
            "PREFECT_API_ENABLE_EPHEMERAL_SERVER": "false",
            "PREFECT_SERVER_EPHEMERAL_STARTUP_TIMEOUT_SECONDS": "90",
            "PREFECT_LOGGING_TO_API": "false",
            "PREFECT_LOGGING_TO_CONSOLE": "false",
            "PREFECT_LOGGING_LEVEL": "CRITICAL",
        }
        self._env_patcher = patch.dict(os.environ, self._prefect_env, clear=False)
        self._env_patcher.start()

        SingletonMeta.clear_all()

    async def teardown_method_async(self, test_name: str):
        # close any session still around
        try:
            await PostgresSession.Instance().shutdown()
        except Exception:
            pass
        try:
            PostgresSession._instances.clear()  # type: ignore[attr-defined]
        except Exception:
            pass

    def teardown_method_sync(self, test_name: str):
        # unpatch enviroment
        try:
            self._env_patcher.stop()
        except Exception:
            pass

        # flush/close Prefect handlers to avoid Rich "I/O on closed file"
        root = logging.getLogger()
        for h in list(root.handlers):
            if "prefect" in h.__class__.__name__.lower() or "prefect" in str(h).lower():
                try:
                    h.flush()
                except Exception:
                    pass
                try:
                    h.close()
                except Exception:
                    pass

        # quiet noisy libs
        for name in (
            "prefect",
            "prefect.client",
            "prefect.server",
            "httpx",
            "httpcore",
        ):
            logging.getLogger(name).setLevel(logging.CRITICAL)

        try:
            SingletonMeta.clear_all()
        except Exception:
            pass
        disable_local_logging()

    # --------------------------------- test -----------------------------------
    async def test_app_runs_with_naive_sub_graph(self):
        # We only exercise the GRAPH path here (your original did that)
        values = {
            **self._compose_common_values(),
            # **self._compose_prompt_files("graph"),
            **self._compose_mode_values(RAGConfigTypeE.HIPPO_RAG),
            **self._compose_graph_values(),
        }
        prov = ConfigProvisioner(
            attributes=[
                *HIPPO_RAG_SETTINGS,
                *OPENAI_SETTINGS,
                *QDRANT_SETTINGS,
                *LOG_SETTINGS,
                *SETTINGS,
                *TEXT_EMBEDDING_SETTINGS,
                *RERANK_SETTINGS,
                *OPENAI_SETTINGS,
                *POSTGRES_SETTINGS,
                *NEO4J_SETTINGS,
            ],
            values=values,
            create_missing_dirs=True,
        )
        prov.apply()

        data: dict[str, Any] = EMBEDDING_CONFIG_GRAPH["stored_config"]  # type:ignore
        data_r: dict[str, Any] = RETRIVAL_CONFIG_GRAPH["stored_config"]  # type:ignore

        # DB ping/migrations are done in setup; now boot the app
        RAGPrefectApplication.create(ConfigLoaderImplementation.create())
        RAGPrefectApplication.Instance().set_rag_config(
            rag_sytem_config=RAGConfig(
                id="",
                hash="",
                name="",
                config_type="hippo-rag",
                embedding=RagEmbeddingConfig(**data),
                retrieval_config=RagRetrievalConfig(**data_r),
            )
        )
        RAGPrefectApplication.Instance().start()
        await RAGPrefectApplication.Instance().astart()
        await RAGPrefectApplication.Instance().create_usecase()

        # Build indexer components from loaded config and do a tiny indexing round
        config = ConfigLoaderImplementation.Instance()
        cfg_ent = QdrantEmbeddingStoreConfig(
            collection=str(EMBEDDING_CONFIG_GRAPH["id"]),
            dim=config.get_int(EMBEDDING_SIZE),
            distance=Distance.COSINE,
            namespace="entity",
        )
        cfg_chunk = QdrantEmbeddingStoreConfig(
            collection=str(EMBEDDING_CONFIG_GRAPH["id"]),
            dim=config.get_int(EMBEDDING_SIZE),
            distance=Distance.COSINE,
            namespace="chunk",
        )
        cfg_link = QdrantEmbeddingStoreConfig(
            collection=str(EMBEDDING_CONFIG_GRAPH["id"]),
            dim=config.get_int(EMBEDDING_SIZE),
            distance=Distance.COSINE,
            namespace="facts",
        )

        db = Neo4jGraphDB(
            Neo4jConfig(
                database="neo4j",
                node_label="Node",
                rel_type="LINKS",
                ppr_implementation="neo4j-gds",
            )
        )
        embedder = GrpcEmbeddClient(
            address=config.get_str(EMBEDDING_HOST),
            is_secure=config.get_bool(IS_EMBEDDING_HOST_SECURE),
            config=EmbeddingClientConfig(
                normalize=config.get_bool(EMEDDING_NORMALIZE),
                truncate=config.get_bool(TRUNCATE),
                truncate_direction=config.get_str(TRUNCATE_DIRECTION),
                prompt_name_doc=config.get_str(EMBEDDING_DOC_PROMPT_NAME),
                prompt_name_query=config.get_str(EMBEDDING_QUERY_PROMPT_NAME),
            ),
        )

        client = OpenAIAsyncLLM(
            ConfigOpenAI(
                base_url=llm.OPENAI_HOST,
                model=llm.OPENAI_MODEL,
                max_tokens=8129,
                api_key=llm.OPENAI_HOST_KEY,
                timeout=600,
                temperature=0.0,
                context_cutoff=int(128_000 * 0.90),
            )
        )

        indexer = HippoRAGIndexer(
            text_splitter=AdvancedSentenceSplitter(
                config=NodeSplitterConfig(
                    chunk_size=64,
                    chunk_overlap=32,
                    default_language="en",
                )
            ),
            vector_store_entity=QdrantEmbeddingStore(cfg_ent, embedder=embedder),
            vector_store_fact=QdrantEmbeddingStore(cfg_link, embedder=embedder),
            vector_store_chunk=QdrantEmbeddingStore(cfg_chunk, embedder=embedder),
            graph=db,
            openie=AsyncOpenIE(llm=client, config=OpenIEConfig()),
            state_store=PostgresDBStateStore(),
            config=IndexerConfig(
                synonymy_edge_topk=5,
                synonymy_edge_sim_threshold=0.9,
                number_of_parallel_requests=2,
            ),
        )

        content = (
            "Oliver Badman is a politician."
            "George Rankin is a politician."
            "Thomas Marwick is a politician."
            "Cinderella attended the royal ball."
            "Montebello is a part of Rockland County."
            "When the slipper fit perfectly, Cinderella was reunited with the prince."
            "George Rankin is a Firewareman."
            "The prince used the lost glass slipper to search the kingdom."
            "Erik Hort's birthplace is Montebello."
            "Marina is bom in Minsk."
            "Fabian was born in Jena."
        )

        # Minimal DB fixtures
        project = project_models.Project(
            version=0,
            name="test",
            year=0,
            address__country="",
            address__state="",
            address__county="",
            address__city="",
            address__street="",
            address__zip_code="",
            address__lat=0.0,
            address__long=0.0,
        )
        await project.save(force_create=True)

        sample = validation_models.TestSample(
            question_id="dummy",
            dataset_id="test",
            question="What ball Attended Cinderella",
            retrival_complexity=0,
            expected_answer="",
            expected_facts=[],
            expected_context="",
            question_type="",
            metatdata={},
            metadata_filter={},
        )
        await sample.save(force_create=True)

        # Index a small document
        result = await indexer.create_document(
            Document(
                id="",
                content=content,
                metadata={"test_sample_id": "history_book_of_events.pdf"},
            ),
            collection=f"{project.id}-{EMBEDDING_CONFIG_GRAPH['id']}",
        )
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()

        # Direct rag query via HippoRAG
        hippo_rag: HippoRAG = RAGUsecase.Instance().rag_llm  # type: ignore
        response = await hippo_rag.request(
            conversation=Conversation(
                messages=[
                    Message(
                        message="What ball Attendet Cinderella?", role=RoleType.User
                    )
                ],
                model="",
            )
        )
        if response.is_error():
            logger.error(response.get_error())
        assert response.is_ok()

        answer = response.get_ok()
        text = ""
        assert answer.generator is not None
        async for token in answer.generator:
            text += token
        logger.info(text)
        for node in answer.nodes:
            logger.info("%s %s", node.content, node.similarity)

        # Exercise the higher-level usecase path too
        gen_res = await RAGUsecase.Instance().generate_reponse(str(sample.id))
        if gen_res.is_error():
            logger.error(gen_res.get_error())
        assert gen_res.is_ok()

        # Shutdown + cleanup between runs
        await RAGPrefectApplication.Instance().ashutdown()
        RAGPrefectApplication.Instance().shutdown()
        SingletonMeta.clear_all()
        prov.restore()
        disable_local_logging()

    # ---------------- helpers ----------------

    def _compose_common_values(self) -> dict[str, object]:
        vals: dict[str, object] = {}
        # Postgres
        vals[POSTGRES_HOST] = self._pg_host
        vals[POSTGRES_PORT] = int(self._pg_port)
        vals[POSTGRES_USER] = "test"
        vals[POSTGRES_PASSWORD] = "test"
        vals[POSTGRES_DATABASE] = "test_db"

        # (optional) local log level
        vals[LOG_LEVEL] = "error"

        # Qdrant
        vals[QDRANT_HOST] = self._q_host
        vals[QDRANT_PORT] = int(self._q_http)
        vals[QDRANT_GRPC_PORT] = int(self._q_grpc)
        vals[QDRANT_PREFER_GRPC] = True
        vals[QDRANT_API_KEY] = ""  # local
        vals[VECTOR_COLLECTION] = "default_collection"

        # Runtime knobs
        vals[MAX_TOKENS] = 2048
        vals[PARALLEL_REQUESTS] = 1

        # OTEL off
        vals[OTEL_ENABLED] = False
        vals[OTEL_HOST] = ""
        vals[OTEL_INSECURE] = True
        vals[EMBEDD_CONFIG_TO_USE] = "dummy"

        # LLM defaults
        vals[OPENAI_MODEL] = llm.OPENAI_MODEL
        vals[OPENAI_HOST] = llm.OPENAI_HOST
        vals[llm.OPENAI_HOST_KEY] = llm.OPENAI_HOST_KEY

        # Embedding / rerank (optional)
        vals[EMBEDDING_HOST] = embedding.EMBEDDING_HOST
        vals[EMBEDDING_MODEL] = embedding.EMBEDDING_MODEL
        vals[IS_EMBEDDING_HOST_SECURE] = False
        vals[RERANK_HOST] = rerank.RERANKER_HOST

        # Guard EMBEDDING_SIZE
        try:
            vals[EMBEDDING_SIZE] = (
                int(embedding.EMBEDDING_SIZE) if embedding.EMBEDDING_SIZE else 0
            )
        except ValueError:
            vals[EMBEDDING_SIZE] = 0

        return vals

    def _compose_graph_values(self) -> dict[str, object]:
        vals: dict[str, object] = {}
        vals[NEO4J_HOST] = f"bolt://{self._neo_host}:{self._neo_bolt}"
        vals[NEO4J_USER] = NEO4J_USER_DEFAULT
        vals[NEO4J_PASSWORD] = NEO4J_PASS_DEFAULT

        vals[TOP_N_HIPPO_RAG] = 8
        vals[TOP_N_LINKINIG] = 6
        vals[PASSAGE_NODE_WEIGHT] = 0.05
        vals[QA_TOP_N] = 6
        vals[DAMPING] = 0.85
        return vals

    def _compose_mode_values(self, mode: str) -> dict[str, object]:
        return {RAG_TYPE: mode}


EMBEDDING_CONFIG_GRAPH = {
    "id": "e0bb18a4-8580-4a0d-904c-4af65bb9c696",
    "stored_config": {
        "id": "e0bb18a4-8580-4a0d-904c-4af65bb9c696",
        "hash": "cfdbabf7373162490cf5bb47b8a89925eeaaca157a1207f51bcb3254bd61ae98",
        "chunk_size": 512,
        "chunk_overlap": 128,
        "models": {
            "EMBEDDING_MODEL": embedding.EMBEDDING_MODEL,
            "OPENAI_MODEL": llm.OPENAI_MODEL,
        },
        "addition_information": {
            EMEDDING_NORMALIZE: True,
            TRUNCATE: True,
            TRUNCATE_DIRECTION: "right",
            EMBEDDING_DOC_PROMPT_NAME: "",
            EMBEDDING_QUERY_PROMPT_NAME: "",
            TEMPERATUR: 0.5,
            EMBEDDING_SIZE: embedding.EMBEDDING_SIZE,
            SYNONYME_EDEGE_TOP_N: 5,
            SYNONYMY_EDGE_SIM_THRESHOLD: 0.9,
        },
    },
}

RETRIVAL_CONFIG_GRAPH = {
    "id": "e0bb18a4-8580-4a0d-904c-4af65bb9c696",
    "stored_config": {
        "id": "e0bb18a4-8580-4a0d-904c-4af65bb9c696",
        "hash": "cfdbabf7373162490cf5bb47b8a89925eeaaca157a1207f51bcb3254bd61ae98",
        "generator_model": llm.OPENAI_MODEL,
        "temp": 0.0,
        "prompts": {},
        "addition_information": {
            TOP_N_HIPPO_RAG: 5,
            TOP_N_LINKINIG: 5,
            QA_TOP_N: 5,
            PASSAGE_NODE_WEIGHT: 0.5,
            DAMPING: 0.5,
            PPR_DIRECTED: "False",
            CHUNKS_TO_RETRIEVE_PPR_SEED: 100,
        },
    },
}
