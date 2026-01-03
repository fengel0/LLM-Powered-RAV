# tests/test_e2e_env_provisioning.py
from __future__ import annotations

import logging
import os
from typing import Any
from unittest.mock import patch

from core.config_loader import ConfigLoaderImplementation, ConfigProvisioner
from core.logger import disable_local_logging
from core.singelton import SingletonMeta

from deployment_base.enviroment import vllm_reranker
from domain.database.config.model import (
    RAGConfig,
    RAGConfigTypeE,
    RagEmbeddingConfig,
    RagRetrievalConfig,
)
from domain_test.enviroment import embedding, llm, test_containers
from database.session import DatabaseConfig, PostgresSession
from testcontainers.postgres import PostgresContainer
from testcontainers.qdrant import QdrantContainer
from testcontainers.neo4j import Neo4jContainer

# DB models touched by the app
import validation_database.model as validation_models
import config_database.model as config_models
import project_database.model as project_models
import hippo_rag_database.model as hippo_rag_models
import fact_store_database.model as fact_models

from rag_prefect.application_startup import RAGPrefectApplication

from deployment_base.enviroment.log_env import (
    OTEL_ENABLED,
    OTEL_HOST,
    OTEL_INSECURE,
    SETTINGS as LOG_SETTINGS,
)

