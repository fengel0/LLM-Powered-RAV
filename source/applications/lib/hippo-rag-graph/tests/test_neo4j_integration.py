# tests/test_graphdb_neo4j_async.py
import logging

from testcontainers.neo4j import Neo4jContainer
from core.logger import init_logging

from domain_test.hippo_rag.hippo_rag_graph_store_test import TestGraphDB
from hippo_rag_graph.graph_implementation import (
    Neo4jSession,
    Neo4jSessionConfig,
    Neo4jGraphDB,
    Neo4jConfig,
)
from domain_test.enviroment import test_containers

init_logging("info")
logger = logging.getLogger(__name__)

NEO4J_USER = "neo4j"
NEO4J_PASS = "ThisIsSomeDummyPassw0rd!"


class TestNeo4jGraphDBBase(TestGraphDB):
    __test__ = True
    container: Neo4jContainer
    uri: str

    def setup_method_sync(self, test_name: str):
        # Start container (sync)
        self.container = Neo4jContainer(
            image=test_containers.NEO4J_VERSION,
            username=NEO4J_USER,
            password=NEO4J_PASS,
        )
        self.container.with_env(
            "NEO4J_PLUGINS", '["apoc","graph-data-science"]'
        ).with_env("NEO4J_apoc_export_file_enabled", "true").with_env(
            "NEO4J_apoc_import_file_enabled", "true"
        ).with_env("NEO4J_apoc_import_file_use__neo4j__config", "true")
        self.container.with_exposed_ports(7687, 7474)
        self.container.start()

        host = self.container.get_container_host_ip()
        bolt_port = int(self.container.get_exposed_port(7687))
        self.uri = f"bolt://{host}:{bolt_port}"
        logger.info(f"[{test_name}] Neo4j container started at {self.uri}")

    async def setup_method_async(self, test_name: str):
        # Create + start session singleton
        sess = Neo4jSession.create(  # type: ignore[attr-defined]
            Neo4jSessionConfig(uri=self.uri, user=NEO4J_USER, password=NEO4J_PASS)
        )
        await sess.start()

        # Create DB wrapper and start
        self.db = Neo4jGraphDB(
            Neo4jConfig(database="neo4j", node_label="Node", rel_type="LINKS")
        )
        await self.db.start()
        logger.info(f"[{test_name}] Neo4j session started")

    async def teardown_method_async(self, test_name: str):
        logger.info(f"[{test_name}] stopping Neo4j session")
        try:
            # Gracefully shut down the session singleton if present
            await Neo4jSession.Instance().shutdown()  # type: ignore[attr-defined]
        except Exception as e:
            logger.warning(f"Neo4jSession shutdown warning: {e}")
        finally:
            # Clear any singleton references to avoid cross-test leakage
            try:
                Neo4jSession._instances.clear()  # type: ignore[attr-defined]
            except Exception:
                pass

    def teardown_method_sync(self, test_name: str):
        logger.info(f"[{test_name}] stopping Neo4j container")
        try:
            self.container.stop()
        finally:
            logger.info(f"[{test_name}] Neo4j container stopped")
