from types import ModuleType
from core.config_loader import ConfigLoader
from deployment_base.enviroment import postgres_env

from deployment_base.application import AsyncLifetimeReg


class PostgresStartupSequence(AsyncLifetimeReg):
    _models: list[ModuleType | str]

    def __init__(self, models: list[ModuleType | str]) -> None:
        super().__init__()
        self._models = models

    async def start(self, config_loader: ConfigLoader):
        from database.session import PostgresSession, DatabaseConfig

        result = config_loader.load_values(postgres_env.SETTINGS)
        if result.is_error():
            raise result.get_error()

        config_db = DatabaseConfig(
            host=config_loader.get_str(postgres_env.POSTGRES_HOST),
            port=f"{config_loader.get_int(postgres_env.POSTGRES_PORT)}",
            database_name=config_loader.get_str(postgres_env.POSTGRES_DATABASE),
            username=config_loader.get_str(postgres_env.POSTGRES_USER),
            password=config_loader.get_str(postgres_env.POSTGRES_PASSWORD),
        )

        PostgresSession.create(  # type: ignore
            config=config_db,
            models=self._models,
        )
        await PostgresSession.Instance().start()

    async def shutdown(self):
        from database.session import PostgresSession

        await PostgresSession.Instance().shutdown()
