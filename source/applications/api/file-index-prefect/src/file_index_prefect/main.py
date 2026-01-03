import asyncio

from core.config_loader import ConfigLoaderImplementation
from domain.database.config.model import RagEmbeddingConfig
from domain.pipeline.events import EventName
from file_converter_prefect.application_startup import ApplicationFileConverterPrefect
from file_index_prefect.prefect_task_convert import created_or_updated_file
from file_embedding_prefect.application_startup import (
    FileEmbeddingPrefectApplication,
    RAGEmbeddingConfigLoaderApplication,
)
from file_index_prefect.prefect_task_emedding import embedd_file
from file_embedding_prefect.settings import PARALLEL_REQUESTS
from file_uploader_prefect.application_startup import FileUploaderPrefect
from file_index_prefect.prefect_task_upload import upload_files
from prefect import serve
from prefect.automations import Automation
from prefect.events.actions import RunDeployment
from prefect.events.schemas.automations import EventTrigger
from prefect_core.base_deployment import DUMMY_ID, CustomFlow


async def get_embedding_config() -> RagEmbeddingConfig:
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
    return config


def get_embedding_flow(rag_cofig: RagEmbeddingConfig):
    FileEmbeddingPrefectApplication.create(
        config_loader=ConfigLoaderImplementation.Instance()
    )
    FileEmbeddingPrefectApplication.Instance().set_embedding_config(rag_cofig)
    embedding_flow = CustomFlow(embedd_file)  # type: ignore
    automation = Automation(
        name=EventName.FILE_CONVERTED.value,
        trigger=EventTrigger(
            expect={EventName.FILE_CONVERTED.value},
            posture="Reactive",  # type: ignore
            threshold=1,
        ),
        actions=[  # type: ignore
            RunDeployment(  # type: ignore
                deployment_id=DUMMY_ID,
                parameters={"file_id": "{{ event.resource.id.split('/')[-1] }}"},
            )
        ],
    )

    embedding_flow.add_automations([automation])
    return embedding_flow.to_deployment(  # type: ignore
        name=FileEmbeddingPrefectApplication.Instance().get_application_name(),
        tags=["file embedding"],
        # limit=config.get_int(PARALLEL_REQUESTS),
    )


def get_upload_flow():
    FileUploaderPrefect.create(ConfigLoaderImplementation.Instance())
    flow_file_upload = CustomFlow(upload_files)  # type: ignore
    return flow_file_upload.to_deployment(  # type: ignore
        name=FileUploaderPrefect.Instance().get_application_name(),
        tags=["file upload"],
    )


def get_file_converter_flow():
    ApplicationFileConverterPrefect.create(
        config_loader=ConfigLoaderImplementation.Instance()
    )
    convert_file_upload = CustomFlow(created_or_updated_file)  # type: ignore
    automation_file_create_automation = Automation(
        name=EventName.FILE_CREATED_UPDATES.value,
        trigger=EventTrigger(
            expect={EventName.FILE_CREATED_UPDATES.value},
            posture="Reactive",  # type: ignore
            threshold=1,
        ),
        actions=[  # type: ignore
            RunDeployment(  # type: ignore
                deployment_id=DUMMY_ID,
                parameters={"file_id": "{{ event.resource.id.split('/')[-1] }}"},
            )
        ],
    )
    convert_file_upload.add_automations([automation_file_create_automation])

    return convert_file_upload.to_deployment(  # type: ignore
        name=ApplicationFileConverterPrefect.Instance().get_application_name(),
        tags=["file upload"],
    )


if __name__ == "__main__":
    config = asyncio.run(get_embedding_config())
    config_loader = ConfigLoaderImplementation.create()
    embedding_flow = get_embedding_flow(config)
    file_upload_flow = get_upload_flow()
    file_converter_flow = get_file_converter_flow()

    serve(
        embedding_flow,
        file_upload_flow,
        file_converter_flow,
        limit=config_loader.get_int(PARALLEL_REQUESTS),
    )
