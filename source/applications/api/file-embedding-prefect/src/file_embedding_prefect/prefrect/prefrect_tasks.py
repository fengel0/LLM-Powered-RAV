from core.config_loader import ConfigLoaderImplementation
from file_embedding_pipline_service.usecase.embbeding_document import (
    EmbeddFilePiplineUsecase,
)
from prefect import logging, task
from file_embedding_prefect.application_startup import (
    FileEmbeddingPrefectApplication,
    RAGEmbeddingConfigLoaderApplication,
)


@task
async def startup():
    RAGEmbeddingConfigLoaderApplication.create(
        config_loader=ConfigLoaderImplementation.create()
    )
    RAGEmbeddingConfigLoaderApplication.Instance().start()
    await RAGEmbeddingConfigLoaderApplication.Instance().astart()
    await RAGEmbeddingConfigLoaderApplication.Instance().create_usecase()

    config_result = (
        await RAGEmbeddingConfigLoaderApplication.Instance().get_rag_config()
    )
    if config_result.is_error():
        raise config_result.get_error()
    config = config_result.get_ok()

    await RAGEmbeddingConfigLoaderApplication.Instance().ashutdown()
    RAGEmbeddingConfigLoaderApplication.Instance().shutdown()

    FileEmbeddingPrefectApplication.create(ConfigLoaderImplementation.create())
    FileEmbeddingPrefectApplication.Instance().set_embedding_config(config)
    FileEmbeddingPrefectApplication.Instance().start()
    await FileEmbeddingPrefectApplication.Instance().astart()
    await FileEmbeddingPrefectApplication.Instance().create_usecase()


async def shutdown():
    await FileEmbeddingPrefectApplication.Instance().ashutdown()
    FileEmbeddingPrefectApplication.Instance().shutdown()


@task(retries=3)
async def embedd_file_(file_id: str):
    logger = logging.get_run_logger()
    result = await EmbeddFilePiplineUsecase.Instance().embedd_file(file_id=file_id)
    if result.is_error():
        logger.error(f"{result.get_error()}")
        raise result.get_error()
    logger.info(f"converted {file_id}")


async def embedd_file(file_id: str):
    try:
        await startup()
        await embedd_file_(file_id=file_id)
    finally:
        await shutdown()
