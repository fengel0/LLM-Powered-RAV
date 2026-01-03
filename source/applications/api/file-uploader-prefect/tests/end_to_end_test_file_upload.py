# tests/test_file_uploader_prefect.py
import os
import logging
from unittest.mock import patch

from core.config_loader import ConfigLoaderImplementation
from core.singelton import SingletonMeta
from database.session import DatabaseConfig, PostgresSession
from testcontainers.postgres import PostgresContainer
from testcontainers.minio import MinioContainer

from file_uploader_prefect.prefrect.prefrect_tasks import upload_files
from file_uploader_prefect.application_startup import FileUploaderPrefect

from domain_test.enviroment.test_containers import MINIO_VERSION, POSTGRES_VERSION

from deployment_base.enviroment.log_env import LOG_SECRETS, LOG_LEVEL

from file_uploader_prefect.settings import (
    FILE_TYPES_TO_OBSERVE,
    OBSERVE_DIR,
)
from deployment_base.enviroment.minio_env import (
    S3_ACCESS_KEY,
    S3_HOST,
    S3_IS_SECURE,
    S3_SECRET_KEY,
    S3_SESSION_KEY,
)
from deployment_base.enviroment.postgres_env import (
    POSTGRES_DATABASE,
    POSTGRES_HOST,
    POSTGRES_PASSWORD,
    POSTGRES_PORT,
    POSTGRES_USER,
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
            image=POSTGRES_VERSION,
            username="testuser",
            password="testpassword",
            dbname="test-db",
        ).start()

        cls._minio = MinioContainer(
            image=MINIO_VERSION,
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
        for c in (getattr(cls, "_minio", None), getattr(cls, "_pg", None)):
            try:
                if c:
                    c.stop()
            except Exception as e:
                logger.warning("Failed to stop container: %s", e)
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
        SingletonMeta.clear_all()

    async def setup_method_async(self, test_name: str):
        # migrate DB schema for each test
        cfg = DatabaseConfig(
            host=self._pg_host,
            port=self._pg_port,
            database_name="test-db",
            username="testuser",
            password="testpassword",
        )
        try:
            PostgresSession._instances.clear()  # type: ignore[attr-defined]
        except Exception:
            pass
        PostgresSession.create(config=cfg, models=[file_models, project_models])  # type: ignore[arg-type]
        sess = PostgresSession.Instance()
        await sess.start()
        await sess.migrations()
        await sess.shutdown()

        # patch enviroment for the task — also *disable all Prefect logging sinks*
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
            OBSERVE_DIR: "./test_files",
            FILE_TYPES_TO_OBSERVE: "doc docx pptx ppt xls xls pdf",
            # prevent Prefect's temp server and its log handlers
            "PREFECT_SERVER_EPHEMERAL_STARTUP_TIMEOUT_SECONDS": "90",
        }
        self._env_patcher = patch.dict(os.environ, self._env, clear=True)
        self._env_patcher.start()
        SingletonMeta.clear_all()

    async def teardown_method_async(self, test_name: str):
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

        # flush/close Prefect handlers only (avoid writing to closed streams)
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
        # also quiet down noisy libs just in case
        for name in (
            "prefect",
            "prefect.client",
            "prefect.server",
            "httpx",
            "httpcore",
        ):
            logging.getLogger(name).setLevel(logging.CRITICAL)

    async def test_dataset_uploader(self) -> None:
        await upload_files()
