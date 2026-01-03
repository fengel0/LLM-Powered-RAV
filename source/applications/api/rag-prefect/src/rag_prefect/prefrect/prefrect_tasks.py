from core.config_loader import ConfigLoaderImplementation
from core.singelton import SingletonMeta
from prefect.events import emit_event
from rag_pipline_service.usecase.rag import RAGUsecase
from domain.pipeline.events import EventName
from rag_prefect.application_startup import (
    RAGConfigLoaderApplication,
    RAGPrefectApplication,
)


async def generate_answer(sample_task: str) -> str:
    result = await RAGUsecase.Instance().generate_reponse(test_sample_id=sample_task)
    if result.is_error():
        raise result.get_error()
    return result.get_ok()


async def startup():
    SingletonMeta.clear_all()
    RAGConfigLoaderApplication.create(config_loader=ConfigLoaderImplementation.create())
    RAGConfigLoaderApplication.Instance().start()
    await RAGConfigLoaderApplication.Instance().astart()
    await RAGConfigLoaderApplication.Instance().create_usecase()

    config_result = await RAGConfigLoaderApplication.Instance().get_rag_config()
    if config_result.is_error():
        raise config_result.get_error()
    config = config_result.get_ok()

    await RAGConfigLoaderApplication.Instance().ashutdown()
    RAGConfigLoaderApplication.Instance().shutdown()

    RAGPrefectApplication.create(ConfigLoaderImplementation.create())
    RAGPrefectApplication.Instance().set_rag_config(config)
    RAGPrefectApplication.Instance().start()
    await RAGPrefectApplication.Instance().astart()
    await RAGPrefectApplication.Instance().create_usecase()


async def shutdown():
    await RAGPrefectApplication.Instance().ashutdown()
    RAGPrefectApplication.Instance().shutdown()


async def generate_ans(task_id: str):
    try:
        await startup()
        id = await generate_answer(sample_task=task_id)

        emit_event(
            event=EventName.EVALUATE_RAG_SYSTEM.value,
            resource={
                "prefect.resource.id": f"{task_id}",
                "prefect.resource.name": f"{id}",
            },
        )
    finally:
        await shutdown()
