from __future__ import annotations
import logging
from uuid import UUID
from prefect.client.types.flexible_schedule_list import FlexibleScheduleList
from prefect.exceptions import (
    TerminationSignal,
)
from typing import (
    Any,
    Iterable,
    Optional,
    ParamSpec,
    TypeVar,
    Union,
    cast,
    override,
)
import asyncio
from rich.console import Console
from prefect.settings import (
    PREFECT_UI_URL,
)
import datetime
from prefect.client.schemas.objects import ConcurrencyLimitConfig

from prefect.automations import Automation
from prefect.events import (
    DeploymentTriggerTypes,
    RunDeployment,
    TriggerTypes,
)
from prefect.flows import Flow
from prefect.schedules import Schedule
from prefect.types.entrypoint import EntrypointType

R = TypeVar("R")  # The return type of the user's function
P = ParamSpec("P")  # The parameters of the flow

logger = logging.getLogger(__name__)

DUMMY_ID = "d2386537-e8e2-457f-9e3e-2f82b7a5a109"


class CustomFlow(Flow[P, R]):
    _list_automation: list[Automation] | None

    def __init__(self, *args, **kwargs):  # type: ignore
        super().__init__(*args, **kwargs)  # type: ignore
        self._list_automation = []

    def add_automations(self, list_automation: list[Automation]):
        self._list_automation = list_automation

    def _create_automation(self, uuid: UUID):
        if self._list_automation:
            for automation in self._list_automation:
                try:
                    automation_fetch = cast(
                        Automation, Automation.read(name=automation.name)
                    )

                    found_action: bool = False
                    for action in automation_fetch.actions:
                        if (
                            isinstance(action, RunDeployment)
                            and action.deployment_id == uuid
                        ):
                            found_action = True

                    for action in automation.actions:
                        if isinstance(action, RunDeployment):
                            action.deployment_id = uuid

                    if not found_action:
                        automation_fetch.actions.extend(automation.actions)

                    automation_fetch.update()
                    logger.info(f"updated {automation.name}")
                except:
                    for action in automation.actions:
                        if isinstance(action, RunDeployment):
                            action.deployment_id = uuid
                    automation.create()
                    logger.info(f"created {automation.name}")

    @override
    def serve(
        self,
        name: Optional[str] = None,
        interval: Optional[
            Union[
                Iterable[Union[int, float, datetime.timedelta]],
                int,
                float,
                datetime.timedelta,
            ]
        ] = None,
        cron: Optional[Union[Iterable[str], str]] = None,
        rrule: Optional[Union[Iterable[str], str]] = None,
        paused: Optional[bool] = None,
        schedule: Optional[Schedule] = None,
        schedules: Optional["FlexibleScheduleList"] = None,
        global_limit: Optional[
            Union[int, ConcurrencyLimitConfig, None]
        ] = ConcurrencyLimitConfig(limit=1),
        triggers: Optional[list[Union[DeploymentTriggerTypes, TriggerTypes]]] = None,
        parameters: Optional[dict[str, Any]] = None,
        description: Optional[str] = None,
        tags: Optional[list[str]] = None,
        version: Optional[str] = None,
        enforce_parameter_schema: bool = True,
        pause_on_shutdown: bool = True,
        print_starting_message: bool = True,
        limit: Optional[int] = 1,
        webserver: bool = False,
        entrypoint_type: EntrypointType = EntrypointType.FILE_PATH,
    ) -> None:
        """
        Creates a deployment for this flow and starts a runner to monitor for scheduled work.

        Args:
            name: The name to give the created deployment. Defaults to the name of the flow.
            interval: An interval on which to execute the deployment. Accepts a number or a
                timedelta object to create a single schedule. If a number is given, it will be
                interpreted as seconds. Also accepts an iterable of numbers or timedelta to create
                multiple schedules.
            cron: A cron schedule string of when to execute runs of this deployment.
                Also accepts an iterable of cron schedule strings to create multiple schedules.
            rrule: An rrule schedule string of when to execute runs of this deployment.
                Also accepts an iterable of rrule schedule strings to create multiple schedules.
            triggers: A list of triggers that will kick off runs of this deployment.
            paused: Whether or not to set this deployment as paused.
            schedule: A schedule object defining when to execute runs of this deployment.
                Used to provide additional scheduling options like `timezone` or `parameters`.
            schedules: A list of schedule objects defining when to execute runs of this deployment.
                Used to define multiple schedules or additional scheduling options like `timezone`.
            global_limit: The maximum number of concurrent runs allowed across all served flow instances associated with the same deployment.
            parameters: A dictionary of default parameter values to pass to runs of this deployment.
            description: A description for the created deployment. Defaults to the flow's
                description if not provided.
            tags: A list of tags to associate with the created deployment for organizational
                purposes.
            version: A version for the created deployment. Defaults to the flow's version.
            enforce_parameter_schema: Whether or not the Prefect API should enforce the
                parameter schema for the created deployment.
            pause_on_shutdown: If True, provided schedule will be paused when the serve function is stopped.
                If False, the schedules will continue running.
            print_starting_message: Whether or not to print the starting message when flow is served.
            limit: The maximum number of runs that can be executed concurrently by the created runner; only applies to this served flow. To apply a limit across multiple served flows, use `global_limit`.
            webserver: Whether or not to start a monitoring webserver for this flow.
            entrypoint_type: Type of entrypoint to use for the deployment. When using a module path
                entrypoint, ensure that the module will be importable in the execution environment.

        Examples:
            Serve a flow:

            ```python
            from prefect import flow

            @flow
            def my_flow(name):
                print(f"hello {name}")

            if __name__ == "__main__":
                my_flow.serve("example-deployment")
            ```

            Serve a flow and run it every hour:

            ```python
            from prefect import flow

            @flow
            def my_flow(name):
                print(f"hello {name}")

            if __name__ == "__main__":
                my_flow.serve("example-deployment", interval=3600)
            ```
        """
        from prefect.runner import Runner

        runner = Runner(name=name, pause_on_shutdown=pause_on_shutdown, limit=limit)
        deployment_id = runner.add_flow(
            self,
            name=name,
            triggers=triggers,
            interval=interval,
            cron=cron,
            rrule=rrule,
            paused=paused,
            schedule=schedule,
            schedules=schedules,
            concurrency_limit=global_limit,
            parameters=parameters,
            description=description,
            tags=tags,
            version=version,
            enforce_parameter_schema=enforce_parameter_schema,
            entrypoint_type=entrypoint_type,
        )
        assert isinstance(deployment_id, UUID)
        self._create_automation(uuid=deployment_id)
        if print_starting_message:
            help_message = (
                f"[green]Your flow {self.name!r} is being served and polling for"
                " scheduled runs!\n[/]\nTo trigger a run for this flow, use the"
                " following command:\n[blue]\n\t$ prefect deployment run"
                f" '{self.name}/{name}'\n[/]"
            )
            if PREFECT_UI_URL:
                help_message += (
                    "\nYou can also run your flow via the Prefect UI:"
                    f" [blue]{PREFECT_UI_URL.value()}/deployments/deployment/{deployment_id}[/]\n"
                )

            console = Console()
            console.print(help_message, soft_wrap=True)

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError as exc:
            if "no running event loop" in str(exc):
                loop = None
            else:
                raise

        try:
            if loop is not None:
                loop.run_until_complete(runner.start(webserver=webserver))
            else:
                asyncio.run(runner.start(webserver=webserver))
        except (KeyboardInterrupt, TerminationSignal) as exc:
            logger.info(f"Received {type(exc).__name__}, shutting down...")
            if loop is not None:
                loop.stop()
