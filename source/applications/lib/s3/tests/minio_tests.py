# tests/test_minio_file_storage.py
import logging

from testcontainers.minio import MinioContainer

from core.logger import init_logging
from core.singelton import SingletonMeta
from domain_test.storage.storage_test import TestDBFileStorage

from domain_test.enviroment import test_containers

from s3.minio import (
    MinioFileStorageConfig,
    MinioConnection,
    MinioFileStorage,
)

init_logging("debug".upper())
logger = logging.getLogger(__name__)


class TestMinioFileStorage(TestDBFileStorage):
    __test__ = True
    """
    Concrete runner: spins up a MinIO container and runs the generic suite.
    """

    container: MinioContainer

    # Per-test setup/teardown for clean isolation; switch to Class-level if preferred
    def setup_method_sync(self, test_name: str):
        # Start MinIO
        self.container = MinioContainer(
            image=test_containers.MINIO_VERSION
        ).with_exposed_ports(9000)
        self.container.start()

        host = f"{self.container.get_container_host_ip()}:{self.container.get_exposed_port(9000)}"
        logger.info(f"MinIO up @ {host}")

        # Configure + connect
        cfg = MinioFileStorageConfig(
            host=host,
            access_key=self.container.access_key,
            secret_key=self.container.secret_key,
            sesssion_token=None,
            secure=False,
        )

        # (Re)initialize connection for this test instance
        MinioConnection.init_connection(cfg)
        minio_client = MinioConnection.get_instance(cfg.host)
        self.storage = MinioFileStorage(minio_client)

        # bucket used by the base suite
        self.bucket = "test_bucket"

        # Stop the container; if you have a connection singleton map, clear it here as well

    def teardown_method_sync(self, test_name: str):
        try:
            self.container.stop()
            SingletonMeta.clear_all()
        finally:
            pass
