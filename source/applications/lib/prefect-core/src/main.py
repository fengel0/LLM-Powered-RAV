import logging

from prefect.automations import Automation, EventTrigger, RunDeployment
from prefect_core.base_deployment import CustomFlow

logger = logging.getLogger(__name__)


async def upload_files():
    logger.error("hi")


if __name__ == "__main__":
    flow = CustomFlow(upload_files)
    flow.add_automations(
        [
            Automation(
                name="test automation",
                trigger=EventTrigger(
                    expect={"test_lol"},
                    posture="Reactive",  # type: ignore
                    threshold=1,
                ),
                actions=[  # type: ignore
                    RunDeployment(  # type: ignore
                        deployment_id="d2386537-e8e2-457f-9e3e-2f82b7a5a109",
                        parameters={
                            "file_id": "{{ event.resource.id.split('/')[-1] }}"
                        },
                    )
                ],
            )
        ]
    )
    flow.serve(  # type: ignore
        name="Test Flow",
        tags=["file upload"],
    )
