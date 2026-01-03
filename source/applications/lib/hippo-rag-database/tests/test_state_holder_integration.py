# tests/test_postgres_db_state_store.py import logging
import logging
from testcontainers.postgres import PostgresContainer
from core.singelton import SingletonMeta

import hippo_rag_database.model as model
from core.logger import init_logging
from database.session import DatabaseConfig, PostgresSession
from domain_test.hippo_rag.hippo_rag_database_test import TestDBStateStore
from hippo_rag_database.state_holder import PostgresDBStateStore
from domain_test.enviroment import test_containers

init_logging("info")
logger = logging.getLogger(__name__)

NEO4J_USER = "neo4j"
NEO4J_PASS = "ThisIsSomeDummyPassw0rd!"


class TestPostgresStateStore(TestDBStateStore):
    __test__ = True
    session: PostgresSession
    container: PostgresContainer
    cfg: DatabaseConfig

    # --------------------------- hooks ---------------------------

    def setup_method_sync(self, test_name: str):
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
            models=[model],
        )
        await self.session.start()
        await self.session.migrations()
        self.state_store = PostgresDBStateStore()

    def teardown_method_sync(self, test_name: str):
        self.container.stop()
        SingletonMeta.clear_all()
        logger.info(f"[{test_name}] Postgres container stopped")

    async def teardown_method_async(self, test_name: str):
        await self.session.shutdown()
        logger.info(f"[{test_name}] DB session shutdown complete")
