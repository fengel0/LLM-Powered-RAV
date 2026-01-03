import logging

from deployment_base.startup_sequence.log import LoggerStartupSequence
from deployment_base.startup_sequence.postgres import PostgresStartupSequence

from deployment_base.application import Application
from evaluation_service.usecase.evaluation import (
    EvaluationServiceConfig,
    EvaluationServiceUsecases,
)

from validation_database.validation_db_implementation import (
    PostgresDBEvaluation,
    PostgresDBEvaluatorDatabase,
)

import validation_database.model as validation_models

from trigger_evaluation_prefect.settings import (
    API_NAME,
    API_VERSION,
)

logger = logging.getLogger(__name__)


class TriggerApplication(Application):
    def get_application_name(self) -> str:
        return f"{API_NAME}-{API_VERSION}"

    def _add_components(self):
        self._with_component(
            component=LoggerStartupSequence(
                application_name=self.get_application_name(),
                application_version=API_VERSION,
            )
        )._with_acomponent(
            component=PostgresStartupSequence(models=[validation_models])
        )

    async def _create_usecase(self):
        evaluator_database = PostgresDBEvaluatorDatabase()
        evaluation_database = PostgresDBEvaluation()

        cfg = EvaluationServiceConfig(admin_token="")
        self.svc = EvaluationServiceUsecases.create(  # type: ignore
            evaluator_database=evaluator_database,
            evaluation_database=evaluation_database,
            config=cfg,
        )
