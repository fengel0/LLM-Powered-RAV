from core.config_loader import ConfigLoader
from deployment_base.enviroment import (
    advanced_chunker,
    qdrant_env,
    text_embedding,
)
from domain.database.config.model import RagEmbeddingConfig


def update_simple(
    config: RagEmbeddingConfig, config_loader: ConfigLoader
) -> RagEmbeddingConfig:
    result = config_loader.load_values(qdrant_env.SETTINGS)
    if result.is_error():
        raise result.get_error()

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
    config.models[qdrant_env.SPARSE_MODEL] = config_loader.get_str(
        qdrant_env.SPARSE_MODEL
    )

    return config
