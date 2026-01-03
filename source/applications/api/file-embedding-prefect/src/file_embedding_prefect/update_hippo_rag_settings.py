from core.config_loader import ConfigLoader
from domain.database.config.model import RagEmbeddingConfig
from deployment_base.enviroment import (
    advanced_chunker,
    openai_env,
    text_embedding,
    hippo_rag,
)


def update_graph(
    config: RagEmbeddingConfig, config_loader: ConfigLoader
) -> RagEmbeddingConfig:
    config.addition_information = {}

    config.chunk_size = config_loader.get_int(advanced_chunker.CHUNK_SIZE)
    config.chunk_overlap = config_loader.get_int(advanced_chunker.CHUNK_OVERLAB)

    # ------

    config.addition_information[text_embedding.EMEDDING_NORMALIZE] = (
        config_loader.get_bool(text_embedding.EMEDDING_NORMALIZE)
    )
    config.addition_information[text_embedding.TRUNCATE] = config_loader.get_bool(
        text_embedding.TRUNCATE
    )
    config.addition_information[text_embedding.TRUNCATE_DIRECTION] = (
        config_loader.get_str(text_embedding.TRUNCATE_DIRECTION)
    )
    config.addition_information[text_embedding.EMBEDDING_DOC_PROMPT_NAME] = (
        config_loader.get_str(text_embedding.EMBEDDING_DOC_PROMPT_NAME)
    )
    config.addition_information[text_embedding.EMBEDDING_QUERY_PROMPT_NAME] = (
        config_loader.get_str(text_embedding.EMBEDDING_QUERY_PROMPT_NAME)
    )
    config.models[text_embedding.EMBEDDING_MODEL] = config_loader.get_str(
        text_embedding.EMBEDDING_MODEL
    )

    # ------

    config.models[openai_env.OPENAI_MODEL] = config_loader.get_str(
        openai_env.OPENAI_MODEL
    )
    config.addition_information[openai_env.TEMPERATUR] = config_loader.get_float(
        openai_env.TEMPERATUR
    )

    # ------

    config.addition_information[hippo_rag.EMBEDDING_SIZE] = config_loader.get_int(
        hippo_rag.EMBEDDING_SIZE
    )

    config.addition_information[hippo_rag.SYNONYME_EDEGE_TOP_N] = config_loader.get_int(
        hippo_rag.SYNONYME_EDEGE_TOP_N
    )
    config.addition_information[hippo_rag.SYNONYMY_EDGE_SIM_THRESHOLD] = (
        config_loader.get_float(hippo_rag.SYNONYMY_EDGE_SIM_THRESHOLD)
    )

    return config
