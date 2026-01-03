from __future__ import annotations
from deployment_base.enviroment import postgres_env

import file_database.model as file_models
import project_database.model as project_models
import validation_database.model as validation_models
import config_database.model as config_models
import hippo_rag_database.model as hippo_rag_models
import fact_store_database.model as fact_models

from core.config_loader import ConfigLoaderImplementation
from database.session import DatabaseConfig, PostgresSession
from database_migration.application_startup import DatbaseMigrationApplication
import asyncio
import logging


from database_migration.settings import UPDATE_MESSAGE

logger = logging.getLogger(__name__)


async def main():
    application = DatbaseMigrationApplication.create(
        config_loader=ConfigLoaderImplementation.create()
    )
    config_loader = ConfigLoaderImplementation.Instance()
    application.start()
    await application.astart()
    await application.create_usecase()

    config_loader.load_values(postgres_env.SETTINGS)

    config_db = DatabaseConfig(
        host=config_loader.get_str(postgres_env.POSTGRES_HOST),
        port=f"{config_loader.get_int(postgres_env.POSTGRES_PORT)}",
        database_name=config_loader.get_str(postgres_env.POSTGRES_DATABASE),
        username=config_loader.get_str(postgres_env.POSTGRES_USER),
        password=config_loader.get_str(postgres_env.POSTGRES_PASSWORD),
    )
    PostgresSession.create(
        config=config_db,
        models=[
            file_models,
            project_models,
            validation_models,
            config_models,
            hippo_rag_models,
            hippo_rag_models,
            fact_models,
        ],
    )
    await PostgresSession.Instance().start()
    await PostgresSession.Instance().migrations(
        ConfigLoaderImplementation.Instance().get_str(UPDATE_MESSAGE)
    )

    await application.ashutdown()
    application.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
