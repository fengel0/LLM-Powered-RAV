# tests/test_e2e_env_provisioning_embedding.py
from __future__ import annotations

import logging
from typing import Any
from domain.rag.indexer.model import Document
import os
from unittest.mock import patch

from deployment_base.enviroment.log_env import SETTINGS as LOG_SETTINGS
from deployment_base.enviroment.vllm_reranker import SETTINGS as RERANK_SETTINGS

from domain_test.enviroment import llm, test_containers, embedding, rerank
import file_database.model as file_models
import config_database.model as config_models
from core.config_loader import ConfigLoaderImplementation, ConfigProvisioner
from core.logger import disable_local_logging
from core.singelton import SingletonMeta
from database.session import DatabaseConfig, PostgresSession
from deployment_base.enviroment.minio_env import (
    S3_ACCESS_KEY,
    S3_HOST,
    S3_IS_SECURE,
    S3_SECRET_KEY,
    S3_SESSION_KEY,
)
from deployment_base.enviroment.minio_env import (
    SETTINGS as S3_SETTINGS,
)
from deployment_base.enviroment.openai_env import (
    OPENAI_HOST,
    OPENAI_KEY,
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
    QDRANT_GRPC_PORT,
    QDRANT_HOST,
    QDRANT_PORT,
    QDRANT_PREFER_GRPC,
    SETTINGS as QDRANT_SETTINGS,
)
from deployment_base.enviroment.text_embedding import (
    EMBEDDING_HOST,
    EMBEDDING_MODEL,
)
from deployment_base.enviroment.text_embedding import (
    SETTINGS_ALL as TEXT_EMBEDDING_SETTINGS,
)
from deployment_base.enviroment.vllm_reranker import RERANK_HOST
from domain_test import AsyncTestBase
from file_embedding_pipline_service.usecase.embbeding_document import (
    EmbeddFilePiplineUsecase,
)
from vector_db.qdrant_vector_store import LlamaIndexVectorStore
from file_embedding_prefect.application_startup import (
    FileEmbeddingPrefectApplication,
    RAGEmbeddingConfigLoaderApplication,
)
from file_embedding_prefect.settings import (
    EMBEDDING_CONFIG,
    EMBEDDING_IMPLEMENTATION,
    SETTINGS,
)
from testcontainers.minio import MinioContainer
from testcontainers.neo4j import Neo4jContainer
from testcontainers.postgres import PostgresContainer
from testcontainers.qdrant import QdrantContainer


logger = logging.getLogger(__name__)


