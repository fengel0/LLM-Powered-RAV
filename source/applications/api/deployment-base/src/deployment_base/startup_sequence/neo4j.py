from core.config_loader import ConfigLoader
from deployment_base.enviroment import neo4j_env

from deployment_base.application import AsyncLifetimeReg


class Neo4jStartupSequence(AsyncLifetimeReg):
    def __init__(self) -> None:
        super().__init__()

    async def start(self, config_loader: ConfigLoader):
        result = config_loader.load_values(neo4j_env.SETTINGS)
        if result.is_error():
            raise result.get_error()
        from hippo_rag_graph.graph_implementation import (
            Neo4jSession,
            Neo4jSessionConfig,
        )

        sess = Neo4jSession.create(
            Neo4jSessionConfig(
                uri=config_loader.get_str(neo4j_env.NEO4J_HOST),
                user=config_loader.get_str(neo4j_env.NEO4J_USER),
                password=config_loader.get_str(neo4j_env.NEO4J_PASSWORD),
            )
        )
        await sess.start()

    async def shutdown(self):
        from hippo_rag_graph.graph_implementation import Neo4jSession

        await Neo4jSession.Instance().shutdown()
