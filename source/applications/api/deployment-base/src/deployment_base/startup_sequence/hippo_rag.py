from types import ModuleType
from core.config_loader import ConfigLoader
from deployment_base.enviroment import qdrant_env

from deployment_base.application import AsyncLifetimeReg


class HippoRAGQdrantStartupSequence(AsyncLifetimeReg):
    _models: list[ModuleType | str]

    def __init__(self) -> None:
        super().__init__()

    async def start(self, config_loader: ConfigLoader):
        result = config_loader.load_values(qdrant_env.SETTINGS)
        if result.is_error():
            raise result.get_error()
        from hippo_rag_vectore_store.vector_store import (
            HippoRAGVectorStoreSession,
            QdrantConfig,
        )

        cfg_qdrant = QdrantConfig(
            host=config_loader.get_str(qdrant_env.QDRANT_HOST),
            port=config_loader.get_int(qdrant_env.QDRANT_PORT),
            api_key=config_loader.get_str(qdrant_env.QDRANT_API_KEY),
            grpc_port=config_loader.get_int(qdrant_env.QDRANT_GRPC_PORT),
            prefere_grpc=config_loader.get_bool(qdrant_env.QDRANT_PREFER_GRPC),
        )

        HippoRAGVectorStoreSession.create(config=cfg_qdrant)

    async def shutdown(self):
        from hippo_rag_vectore_store.vector_store import HippoRAGVectorStoreSession

        await HippoRAGVectorStoreSession.Instance().close()
