# tests/test_file_uploader_prefect.py
import os
import logging
from unittest.mock import patch

from core.config_loader import ConfigLoaderImplementation
from core.singelton import SingletonMeta
from database.session import DatabaseConfig, PostgresSession
from file_converter_service.usecase.convert_file import ConvertFileToMarkdown
from s3.minio import FileStorageObject, MinioConnection, MinioFileStorage
from testcontainers.postgres import PostgresContainer
from testcontainers.minio import MinioContainer

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
from file_converter_api.application_startup import FileConverterAPIApplication


file_list = [
    "./tests/test_files/Leubingen09100Abschlussbericht.doc",
    "./tests/test_files/test_file.pptx",
    "./tests/test_files/test_file_page_split_with_text.docx",
    "./tests/test_files/llama2.pdf",
    "./tests/test_files/datenschutz.html",
    "./tests/test_files/09-100 Katalog Abb.9.doc",
]

dummy_bucket = "dummy_bucket"

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
        self._env_patcher = patch.dict(os.environ, self._env)
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

    async def test_file_conversion(self) -> None:
        FileConverterAPIApplication.create(ConfigLoaderImplementation.create())
        FileConverterAPIApplication.Instance().start()
        await FileConverterAPIApplication.Instance().astart()
        await FileConverterAPIApplication.Instance().create_usecase()

        connection = MinioConnection.get_instance(
            ConfigLoaderImplementation.Instance().get_str(S3_HOST)
        )
        file_storage = MinioFileStorage(connection)

        for file in file_list:
            with open(file, "rb") as f:
                content = f.read()
            filetype = file.split(".")[-1]
            filename = file.split("/")[-1]
            file_storage.upload_file(
                file=FileStorageObject(
                    filetype=filetype,
                    content=content,
                    bucket=dummy_bucket,
                    filename=filename,
                )
            )

        for file in file_list:
            filename = file.split("/")[-1]
            result = ConvertFileToMarkdown.Instance().convert_file(
                dummy_bucket, dummy_bucket, filename=filename
            )
            if result.is_error():
                logger.error(result.get_error())
            assert result.is_ok()

        await FileConverterAPIApplication.Instance().ashutdown()
        FileConverterAPIApplication.Instance().shutdown()
