# tests/test_dataset_uploader_prefect.py
import os
import logging
from unittest.mock import patch

from core.config_loader import ConfigLoaderImplementation
from core.singelton import SingletonMeta
from database.session import DatabaseConfig, PostgresSession
from testcontainers.postgres import PostgresContainer
from dataset_loader_prefect.application_startup import ApplicationDatasetloader
from dataset_loader_prefect.prefrect.prefrect_tasks import upload_dataset
import validation_database.model as models

from deployment_base.enviroment.log_env import (
    OTEL_INSECURE,
    OTEL_HOST,
    OTEL_ENABLED,
    LOG_LEVEL,
    LOG_SECRETS,
)


from deployment_base.enviroment.postgres_env import (
    POSTGRES_PORT,
    POSTGRES_USER,
    POSTGRES_DATABASE,
    POSTGRES_HOST,
    POSTGRES_PASSWORD,
)


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

        cls._pg_host = cls._pg.get_container_host_ip()
        cls._pg_port = str(cls._pg.get_exposed_port(5432))

    @classmethod
    def teardown_class_sync(cls):
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
        PostgresSession.create(config=cfg, models=[models])  # type: ignore[arg-type]
        sess = PostgresSession.Instance()
        await sess.start()
        await sess.migrations()
        await sess.shutdown()
        SingletonMeta.clear_all()

    async def teardown_method_async(self, test_name: str):
        try:
            await PostgresSession.Instance().shutdown()
        except Exception:
            pass

    def teardown_method_sync(self, test_name: str):
        # Only flush/close Prefect-related handlers. Do NOT remove all root handlers.
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

    async def test_dataset_uploader(self) -> None:
        self._env = {
            LOG_LEVEL: "info",
            LOG_SECRETS: "true",
            POSTGRES_HOST: self._pg_host,
            POSTGRES_PORT: self._pg_port,
            POSTGRES_DATABASE: "test-db",
            POSTGRES_USER: "testuser",
            POSTGRES_PASSWORD: "testpassword",
            OTEL_ENABLED: "false",
            OTEL_HOST: "localhost:4317",
            OTEL_INSECURE: "false",
            # prevent Prefect from spawning the temporary API server in tests
            "PREFECT_API_ENABLE_EPHEMERAL_SERVER": "false",
            # keep if you need it on CI; harmless otherwise
            "PREFECT_SERVER_EPHEMERAL_STARTUP_TIMEOUT_SECONDS": "90",
        }

        with patch.dict(os.environ, self._env, clear=True):
            await upload_dataset()
