from core.config_loader import ConfigLoaderImplementation
import asyncio
from prefect.automations import Automation
from prefect.events.schemas.automations import EventTrigger
from prefect.events.actions import RunDeployment
from prefect_core.base_deployment import ConcurrencyLimitConfig, CustomFlow, DUMMY_ID

from grading_prefect.application_startup import (
    GradingApplication,
    GradingConfigLoaderApplication,
)
from grading_prefect.prefrect.prefrect_tasks import evaluate_answer

from domain.pipeline.events import EventName

from grading_prefect.settings import PARALLEL_REQUESTS


async def main():
    GradingConfigLoaderApplication.create(ConfigLoaderImplementation.create())
    GradingConfigLoaderApplication.Instance().start()
    await GradingConfigLoaderApplication.Instance().astart()
    await GradingConfigLoaderApplication.Instance().create_usecase()

    grading_config = await GradingConfigLoaderApplication.Instance().get_config()

    await GradingConfigLoaderApplication.Instance().ashutdown()
    GradingConfigLoaderApplication.Instance().shutdown()
    return grading_config


if __name__ == "__main__":
    grading_config = asyncio.run(main())

    GradingApplication.create(ConfigLoaderImplementation.create())
    GradingApplication.Instance().set_grading_config(config=grading_config)

    config = ConfigLoaderImplementation.Instance()
    flow = CustomFlow(evaluate_answer)  # type: ignore
    automation = Automation(
        name=EventName.EVALUATE_RAG_SYSTEM.value,
        trigger=EventTrigger(
            expect={EventName.EVALUATE_RAG_SYSTEM.value},
            posture="Reactive",  # type: ignore
            threshold=1,
        ),
        actions=[  # type: ignore
            RunDeployment(  # type: ignore
                deployment_id=DUMMY_ID,
                parameters={
                    "task_id": "{{ event.resource.id }}",
                    "candiate": "{{ event.resource.name }}",
                },
            )
        ],
    )

    flow.add_automations([automation])
    config = ConfigLoaderImplementation.Instance()

    flow.serve(  # type: ignore
        name=GradingApplication.Instance().get_application_name(),
        tags=["file upload"],
        global_limit=ConcurrencyLimitConfig(limit=config.get_int(PARALLEL_REQUESTS)),
        limit=config.get_int(PARALLEL_REQUESTS),
    )