from deployment_base.enviroment.neo4j_env import (
    NEO4J_HOST,
    NEO4J_PASSWORD,
    NEO4J_USER,
    SETTINGS as NEO4J_SETTINGS,
)
from deployment_base.enviroment.openai_env import (
    MAX_TOKENS,
    OPENAI_HOST,
    OPENAI_MODEL,
    LLM_REQUEST_TIMEOUT,
    TEMPERATUR,
)
from deployment_base.enviroment.vllm_reranker import RERANK_HOST, RERANK_MODEL
from deployment_base.enviroment.vllm_reranker import SETTINGS as RERANK_SETTINGS
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
    SETTINGS as QDRANT_SETTINGS,
    SPARSE_MODEL,
    VECTOR_BATCH_SIZE,
    VECTOR_COLLECTION,
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
from rag_prefect.settings import (
    EMBEDD_CONFIG_TO_USE,
    PARALLEL_REQUESTS,
    RAG_TYPE,
    SETTINGS,
)
from deployment_base.enviroment.text_embedding import (
    SETTINGS_ALL as TEXT_EMBEDDING_SETTINGS,
)
from deployment_base.enviroment.simple_rag import (
    SYSTEM_PROMPT_SIMPLE,
    TOP_N_COUNT_DENSE,
    TOP_N_COUNT_RERANKER,
    TOP_N_COUNT_SPARSE,
    SETTINGS as SIMPLE_RAG_SETTINGS,
)
from deployment_base.enviroment.sub_question_rag import (
    CONDENSE_QUESTON_PROMPT,
    SUB_QUER_PROMPT,
    SUB_SYSTEM_PROMPT,
    QA_PROMPT,
    QUERY_WRAPPER_PROMPT,
    SETTINGS as SUB_SETTINGS,
)
from deployment_base.enviroment.hippo_rag import (
    CHUNKS_TO_RETRIEVE_PPR_SEED,
    DAMPING,
    PASSAGE_NODE_WEIGHT,
    PPR_DIRECTED,
    SYNONYME_EDEGE_TOP_N,
    SYNONYMY_EDGE_SIM_THRESHOLD,
    TOP_N_HIPPO_RAG,
    TOP_N_LINKINIG,
    QA_TOP_N,
    SETTINGS as HIPPO_RAG_SETTINGS,
)
from domain_test import AsyncTestBase

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

        # Neo4j (for graph mode)
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
    async def test_app_runs(self):
        # 1) SIMPLE / "naive"
        values = {
            **self._compose_common_values(),
            **self._compose_vector_values(),
            **self._compose_prompt_files("simple"),
            **self._compose_mode_values(RAGConfigTypeE.HYBRID),
        }
        prov = ConfigProvisioner(
            attributes=[
                *HIPPO_RAG_SETTINGS,
                *RERANK_SETTINGS,
                *OPENAI_SETTINGS,
                *QDRANT_SETTINGS,
                *LOG_SETTINGS,
                *SETTINGS,
                *TEXT_EMBEDDING_SETTINGS,
                *OPENAI_SETTINGS,
                *POSTGRES_SETTINGS,
                *NEO4J_SETTINGS,
                *SIMPLE_RAG_SETTINGS,
            ],
            values=values,
            create_missing_dirs=True,
        )
        prov.apply()

        data: dict[str, Any] = EMBEDDING_CONFIG_SIMPLE["stored_config"]  # type: ignore
        data_r: dict[str, Any] = SIMPLE_CONFIG["stored_config"]  # type: ignore

        RAGPrefectApplication.create(ConfigLoaderImplementation.create())
        RAGPrefectApplication.Instance().set_rag_config(
            rag_sytem_config=RAGConfig(
                id="",
                hash="",
                config_type="hybrid",
                name="",
                embedding=RagEmbeddingConfig(**data),
                retrieval_config=RagRetrievalConfig(**data_r),
            )
        )
        RAGPrefectApplication.Instance().start()
        await RAGPrefectApplication.Instance().astart()
        await RAGPrefectApplication.Instance().create_usecase()
        await RAGPrefectApplication.Instance().ashutdown()
        RAGPrefectApplication.Instance().shutdown()
        disable_local_logging()
        prov.restore()

        # 2) SUB mode
        values = {
            **self._compose_common_values(),
            **self._compose_vector_values(),
            **self._compose_prompt_files("sub"),
            **self._compose_mode_values(RAGConfigTypeE.SUBQUESTION),
        }
        prov = ConfigProvisioner(
            attributes=[
                *HIPPO_RAG_SETTINGS,
                *OPENAI_SETTINGS,
                *QDRANT_SETTINGS,
                *RERANK_SETTINGS,
                *LOG_SETTINGS,
                *SETTINGS,
                *TEXT_EMBEDDING_SETTINGS,
                *OPENAI_SETTINGS,
                *POSTGRES_SETTINGS,
                *NEO4J_SETTINGS,
                *SUB_SETTINGS,
            ],
            values=values,
            create_missing_dirs=True,
        )
        prov.apply()

        data: dict[str, Any] = EMBEDDING_CONFIG_SIMPLE["stored_config"]  # type: ignore
        data_r: dict[str, Any] = SUB_CONFIG["stored_config"]  # type: ignore

        RAGPrefectApplication.create(ConfigLoaderImplementation.create())
        RAGPrefectApplication.Instance().set_rag_config(
            rag_sytem_config=RAGConfig(
                id="",
                hash="",
                config_type="hippo-rag",
                name="",
                embedding=RagEmbeddingConfig(**data),
                retrieval_config=RagRetrievalConfig(**data_r),
            )
        )
        RAGPrefectApplication.Instance().start()
        await RAGPrefectApplication.Instance().astart()
        await RAGPrefectApplication.Instance().create_usecase()
        await RAGPrefectApplication.Instance().ashutdown()
        RAGPrefectApplication.Instance().shutdown()
        disable_local_logging()
        prov.restore()

        # 3) GRAPH mode (adds Neo4j + hippo knobs)
        values = {
            **self._compose_common_values(),
            **self._compose_prompt_files("graph"),
            **self._compose_mode_values(RAGConfigTypeE.HIPPO_RAG),
            **self._compose_graph_values(),
        }
        prov = ConfigProvisioner(
            attributes=[
                *OPENAI_SETTINGS,
                *QDRANT_SETTINGS,
                *LOG_SETTINGS,
                *RERANK_SETTINGS,
                *SETTINGS,
                *TEXT_EMBEDDING_SETTINGS,
                *OPENAI_SETTINGS,
                *POSTGRES_SETTINGS,
                *NEO4J_SETTINGS,
            ],
            values=values,
            create_missing_dirs=True,
        )
        prov.apply()

        data: dict[str, Any] = EMBEDDING_CONFIG_GRAPH["stored_config"]  # type: ignore
        data_r: dict[str, Any] = RETRIVAL_CONFIG_GRAPH["stored_config"]  # type: ignore

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
        await RAGPrefectApplication.Instance().ashutdown()
        RAGPrefectApplication.Instance().shutdown()
        disable_local_logging()
        prov.restore()

    # ---------------- helpers ----------------

    def _compose_common_values(self) -> dict[str, object]:
        vals: dict[str, object] = {}
        # Postgres
        vals[POSTGRES_HOST] = self._pg_host
        vals[POSTGRES_PORT] = int(self._pg_port)
        vals[POSTGRES_USER] = "test"
        vals[POSTGRES_PASSWORD] = "test"
        vals[POSTGRES_DATABASE] = "test_db"

        # Qdrant
        vals[QDRANT_HOST] = self._q_host
        vals[QDRANT_PORT] = int(self._q_http)
        vals[QDRANT_GRPC_PORT] = int(self._q_grpc)
        vals[QDRANT_PREFER_GRPC] = True
        vals[QDRANT_API_KEY] = ""  # local

        vals[VECTOR_COLLECTION] = "default_collection"

        # Runtime knobs
        vals[LLM_REQUEST_TIMEOUT] = 120
        vals[MAX_TOKENS] = 2048
        vals[PARALLEL_REQUESTS] = 1
        vals[EMBEDD_CONFIG_TO_USE] = "dummy"

        # OTEL off
        vals[OTEL_ENABLED] = False
        vals[OTEL_HOST] = ""
        vals[OTEL_INSECURE] = True

        # LLM defaults
        vals[OPENAI_MODEL] = llm.OPENAI_MODEL
        vals[OPENAI_HOST] = llm.OPENAI_HOST
        vals[llm.OPENAI_HOST_KEY] = llm.OPENAI_HOST_KEY

        # Embedding/rerank backends (optional)
        vals[EMBEDDING_HOST] = embedding.EMBEDDING_HOST
        vals[EMBEDDING_MODEL] = embedding.EMBEDDING_MODEL
        vals[IS_EMBEDDING_HOST_SECURE] = False
        vals[RERANK_HOST] = vllm_reranker.RERANK_HOST
        # If EMBEDDING_DIM is empty, cast will raise; guard with default
        try:
            vals[EMBEDDING_SIZE] = (
                int(embedding.EMBEDDING_SIZE) if embedding.EMBEDDING_SIZE else 0
            )
        except ValueError:
            vals[EMBEDDING_SIZE] = 0
        return vals

    def _compose_vector_values(self) -> dict[str, object]:
        return {
            TOP_N_COUNT_DENSE: 4,
            TOP_N_COUNT_SPARSE: 4,
            TOP_N_COUNT_RERANKER: 4,
            VECTOR_BATCH_SIZE: 16,
        }

    def _compose_graph_values(self) -> dict[str, object]:
        vals: dict[str, object] = {}
        vals[NEO4J_HOST] = f"bolt://{self._neo_host}:{self._neo_bolt}"
        vals[NEO4J_USER] = NEO4J_USER_DEFAULT
        vals[NEO4J_PASSWORD] = NEO4J_PASS_DEFAULT

        # Hippo-ish params
        vals[TOP_N_HIPPO_RAG] = 8
        vals[TOP_N_LINKINIG] = 6
        vals[PASSAGE_NODE_WEIGHT] = 0.05
        vals[QA_TOP_N] = 6
        vals[DAMPING] = 0.85

        try:
            vals[EMBEDDING_SIZE] = (
                int(embedding.EMBEDDING_SIZE) if embedding.EMBEDDING_SIZE else 0
            )
        except ValueError:
            vals[EMBEDDING_SIZE] = 0
        return vals

    def _compose_mode_values(self, mode: str) -> dict[str, object]:
        return {RAG_TYPE: mode}

    def _compose_prompt_files(self, mode: str) -> dict[str, object]:
        """
        Provide content for FileConfigAttribute-backed prompts; the provisioner
        will materialize files where the app expects them.
        """
        vals: dict[str, object] = {}

        # if mode == "simple":
        # vals[RETRIVAL_CONFIG] = json.dumps(SIMPLE_CONFIG)
        # elif mode == "sub":
        # vals[RETRIVAL_CONFIG] = json.dumps(SUB_CONFIG)
        # elif mode == "graph":
        # vals[RETRIVAL_CONFIG] = json.dumps(GRAPH_CONFIG)

        return vals


