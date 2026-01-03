from core.config_loader import ConfigLoaderImplementation
import asyncio
from domain.database.config.model import RagEmbeddingConfig
from prefect.automations import Automation
from prefect.events.schemas.automations import EventTrigger
from prefect.events.actions import RunDeployment
from prefect_core.base_deployment import ConcurrencyLimitConfig, CustomFlow, DUMMY_ID

from domain.pipeline.events import EventName

from file_embedding_prefect.application_startup import (
    FileEmbeddingPrefectApplication,
    RAGEmbeddingConfigLoaderApplication,
)
from file_embedding_prefect.prefrect.prefrect_tasks import embedd_file
from file_embedding_prefect.settings import PARALLEL_REQUESTS


async def main() -> RagEmbeddingConfig:
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


if __name__ == "__main__":
    config = asyncio.run(main())
    FileEmbeddingPrefectApplication.create(
        config_loader=ConfigLoaderImplementation.create()
    )
    FileEmbeddingPrefectApplication.Instance().set_embedding_config(config)

    config = ConfigLoaderImplementation.Instance()
    flow = CustomFlow(embedd_file)  # type: ignore
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

    flow.add_automations([automation])

    flow.serve(  # type: ignore
        name=FileEmbeddingPrefectApplication.Instance().get_application_name(),
        tags=["file embedding"],
        global_limit=ConcurrencyLimitConfig(limit=config.get_int(PARALLEL_REQUESTS)),
        limit=config.get_int(PARALLEL_REQUESTS),
    )
