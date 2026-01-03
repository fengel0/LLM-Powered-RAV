from core.config_loader import ConfigLoaderImplementation
from prefect.automations import Automation
from prefect.events.schemas.automations import EventTrigger
from prefect.events.actions import RunDeployment
from prefect_core.base_deployment import CustomFlow, DUMMY_ID

from domain.pipeline.events import EventName

from file_converter_prefect.application_startup import ApplicationFileConverterPrefect
from file_converter_prefect.prefrect.prefrect_tasks import created_or_updated_file


if __name__ == "__main__":
    ApplicationFileConverterPrefect.create(
        config_loader=ConfigLoaderImplementation.create()
    )
    flow = CustomFlow(created_or_updated_file)  # type: ignore
    automation = Automation(
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

    flow.add_automations([automation])

    flow.serve(  # type: ignore
        name=ApplicationFileConverterPrefect.Instance().get_application_name(),
        tags=["file upload"],
    )