# ----- sample retrieval configs (as in your original) -----
SIMPLE_CONFIG = {
    "id": "e0bb18a4-8580-4a0d-904c-4af65bb9c696",
    "stored_config": {
        "id": "e0bb18a4-8580-4a0d-904c-4af65bb9c696",
        "hash": "cfdbabf7373162490cf5bb47b8a89925eeaaca157a1207f51bcb3254bd61ae98",
        "generator_model": llm.OPENAI_MODEL,
        "temp": 0.0,
        "prompts": {
            SYSTEM_PROMPT_SIMPLE: "You are a retrieval assistant. Answer strictly from context. Cite chunks by id if available.",
            SUB_SYSTEM_PROMPT: "Decompose complex questions into focused sub-queries. Return JSON list of sub-queries.",
            SUB_QUER_PROMPT: "Write 2–5 precise sub-queries for: {question}",
            CONDENSE_QUESTON_PROMPT: "Rewrite the follow-up to a standalone query using the chat history.",
            QA_PROMPT: "Given the retrieved context, answer the user succinctly. If missing info, say so.",
            QUERY_WRAPPER_PROMPT: "Query: {q}",
        },
        "addition_information": {
            RERANK_MODEL: vllm_reranker.RERANK_MODEL,
            TOP_N_COUNT_DENSE: 5,
            TOP_N_COUNT_SPARSE: 5,
            TOP_N_COUNT_RERANKER: 5,
        },
    },
}