class TestLlamaIndexImplementation(AsyncTestBase):
    __test__ = True

    # -------------------- class-level: start/stop containers -------------------
    @classmethod
    def setup_class_sync(cls):
        # Qdrant
        cls._qdrant = (
            QdrantContainer(image=test_containers.QDRANT_VERSION)
            .with_exposed_ports(6333)
            .with_exposed_ports(6334)
            .start()
        )
        # MinIO
        cls._minio = MinioContainer().with_exposed_ports(9000).start()
        # Neo4j
        # Postgres
        cls._postgres = PostgresContainer(
            image=test_containers.POSTGRES_VERSION,
            username="test",
            password="test",
            dbname="test_db",
        ).start()

        # cache endpoints
        cls._pg_host = cls._postgres.get_container_host_ip()
        cls._pg_port = int(cls._postgres.get_exposed_port(5432))

        cls._s3_host = cls._minio.get_container_host_ip()
        cls._s3_port = int(cls._minio.get_exposed_port(9000))

        cls._q_host = cls._qdrant.get_container_host_ip()
        cls._q_http_port = int(cls._qdrant.get_exposed_port(6333))
        cls._q_grpc_port = int(cls._qdrant.get_exposed_port(6334))

        logger.info("Containers started for embedding E2E test.")

    @classmethod
    def teardown_class_sync(cls):
        # stop in reverse-ish order
        for c in (
            getattr(cls, "_postgres", None),
            getattr(cls, "_minio", None),
            getattr(cls, "_qdrant", None),
        ):
            try:
                if c:
                    c.stop()
            except Exception as e:
                logger.warning("Failed to stop container: %s", e)

    # ------------------------ per-test setup / teardown ------------------------
    def setup_method_sync(self, test_name: str):
        # enviroment flags for Prefect (avoid ephemeral server noise in tests)
        self._prefect_env = {
            "PREFECT_API_ENABLE_EPHEMERAL_SERVER": "false",
            "PREFECT_SERVER_EPHEMERAL_STARTUP_TIMEOUT_SECONDS": "90",
        }
        self._env_patcher = patch.dict(os.environ, self._prefect_env, clear=False)
        self._env_patcher.start()

        SingletonMeta.clear_all()

    async def setup_method_async(self, test_name: str):
        # Prepare a clean DB schema each test (start → migrate → shutdown)
        cfg = DatabaseConfig(
            host=self._pg_host,
            port=str(self._pg_port),
            database_name="test_db",
            username="test",
            password="test",
        )
        try:
            PostgresSession._instances.clear()  # type: ignore[attr-defined]
        except Exception:
            pass

        PostgresSession.create(config=cfg, models=[file_models, config_models])  # type: ignore[arg-type]
        sess = PostgresSession.Instance()
        await sess.start()
        await sess.migrations()
        await sess.shutdown()
        SingletonMeta.clear_all()

    def teardown_method_sync(self, test_name: str):
        # Flush/close Prefect handlers so background threads don't write to closed streams
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

        try:
            self._env_patcher.stop()
        except Exception:
            pass

        try:
            SingletonMeta.clear_all()
        except Exception:
            pass

        # be extra quiet after test
        disable_local_logging()

    # -------------------------------- the test --------------------------------
    async def test_embedd_file_runs_with_provisioned_env(self):
        # ----- Phase 1: vector implementation -----
        vector_values = self._compose_env_values_vector()
        self._provisioner = ConfigProvisioner(
            attributes=[
                *OPENAI_SETTINGS,
                *QDRANT_SETTINGS,
                *LOG_SETTINGS,
                *SETTINGS,
                *S3_SETTINGS,
                *TEXT_EMBEDDING_SETTINGS,
                *OPENAI_SETTINGS,
                *POSTGRES_SETTINGS,
                *RERANK_SETTINGS,
            ],
            values=vector_values,
            create_missing_dirs=True,
        )
        self._provisioner.apply()

        RAGEmbeddingConfigLoaderApplication.create(
            config_loader=ConfigLoaderImplementation.create()
        )
        RAGEmbeddingConfigLoaderApplication.Instance().start()
        await RAGEmbeddingConfigLoaderApplication.Instance().astart()
        await RAGEmbeddingConfigLoaderApplication.Instance().create_usecase()

        config_result = (
            await RAGEmbeddingConfigLoaderApplication.Instance().get_rag_config()
        )
        if config_result.is_error():
            raise config_result.get_error()
        config = config_result.get_ok()

        await RAGEmbeddingConfigLoaderApplication.Instance().ashutdown()
        RAGEmbeddingConfigLoaderApplication.Instance().shutdown()

        FileEmbeddingPrefectApplication.create(
            config_loader=ConfigLoaderImplementation()
        )
        FileEmbeddingPrefectApplication.Instance().set_embedding_config(config=config)
        FileEmbeddingPrefectApplication.Instance().start()
        await FileEmbeddingPrefectApplication.Instance().astart()
        await FileEmbeddingPrefectApplication.Instance().create_usecase()

        indexer: LlamaIndexVectorStore = (
            EmbeddFilePiplineUsecase.Instance()._vectore_store
        )  # type: ignore[attr-defined]

        result = await indexer.create_document(
            doc=Document(
                id=" ",
                metadata={},
                content=(
                    "Ich mag das Krämerbrückenfest."
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
                ),
            ),
        )
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()

        await FileEmbeddingPrefectApplication.Instance().ashutdown()
        FileEmbeddingPrefectApplication.Instance().shutdown()
        SingletonMeta.clear_all()

        # clean up any local logging handlers attached during startup
        disable_local_logging()

    # ------------------------------- helpers ----------------------------------
    def _compose_env_values_vector(self) -> dict[str, object]:
        vals: dict[str, object] = {}
        # Postgres
        vals["LOG_LEVEL"] = "debug"
        vals[POSTGRES_HOST] = self._pg_host
        vals[POSTGRES_PORT] = self._pg_port
        vals[POSTGRES_USER] = "test"
        vals[POSTGRES_PASSWORD] = "test"
        vals[POSTGRES_DATABASE] = "test_db"

        # LLM/embedding config (placeholders)
        vals[OPENAI_HOST] = llm.OPENAI_HOST
        vals[OPENAI_MODEL] = llm.OPENAI_MODEL
        vals[OPENAI_KEY] = llm.OPENAI_HOST_KEY

        # Qdrant
        vals[QDRANT_HOST] = self._q_host
        vals[QDRANT_PORT] = self._q_http_port
        vals[QDRANT_GRPC_PORT] = self._q_grpc_port
        vals[QDRANT_PREFER_GRPC] = True

        # optional services
        vals[RERANK_HOST] = rerank.RERANKER_HOST
        vals[EMBEDDING_HOST] = embedding.EMBEDDING_HOST
        vals[EMBEDDING_MODEL] = "dummy"

        # MinIO (S3)
        vals[S3_HOST] = f"{self._s3_host}:{self._s3_port}"
        vals[S3_ACCESS_KEY] = "minioadmin"
        vals[S3_SECRET_KEY] = "minioadmin"
        vals[S3_SESSION_KEY] = ""  # optional
        vals[S3_IS_SECURE] = False

        vals[EMBEDDING_IMPLEMENTATION] = "vector"
        vals[EMBEDDING_CONFIG] = BASE_EMBEDD_CONFIG
        return vals


BASE_EMBEDD_CONFIG: dict[str, Any] = {
    "id": "83716762-7485-4316-a93f-f75d6df507c7",
    "stored_config": {
        "id": "",
        "chunk_size": 0,
        "chunk_overlap": 0,
        "models": {},
        "addition_information": {},
    },
}
