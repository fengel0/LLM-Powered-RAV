# tests/test_system_config_database_postgres.py
import logging

from core.singelton import SingletonMeta
from testcontainers.postgres import PostgresContainer

from core.logger import init_logging
from database.session import DatabaseConfig, PostgresSession
import config_database.model as config_models
from config_database.db_implementation import (
    PostgresRAGConfigDatabase,
    PostgresRAGEmbeddingConfigDatabase,
    PostgresRAGRetrievalConfigDatabase,
    PostgresSystemConfigDatabase,
)
from domain.database.config.model import EvaluationConfig
from domain_test.enviroment import test_containers

from domain_test.database.config.config_db_test import (
    TestDBSystemConfigDatabase,
    TestRAGConfigDatabase,
)

init_logging("info")
logger = logging.getLogger(__name__)


class TestPostgresSystemConfigDatabase(TestDBSystemConfigDatabase):
    """
    Concrete runner: spins up Postgres and runs the generic system-config suite.
    """

    __test__ = True

    session: PostgresSession
    container: PostgresContainer
    cfg: DatabaseConfig

    # ----------------------------- lifecycle ----------------------------- #
    def setup_method_sync(self, test_name: str):
        self.container = PostgresContainer(
            image=test_containers.POSTGRES_VERSION,
            username="test",
            password="test",
            dbname="test_db",
        )
        self.container.start()

        self.cfg = DatabaseConfig(
            host=self.container.get_container_host_ip(),
            port=str(self.container.get_exposed_port(self.container.port)),
            database_name="test_db",
            username="test",
            password="test",
        )

    async def setup_method_async(self, test_name: str):
        # Ensure a clean session singleton between tests
        PostgresSession._instances = {}  # type: ignore[attr-defined]

        self.session = PostgresSession.create(  # type: ignore[assignment]
            config=self.cfg,
            models=[config_models],  # register Config DB models
        )
        await self.session.start()
        await self.session.migrations()

        # System under test
        self.db = PostgresSystemConfigDatabase(model=EvaluationConfig)

    def teardown_method_sync(self, test_name: str):
        try:
            self.container.stop()
        finally:
            # Clear app-level singletons so the next test run is clean
            SingletonMeta.clear_all()

    async def teardown_method_async(self, test_name: str):
        await self.session.shutdown()


class TestPostgresRAGConfigDatabase(TestRAGConfigDatabase):
    """
    Concrete runner: spins up Postgres and runs the generic system-config suite.
    """

    __test__ = True

    session: PostgresSession
    container: PostgresContainer
    cfg: DatabaseConfig

    # ----------------------------- lifecycle ----------------------------- #
    def setup_method_sync(self, test_name: str):
        self.container = PostgresContainer(
            image=test_containers.POSTGRES_VERSION,
            username="test",
            password="test",
            dbname="test_db",
        )
        self.container.start()

        self.cfg = DatabaseConfig(
            host=self.container.get_container_host_ip(),
            port=str(self.container.get_exposed_port(self.container.port)),
            database_name="test_db",
            username="test",
            password="test",
        )

    async def setup_method_async(self, test_name: str):
        # Ensure a clean session singleton between tests
        PostgresSession._instances = {}  # type: ignore[attr-defined]

        self.session = PostgresSession.create(  # type: ignore[assignment]
            config=self.cfg,
            models=[config_models],  # register Config DB models
        )
        await self.session.start()
        await self.session.migrations()

        # System under test
        self.db_rag = PostgresRAGConfigDatabase()
        self.db_retrival = PostgresRAGRetrievalConfigDatabase()
        self.db_embedding = PostgresRAGEmbeddingConfigDatabase()

    def teardown_method_sync(self, test_name: str):
        try:
            self.container.stop()
        finally:
            # Clear app-level singletons so the next test run is clean
            SingletonMeta.clear_all()

    async def teardown_method_async(self, test_name: str):
        await self.session.shutdown()
