# tests/test_evaluator_database_postgres.py
import logging

from core.singelton import SingletonMeta
from testcontainers.postgres import PostgresContainer

from core.logger import init_logging
from database.session import DatabaseConfig, PostgresSession
import validation_database.model as validation_models
from validation_database.validation_db_implementation import PostgresDBEvaluatorDatabase

from domain_test.database.validation.evaluator_database import TestDBEvaluatorDatabase
from domain_test.enviroment import test_containers

init_logging("info")
logger = logging.getLogger(__name__)


class TestPostgresEvaluatorDatabase(TestDBEvaluatorDatabase):
    """
    Concrete runner: spins up Postgres and runs the generic evaluator suite.
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
            models=[validation_models],
        )
        await self.session.start()
        await self.session.migrations()

        # System under test
        self.evaluator_db = PostgresDBEvaluatorDatabase()

    def teardown_method_sync(self, test_name: str):
        try:
            self.container.stop()
        finally:
            # Clear app-level singletons so the next test run is clean
            SingletonMeta.clear_all()

    async def teardown_method_async(self, test_name: str):
        await self.session.shutdown()
