from core.config_loader import ConfigLoader
from llama_index_extension.build_components import LLamaIndexHolder, LlamaIndexRAGConfig
from deployment_base.application import AsyncLifetimeReg
from deployment_base.enviroment import (
    qdrant_env,
    openai_env,
)


class LlamaIndexQdrantStartupSequence(AsyncLifetimeReg):
    def __init__(
        self,
    ) -> None:
        super().__init__()

    async def start(self, config_loader: ConfigLoader):
        from llama_index_extension.build_components import (
            LlamaIndexVectorStoreSessionConfig,
            LlamaIndexVectorStoreSession,
        )

        result = config_loader.load_values([*qdrant_env.SETTINGS])
        if result.is_error():
            raise result.get_error()

        config_v_db = LlamaIndexVectorStoreSessionConfig(
            qdrant_host=config_loader.get_str(qdrant_env.QDRANT_HOST),
            qdrant_port=config_loader.get_int(qdrant_env.QDRANT_PORT),
            qdrant_api_key=config_loader.get_str(qdrant_env.QDRANT_API_KEY),
            qdrant_grpc_port=config_loader.get_int(qdrant_env.QDRANT_GRPC_PORT),
            qdrant_prefer_grpc=config_loader.get_bool(qdrant_env.QDRANT_PREFER_GRPC),
            collection=config_loader.get_str(qdrant_env.VECTOR_COLLECTION),
            batch_size=int(config_loader.get_int(qdrant_env.VECTOR_BATCH_SIZE)),
        )

        LlamaIndexVectorStoreSession.create(config=config_v_db)  # type: ignore

    async def shutdown(self):
        from llama_index_extension.build_components import (
            LlamaIndexVectorStoreSession,
        )

        await LlamaIndexVectorStoreSession.Instance().close()


class LlamaIndexStartupSequence(AsyncLifetimeReg):
    def __init__(
        self,
    ) -> None:
        super().__init__()

    async def start(self, config_loader: ConfigLoader):
        result = config_loader.load_values(
            [
                *openai_env.SETTINGS_HOST,
            ]
        )
        if result.is_error():
            raise result.get_error()

        config_llm = LlamaIndexRAGConfig(
            base_url=config_loader.get_str(openai_env.OPENAI_HOST),
            api_key=config_loader.get_str(openai_env.OPENAI_KEY),
            timeout=config_loader.get_int(openai_env.LLM_REQUEST_TIMEOUT),
        )

        LLamaIndexHolder.create(  # type: ignore
            config=config_llm
        )

    async def shutdown(self):
        from llama_index_extension.build_components import (
            LlamaIndexVectorStoreSession,
        )

        await LlamaIndexVectorStoreSession.Instance().close()
