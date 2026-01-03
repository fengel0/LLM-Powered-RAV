from deployment_base.application import Application
from deployment_base.startup_sequence.log import LoggerStartupSequence
from deployment_base.startup_sequence.postgres import PostgresStartupSequence

from config_database.db_implementation import (
    PostgresRAGConfigDatabase,
    PostgresSystemConfigDatabase,
    RAGConfigDatabase,
)
import config_database.model as config_model
from evaluation_service.usecase.evaluation import (
    EvaluationServiceConfig,
    EvaluationServiceUsecases,
)
from config_service.usecase.config_eval import ConfigServiceUsecases
import logging


from pydantic import BaseModel
import validation_database.model as validation_models
from validation_database.validation_db_implementation import (
    PostgresDBEvaluation,
    PostgresDBEvaluatorDatabase,
)


from graph_view.settings import (
    API_NAME,
    API_VERSION,
)

logger = logging.getLogger(__name__)


class DummyModel(BaseModel):
    system_name: str | None = None
    name: str | None = None


class GraphViewApplication(Application):
    def get_application_name(self) -> str:
        return f"{API_NAME}-{API_VERSION}"

    def _add_components(self):
        self._with_component(
            component=LoggerStartupSequence(
                application_name=self.get_application_name(),
                application_version=API_VERSION,
            )
        )._with_acomponent(
            component=PostgresStartupSequence(models=[config_model, validation_models])
        )

    async def _create_usecase(self):
        evaluator_database = PostgresDBEvaluatorDatabase()
        evaluation_database = PostgresDBEvaluation()
        cfg_database = PostgresSystemConfigDatabase(model=DummyModel)

        cfg = EvaluationServiceConfig(admin_token="")
        EvaluationServiceUsecases.create(  # type: ignore
            evaluator_database=evaluator_database,
            evaluation_database=evaluation_database,
            config=cfg,
        )
        ConfigServiceUsecases.create(
            config_database=cfg_database, rag_database=PostgresRAGConfigDatabase()
        )  # type: ignore
