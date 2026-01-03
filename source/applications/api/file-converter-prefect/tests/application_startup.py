# tests/test_e2e_env_provisioning.py
from __future__ import annotations

import os
import logging
from unittest.mock import patch

from core.singelton import SingletonMeta
from database.session import DatabaseConfig, PostgresSession
from testcontainers.minio import MinioContainer
from testcontainers.postgres import PostgresContainer
import file_database.model as file_models
import project_database.model as project_models

from file_converter_prefect.application_startup import (
    ApplicationFileConverterPrefect,
)

from deployment_base.enviroment import openai_env, minio_env, postgres_env
from deployment_base.enviroment.openai_env import (
    LLM_REQUEST_TIMEOUT,
    OPENAI_MODEL,
    OPENAI_KEY,
    OPENAI_HOST,
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


# config keys / SETTINGS
from file_converter_prefect.settings import (
    FILE_CONVERTER_API,
    PROMPT,
    REQUEST_TIMEOUT_IN_SECONDS,
    SETTINGS,
    SYSTEM_PROMPT,
)

from core.config_loader import ConfigLoaderImplementation, ConfigProvisioner
from domain_test import AsyncTestBase

logger = logging.getLogger(__name__)


class TestHippoImplementation(AsyncTestBase):
    __test__ = True

    # -------------------- class-level: start/stop containers -------------------
    @classmethod
    def setup_class_sync(cls):
        # MinIO
        cls._minio = MinioContainer().with_exposed_ports(9000).start()
        # Postgres
        cls._postgres = PostgresContainer(
            image="postgres:16-alpine",
            username="test",
            password="test",
            dbname="test_db",
        ).start()

        # cache endpoints
        cls._pg_host = cls._postgres.get_container_host_ip()
        cls._pg_port = int(cls._postgres.get_exposed_port(5432))
        cls._s3_host = cls._minio.get_container_host_ip()
        cls._s3_port = int(cls._minio.get_exposed_port(9000))

    @classmethod
    def teardown_class_sync(cls):
        for c in (getattr(cls, "_postgres", None), getattr(cls, "_minio", None)):
            try:
                if c:
                    c.stop()
            except Exception as e:
                logger.warning("Failed to stop container: %s", e)

    # ------------------------ per-test setup / teardown ------------------------
    def setup_method_sync(self, test_name: str):
        # Compose values for infra; everything else comes from SETTINGS defaults
        self._values = self._compose_env_values()

        # Provision enviroment/files
        self._provisioner = ConfigProvisioner(
            attributes=[
                *openai_env.SETTINGS,
                *minio_env.SETTINGS,
                *postgres_env.SETTINGS,
                *SETTINGS,
            ],
            values=self._values,
            create_missing_dirs=True,
        )
        self._provisioner.apply()

        # Disable Prefect ephemeral API server just for the test
        self._prefect_env = {
            "PREFECT_API_ENABLE_EPHEMERAL_SERVER": "false",
            "PREFECT_SERVER_EPHEMERAL_STARTUP_TIMEOUT_SECONDS": "90",
        }
        self._env_patcher = patch.dict(os.environ, self._prefect_env, clear=False)
        self._env_patcher.start()

        # keep singletons clean between tests
        SingletonMeta.clear_all()

    async def setup_method_async(self, test_name: str):
        # optional: ensure DB is reachable; create + shutdown a session quickly
        cfg = DatabaseConfig(
            host=os.environ[POSTGRES_HOST],
            port=str(os.environ[POSTGRES_PORT]),
            database_name=os.environ[POSTGRES_DATABASE],
            username=os.environ[POSTGRES_USER],
            password=os.environ[POSTGRES_PASSWORD],
        )
        PostgresSession.create(config=cfg, models=[file_models, project_models])  # type: ignore[arg-type]
        sess = PostgresSession.Instance()
        await sess.start()
        await sess.migrations()
        await sess.shutdown()
        SingletonMeta.clear_all()

    def teardown_method_sync(self, test_name: str):
        # restore enviroment/files
        try:
            if hasattr(self, "_provisioner"):
                self._provisioner.restore()
        finally:
            # stop enviroment patch
            try:
                self._env_patcher.stop()
            except Exception:
                pass

            # flush/close Prefect logging handlers (don’t rip out all handlers)
            root = logging.getLogger()
            for h in list(root.handlers):
                if (
                    "prefect" in h.__class__.__name__.lower()
                    or "prefect" in str(h).lower()
                ):
                    try:
                        h.flush()
                    except Exception:
                        pass
                    try:
                        h.close()
                    except Exception:
                        pass

            # clean sessions/singletons
            try:
                SingletonMeta.clear_all()
            except Exception:
                pass

    # -------------------------------- the test --------------------------------
    async def test_embedd_file_runs_with_provisioned_env(self):
        # Database/S3 envs are set
        for k in (
            POSTGRES_HOST,
            POSTGRES_PORT,
            POSTGRES_DATABASE,
            POSTGRES_USER,
            POSTGRES_PASSWORD,
        ):
            assert os.environ.get(k), f"{k} should be set"

        for k in (S3_HOST, S3_ACCESS_KEY, S3_SECRET_KEY, S3_SESSION_KEY, S3_IS_SECURE):
            assert os.environ.get(k) is not None, f"{k} should be set (empty allowed)"

        # App lifecycle should run with provisioned enviroment
        ApplicationFileConverterPrefect.create(
            config_loader=ConfigLoaderImplementation.create()
        )
        ApplicationFileConverterPrefect.Instance().start()
        await ApplicationFileConverterPrefect.Instance().astart()
        await ApplicationFileConverterPrefect.Instance().create_usecase()
        await ApplicationFileConverterPrefect.Instance().ashutdown()
        ApplicationFileConverterPrefect.Instance().shutdown()

    # ------------------------------- helpers ----------------------------------
    def _compose_env_values(self) -> dict[str, object]:
        vals: dict[str, object] = {}

        # Postgres
        vals[POSTGRES_HOST] = self._pg_host
        vals[POSTGRES_PORT] = self._pg_port
        vals[POSTGRES_USER] = "test"
        vals[POSTGRES_PASSWORD] = "test"
        vals[POSTGRES_DATABASE] = "test_db"

        vals[SYSTEM_PROMPT] = "test"
        vals[PROMPT] = "test"
        vals[OPENAI_HOST] = "http://127.0.0.1::11434"
        vals[OPENAI_MODEL] = "model"
        vals[OPENAI_KEY] = " dmuu"
        vals[LLM_REQUEST_TIMEOUT] = 60
        vals[FILE_CONVERTER_API] = "http://127.0.0.1"
        vals[REQUEST_TIMEOUT_IN_SECONDS] = 60

        # MinIO (S3) – most non-AWS clients want host:port
        vals[S3_HOST] = f"{self._s3_host}:{self._s3_port}"
        vals[S3_ACCESS_KEY] = "minioadmin"
        vals[S3_SECRET_KEY] = "minioadmin"
        vals[S3_SESSION_KEY] = ""  # optional
        vals[S3_IS_SECURE] = False

        return vals
