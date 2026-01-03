import logging
from typing import Tuple
from core.result import Any, Result
from core.singelton import BaseSingleton
from domain.database.config.interface import (
    RAGConfigDatabase,
    SystemConfigDatabase,
)
from domain.database.config.model import GradingServiceConfig
from opentelemetry import trace
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ConfigServiceUsecases(BaseSingleton):


    """
    ConfigService usecase
    allows to load certain config types from the database
    """

    _config_database: SystemConfigDatabase[Any]
    _rag_database: RAGConfigDatabase

    tracer: trace.Tracer

    def _init_once(
        self,
        config_database: SystemConfigDatabase[BaseModel],
        rag_database: RAGConfigDatabase,
    ):
        logger.info("created TextAnalysUsecase Usecase")

        self._config_database = config_database
        self._rag_database = rag_database
        self.tracer = trace.get_tracer("ConfigServiceUsecase")

    async def get_grading_configs(self) -> Result[list[Tuple[str, str]]]:
        configs_result = await self._config_database.fetch_by_config_type(
            str(GradingServiceConfig.__name__)
        )
        ids: list[Tuple[str, str]] = []
        if configs_result.is_error():
            return Result.Err(configs_result.get_error())

        configs = configs_result.get_ok()
        for config_id in configs.keys():
            data = configs[config_id]
            ids.append(
                (
                    f"{data['system_name']}-{data['model']}-{config_id}",
                    config_id,
                )
            )
        return Result.Ok(ids)

    async def get_system_configs(self) -> Result[list[Tuple[str, str]]]:
        configs_result = await self._rag_database.fetch_all()
        ids: list[Tuple[str, str]] = []
        if configs_result.is_error():
            return Result.Err(configs_result.get_error())

        configs = configs_result.get_ok()
        for config in configs:
            ids.append(
                (
                    f"{config.name}-{config.id}",
                    config.id,
                )
            )
        return Result.Ok(ids)
