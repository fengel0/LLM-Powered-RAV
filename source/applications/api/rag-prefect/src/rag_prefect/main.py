from core.config_loader import ConfigLoaderImplementation
import asyncio
from domain.database.config.model import RAGConfig
from prefect.automations import Automation
from prefect.events.schemas.automations import EventTrigger
from prefect.events.actions import RunDeployment
from prefect_core.base_deployment import ConcurrencyLimitConfig, CustomFlow, DUMMY_ID

from rag_prefect.application_startup import (
    RAGConfigLoaderApplication,
    RAGPrefectApplication,
)
from rag_prefect.prefrect.prefrect_tasks import generate_ans
from rag_prefect.settings import PARALLEL_REQUESTS
from domain.pipeline.events import EventName


async def main() -> RAGConfig:
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
    return config


if __name__ == "__main__":
    config = asyncio.run(main())

    RAGPrefectApplication.create(config_loader=ConfigLoaderImplementation.create())
    RAGPrefectApplication.Instance().set_rag_config(config)

    flow = CustomFlow(generate_ans, retries=3)  # type: ignore
    automation = Automation(
        name=EventName.ASK_RAG_SYSTEM.value,
        trigger=EventTrigger(
            expect={EventName.ASK_RAG_SYSTEM.value},
            posture="Reactive",  # type: ignore
            threshold=1,
        ),
        actions=[  # type: ignore
            RunDeployment(  # type: ignore
                deployment_id=DUMMY_ID,
                parameters={"task_id": "{{ event.resource.id.split('/')[-1] }}"},
            )
        ],
    )

    flow.add_automations([automation])
    config_loader = ConfigLoaderImplementation.Instance()

    flow.serve(  # type: ignore
        name=RAGPrefectApplication.Instance().get_application_name(),
        tags=["file upload"],
        global_limit=ConcurrencyLimitConfig(
            limit=config_loader.get_int(PARALLEL_REQUESTS)
        ),
        limit=config_loader.get_int(PARALLEL_REQUESTS),
    )
