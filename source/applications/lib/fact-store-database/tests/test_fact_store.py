import logging

from core.singelton import SingletonMeta
from testcontainers.postgres import PostgresContainer
from domain_test.enviroment import test_containers

from core.logger import init_logging
from database.session import DatabaseConfig, PostgresSession

import fact_store_database.model as facts_models
from fact_store_database.state_holder import (
    PostgresDBFactStore,
)

from domain_test.database.facts.facts_store import TestDBFactsStore



init_logging("info")
logger = logging.getLogger(__name__)


class TestPostgresDBFactsStore(TestDBFactsStore):
    __test__ = True
    session: PostgresSession
    container: PostgresContainer
    cfg: DatabaseConfig

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
        self.session = PostgresSession.create(  # type: ignore[assignment]
            config=self.cfg,
            models=[facts_models],  # <-- register facts models
        )
        await self.session.start()
        await self.session.migrations()

        # System under test
        self.state_store = PostgresDBFactStore()

    def teardown_method_sync(self, test_name: str):
        self.container.stop()
        SingletonMeta.clear_all()

    async def teardown_method_async(self, test_name: str):
        await self.session.shutdown()
