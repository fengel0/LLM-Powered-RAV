from core.singelton import SingletonMeta
from database.session import DatabaseConfig, PostgresSession
from testcontainers.postgres import PostgresContainer
from domain_test.database.project.project_database import TestProjectDatabase
import project_database.model as models
from project_database.project_db_implementation import PostgresDBProjectDatbase
from domain_test.enviroment import test_containers


class TestProjectDatabasePostgres(TestProjectDatabase):
    __test__ = True

    session: PostgresSession
    container: PostgresContainer
    cfg: DatabaseConfig

    # --------------------------------------------------------------------- #
    # lifecycle
    # --------------------------------------------------------------------- #
    def setup_method_sync(self, test_name: str):
        """Start ephemeral Postgres and prepare DB config."""
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
        """Create session, run migrations, and wire the DAL under test."""
        # Ensure a clean session singleton between tests
        PostgresSession._instances = {}  # type: ignore[attr-defined]

        self.session = PostgresSession.create(  # type: ignore[assignment]
            config=self.cfg,
            models=[models],
        )
        await self.session.start()
        await self.session.migrations()

        # System under test
        self.db = PostgresDBProjectDatbase()

    def teardown_method_sync(self, test_name: str):
        """Stop container and clear singletons so the next test is clean."""
        try:
            self.container.stop()
        finally:
            SingletonMeta.clear_all()

    async def teardown_method_async(self, test_name: str):
        """Shutdown DB session."""
        await self.session.shutdown()
