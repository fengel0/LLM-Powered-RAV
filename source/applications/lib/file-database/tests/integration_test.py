import logging
from domain_test.enviroment import test_containers
from testcontainers.postgres import PostgresContainer

from core.singelton import SingletonMeta

from core.logger import init_logging
from database.session import DatabaseConfig, PostgresSession
from file_database.file_db_implementation import PostgresFileDatabase
import file_database.model as file_model

from domain_test.database.file.file_database import TestFileDatabase

init_logging("info")
logger = logging.getLogger(__name__)


class TestFileDatabasePostgres(TestFileDatabase):
    __test__ = True
    db: PostgresFileDatabase
    session: PostgresSession
    container: PostgresContainer
    cfg: DatabaseConfig

    # --------------------------- hooks ---------------------------

    def setup_method_sync(self, test_name: str):
        # Start a disposable Postgres container for EACH test
        self.container = PostgresContainer(
            image=test_containers.POSTGRES_VERSION,
            username="test",
            password="test",
            dbname="test_db",
        ).start()

        self.cfg = DatabaseConfig(
            host=self.container.get_container_host_ip(),
            port=str(self.container.get_exposed_port(self.container.port)),
            database_name="test_db",
            username="test",
            password="test",
        )
        logger.info(f"[{test_name}] Postgres container started")

    async def setup_method_async(self, test_name: str):

        self.session = PostgresSession.create(  # type: ignore[assignment]
            config=self.cfg,
            models=[file_model],
        )
        await self.session.start()
        await self.session.migrations()
        self.db = PostgresFileDatabase()

    def teardown_method_sync(self, test_name: str):
        self.container.stop()
        SingletonMeta.clear_all()
        logger.info(f"[{test_name}] Postgres container stopped")

    async def teardown_method_async(self, test_name: str):
        await self.session.shutdown()
        logger.info(f"[{test_name}] DB session shutdown complete")

