# tests/test_e2e_env_provisioning_embedding_pipeline.py
from __future__ import annotations

import logging
from typing import Any

import config_database.model as config_models
import file_database.model as file_models
import hippo_rag_database.model as hippo_rag_models
from core.config_loader import ConfigLoaderImplementation, ConfigProvisioner
from core.logger import disable_local_logging
from core.singelton import SingletonMeta
from database.session import DatabaseConfig, PostgresSession
from deployment_base.enviroment.advanced_chunker import CHUNK_OVERLAB, CHUNK_SIZE

from deployment_base.enviroment.log_env import LOG_LEVEL, SETTINGS as LOG_SETTINGS


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
from deployment_base.enviroment.neo4j_env import (
    NEO4J_HOST,
    NEO4J_PASSWORD,
    NEO4J_USER,
    SETTINGS as NEO4J_SETTINGS,
)

from deployment_base.enviroment.openai_env import (
    MAX_TOKENS,
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
    EMBEDDING_SIZE,
    IS_EMBEDDING_HOST_SECURE,
)
from deployment_base.enviroment.text_embedding import (
    SETTINGS_ALL as TEXT_EMBEDDING_SETTINGS,
)
from deployment_base.enviroment.vllm_reranker import RERANK_HOST
from domain.rag.indexer.model import Document
from domain_test import AsyncTestBase
from file_embedding_pipline_service.usecase.embbeding_document import (
    EmbeddFilePiplineUsecase,
)
from file_embedding_prefect.application_startup import (
    FileEmbeddingPrefectApplication,
    RAGEmbeddingConfigLoaderApplication,
)
from file_embedding_prefect.settings import (
    EMBEDDING_CONFIG,
    EMBEDDING_IMPLEMENTATION,
    SETTINGS,
)
from hippo_rag.indexer import HippoRAGIndexer
from testcontainers.minio import MinioContainer
from testcontainers.neo4j import Neo4jContainer
from testcontainers.postgres import PostgresContainer
from testcontainers.qdrant import QdrantContainer

from domain_test.enviroment import llm, rerank, test_containers, embedding

logger = logging.getLogger(__name__)

NEO4J_USER_DEFAULT = "neo4j"
NEO4J_PASS_DEFAULT = "password"


class TestHippoImplementation(AsyncTestBase):
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

        cls._neo_host = cls._neo4j.get_container_host_ip()
        cls._neo_bolt_port = int(cls._neo4j.get_exposed_port(7687))

        logger.info("Containers started for E2E embedding pipeline test.")

    @classmethod
    def teardown_class_sync(cls):
        for c in (
            getattr(cls, "_postgres", None),
            getattr(cls, "_neo4j", None),
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
        # Prevent Prefect's ephemeral API server during tests

        SingletonMeta.clear_all()

    async def setup_method_async(self, test_name: str):
        # Prepare a clean DB schema each test
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

        PostgresSession.create(
            config=cfg, models=[file_models, hippo_rag_models, config_models]
        )  # type: ignore[arg-type]
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
            SingletonMeta.clear_all()
        except Exception:
            pass

        disable_local_logging()

    # -------------------------------- the test --------------------------------
    async def test_embedd_file_runs_with_provisioned_env(self):
        # Build enviroment for "hippo/graph" embedding implementation
        env_vals = self._compose_env_values_hippo()

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
                *NEO4J_SETTINGS,
            ],
            values=env_vals,
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

        # Start app
        FileEmbeddingPrefectApplication.create(
            config_loader=ConfigLoaderImplementation.create()
        )
        FileEmbeddingPrefectApplication.Instance().set_embedding_config(config=config)
        FileEmbeddingPrefectApplication.Instance().start()
        await FileEmbeddingPrefectApplication.Instance().astart()
        await FileEmbeddingPrefectApplication.Instance().create_usecase()

        # Grab the indexer from the usecase and index a tiny doc
        indexer: HippoRAGIndexer = EmbeddFilePiplineUsecase.Instance()._vectore_store  # type: ignore[attr-defined]

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

        # Simple query sanity check against the entity store
        res2 = await indexer._vector_store_entity.query("krämerbrückenfest", top_k=5)  # type: ignore[attr-defined]
        _ = res2.get_ok()  # ensure it returns without raising

        # Shutdown app
        await FileEmbeddingPrefectApplication.Instance().ashutdown()
        FileEmbeddingPrefectApplication.Instance().shutdown()
        SingletonMeta.clear_all()
        disable_local_logging()

    # ------------------------------- helpers ----------------------------------
    def _compose_env_values_hippo(self) -> dict[str, object]:
        vals: dict[str, object] = {}

        vals[LOG_LEVEL] = "debug"
        # Postgres
        vals[POSTGRES_HOST] = self._pg_host
        vals[POSTGRES_PORT] = str(self._pg_port)
        vals[POSTGRES_USER] = "test"
        vals[POSTGRES_PASSWORD] = "test"
        vals[POSTGRES_DATABASE] = "test_db"

        # LLM/embedding + context
        vals[OPENAI_HOST] = llm.OPENAI_HOST
        vals[OPENAI_MODEL] = llm.OPENAI_MODEL
        vals[OPENAI_KEY] = llm.OPENAI_HOST_KEY

        vals[EMBEDDING_IMPLEMENTATION] = "hippo_rag"

        # Qdrant
        vals[QDRANT_HOST] = self._q_host
        vals[QDRANT_PORT] = str(self._q_http_port)
        vals[QDRANT_GRPC_PORT] = str(self._q_grpc_port)
        vals[QDRANT_PREFER_GRPC] = "True"

        # Neo4j
        vals[NEO4J_HOST] = f"bolt://{self._neo_host}:{self._neo_bolt_port}"
        vals[NEO4J_USER] = NEO4J_USER_DEFAULT
        vals[NEO4J_PASSWORD] = NEO4J_PASS_DEFAULT

        # Optional services
        vals[EMBEDDING_HOST] = embedding.EMBEDDING_HOST
        vals[EMBEDDING_MODEL] = "dummy"
        vals[RERANK_HOST] = rerank.RERANKER_HOST

        # MinIO (S3)
        vals[S3_HOST] = f"{self._s3_host}:{self._s3_port}"
        vals[S3_ACCESS_KEY] = "minioadmin"
        vals[S3_SECRET_KEY] = "minioadmin"
        vals[S3_SESSION_KEY] = ""  # optional, empty string is fine
        vals[S3_IS_SECURE] = "False"
        # vals[IS_EMBEDDING_HOST_SECURE] = "False"

        # Chunking & dims
        vals[CHUNK_SIZE] = str(25)
        vals[CHUNK_OVERLAB] = str(5)
        vals[IS_EMBEDDING_HOST_SECURE] = False
        vals[MAX_TOKENS] = 1024
        vals["PREFECT_API_ENABLE_EPHEMERAL_SERVER"] = "false"
        vals["PREFECT_SERVER_EPHEMERAL_STARTUP_TIMEOUT_SECONDS"] = "90"

        vals[EMBEDDING_SIZE] = embedding.EMBEDDING_SIZE
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
