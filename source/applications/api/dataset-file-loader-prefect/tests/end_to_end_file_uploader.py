# tests/test_dataset_uploader_prefect.py
import os
import logging
from unittest.mock import patch

from core.config_loader import ConfigLoaderImplementation
from core.singelton import SingletonMeta
from database.session import DatabaseConfig, PostgresSession
from testcontainers.postgres import PostgresContainer
from testcontainers.minio import MinioContainer
from dataset_file_loader_prefect.application_startup import (
    DatasetFileUploaderApplication,
)
from dataset_file_loader_prefect.prefrect.prefrect_tasks import upload_dataset


from deployment_base.enviroment.log_env import (
    OTEL_INSECURE,
    OTEL_HOST,
    OTEL_ENABLED,
    LOG_LEVEL,
    LOG_SECRETS,
)

from deployment_base.enviroment.minio_env import (
    S3_HOST,
    S3_IS_SECURE,
    S3_SESSION_KEY,
    S3_ACCESS_KEY,
    S3_SECRET_KEY,
)


from deployment_base.enviroment.postgres_env import (
    POSTGRES_PORT,
    POSTGRES_USER,
    POSTGRES_DATABASE,
    POSTGRES_HOST,
    POSTGRES_PASSWORD,
)


import file_database.model as file_models
import project_database.model as project_models

from domain_test import AsyncTestBase

logger = logging.getLogger(__name__)


class TestPostgresSystemConfigDatabase(AsyncTestBase):
    __test__ = True

    @classmethod
    def setup_class_sync(cls):
        cls._pg = PostgresContainer(
            image="postgres:16-alpine",
            username="testuser",
            password="testpassword",
            dbname="test-db",
        ).start()

        cls._minio = MinioContainer(
            access_key="fake_access",
            secret_key="fake_secret",
        ).start()

        cls._pg_host = cls._pg.get_container_host_ip()
        cls._pg_port = str(cls._pg.get_exposed_port(5432))
        cls._s3_host = (
            f"{cls._minio.get_container_host_ip()}:{cls._minio.get_exposed_port(9000)}"
        )

    @classmethod
    def teardown_class_sync(cls):
        try:
            cls._minio.stop()
        except Exception:
            pass
        try:
            cls._pg.stop()
        except Exception:
            pass

    async def setup_method_async(self, test_name: str):
        cfg = DatabaseConfig(
            host=self._pg_host,
            port=self._pg_port,
            database_name="test-db",
            username="testuser",
            password="testpassword",
        )
        PostgresSession.create(config=cfg, models=[file_models, project_models])  # type: ignore[arg-type]
        sess = PostgresSession.Instance()
        await sess.start()
        await sess.migrations()
        await sess.shutdown()
        SingletonMeta.clear_all()

    async def teardown_method_async(self, test_name: str):
        # close any session left around (best-effort)
        try:
            await PostgresSession.Instance().shutdown()
        except Exception:
            pass

    def teardown_method_sync(self, test_name: str):
        # ---- Linen thread recommendation: flush/close Prefect handlers ----
        root = logging.getLogger()
        for h in root.handlers[:]:
            # heuristics: Prefect handlers typically stringify with "prefect" in repr
            if "prefect" in str(h).lower():
                try:
                    h.flush()
                except Exception:
                    pass
                try:
                    h.close()
                except Exception:
                    pass
            root.removeHandler(h)

        # keep things quiet for the rest of the session
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

    async def test_dataset_uploader(self) -> None:
        self._env = {
            LOG_LEVEL: "info",
            LOG_SECRETS: "true",
            S3_HOST: self._s3_host,
            S3_ACCESS_KEY: "fake_access",
            S3_SECRET_KEY: "fake_secret",
            S3_SESSION_KEY: "",
            S3_IS_SECURE: "false",
            POSTGRES_HOST: self._pg_host,
            POSTGRES_PORT: self._pg_port,
            POSTGRES_DATABASE: "test-db",
            POSTGRES_USER: "testuser",
            POSTGRES_PASSWORD: "testpassword",
            OTEL_ENABLED: "false",
            OTEL_HOST: "localhost:4317",
            OTEL_INSECURE: "false",
            "PREFECT_SERVER_EPHEMERAL_STARTUP_TIMEOUT_SECONDS": "90",
        }

        with patch.dict(os.environ, self._env, clear=True):
            await upload_dataset()
