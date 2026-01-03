import logging
from deployment_base.application import Application
from deployment_base.startup_sequence.postgres import PostgresStartupSequence
from deployment_base.startup_sequence.log import LoggerStartupSequence

import file_database.model as file_models
import project_database.model as project_models
import validation_database.model as validation_models
import config_database.model as config_models
import hippo_rag_database.model as hippo_rag_models
import fact_store_database.model as fact_models


from database_migration.settings import (
    SETTINGS,
)

logger = logging.getLogger(__name__)


class DatbaseMigrationApplication(Application):
    def _add_components(self):
        self._with_component(
            component=LoggerStartupSequence(
                application_name="dataset-migration", application_version="0.1.0"
            )
        )
        # ._with_acomponent(
        # component=PostgresStartupSequence(
        # models=[
        # file_models,
        # project_models,
        # validation_models,
        # config_models,
        # hippo_rag_models,
        # hippo_rag_models,
        # fact_models,
        # ]
        # )
        # )

    async def _create_usecase(self):
        self._config_loader.load_values(SETTINGS)