SUB_CONFIG = {
    "id": "e0bb18a4-8580-4a0d-904c-4af65bb9c696",
    "stored_config": {
        "id": "e0bb18a4-8580-4a0d-904c-4af65bb9c696",
        "hash": "cfdbabf7373162490cf5bb47b8a89925eeaaca157a1207f51bcb3254bd61ae98",
        "generator_model": llm.OPENAI_MODEL,
        "temp": 0.0,
        "prompts": {
            SYSTEM_PROMPT_SIMPLE: "You are a retrieval assistant. Answer strictly from context. Cite chunks by id if available.",
            SUB_SYSTEM_PROMPT: "Decompose complex questions into focused sub-queries. Return JSON list of sub-queries.",
            SUB_QUER_PROMPT: "Write 2–5 precise sub-queries for: {question}",
            CONDENSE_QUESTON_PROMPT: "Rewrite the follow-up to a standalone query using the chat history.",
            QA_PROMPT: "Given the retrieved context, answer the user succinctly. If missing info, say so.",
            QUERY_WRAPPER_PROMPT: "Query: {q}",
        },
        "addition_information": {
            RERANK_MODEL: vllm_reranker.RERANK_MODEL,
            TOP_N_COUNT_DENSE: 5,
            TOP_N_COUNT_SPARSE: 5,
            TOP_N_COUNT_RERANKER: 5,
        },
    },
}

EMBEDDING_CONFIG_SIMPLE = {
    "id": "ed7331f9-0599-4a4c-bc9c-24bdd92f0fd0",
    "stored_config": {
        "id": "ed7331f9-0599-4a4c-bc9c-24bdd92f0fd0",
        "hash": "26322329fc0a84d7a0d207bfb84b23dcb6861428c3565096e51e3af8bb80492e",
        "chunk_size": 512,
        "chunk_overlap": 128,
        "models": {
            "EMBEDDING_MODEL": embedding.EMBEDDING_MODEL,
            SPARSE_MODEL: "Qdrant/bm25",
        },
        "addition_information": {
            EMEDDING_NORMALIZE: True,
            TRUNCATE: True,
            TRUNCATE_DIRECTION: "right",
            EMBEDDING_DOC_PROMPT_NAME: "",
            EMBEDDING_QUERY_PROMPT_NAME: "",
        },
    },
}


EMBEDDING_CONFIG_GRAPH = {
    "id": "e0bb18a4-8580-4a0d-904c-4af65bb9c696",
    "stored_config": {
        "id": "e0bb18a4-8580-4a0d-904c-4af65bb9c696",
        "hash": "cfdbabf7373162490cf5bb47b8a89925eeaaca157a1207f51bcb3254bd61ae98",
        "chunk_size": 512,
        "chunk_overlap": 128,
        "models": {
            "EMBEDDING_MODEL": embedding.EMBEDDING_MODEL,
            "OPENAI_MODEL": "llama3.2",
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
