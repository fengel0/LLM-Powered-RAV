import logging

from deployment_base.startup_sequence.log import LoggerStartupSequence
from deployment_base.application import Application
from image_description_service.usecase.image_description import (
    DescribeImageUsecase,
    DescribeImageUsecaseConfig,
)
from openai_client.async_openai import ConfigOpenAI, OpenAIAsyncLLM

from deployment_base.enviroment.minio_env import S3_HOST
from deployment_base.enviroment import openai_env
from deployment_base.startup_sequence.s3 import MinioStartupSequence

from s3.minio import MinioFileStorage, MinioConnection
from rest_client.async_client import OTELAsyncHTTPClient

from file_database.file_db_implementation import PostgresFileDatabase
from file_converter_client.async_client import (
    FileConverterConfig,
    FileConverterServiceClientImpl,
)
from project_database.project_db_implementation import PostgresDBProjectDatbase

from deployment_base.startup_sequence.postgres import PostgresStartupSequence


import file_database.model as file_models
import project_database.model as project_models

from file_converter_pipline_service.usecase.file_converte import (
    ConvertFileUsecase,
)
from file_converter_prefect.settings import (
    API_NAME,
    API_VERSION,
    FILE_CONVERTER_API,
    PROMPT,
    REQUEST_TIMEOUT_IN_SECONDS,
    SETTINGS,
    SYSTEM_PROMPT,
)

logger = logging.getLogger(__name__)


class ApplicationFileConverterPrefect(Application):
    def get_application_name(self) -> str:
        return f"{API_NAME}-{API_VERSION}"

    def _add_components(self):
        self._with_component(
            component=LoggerStartupSequence(
                application_name=self.get_application_name(),
                application_version=API_VERSION,
            )
        )._with_acomponent(
            component=PostgresStartupSequence(
                models=[
                    file_models,
                    project_models,
                ]
            )
        )._with_acomponent(component=MinioStartupSequence())

    async def _create_usecase(self):
        result = self._config_loader.load_values([*SETTINGS, *openai_env.SETTINGS])
        if result.is_error():
            raise result.get_error()

        file_database = PostgresFileDatabase()
        project_database = PostgresDBProjectDatbase()

        file_converter_service = FileConverterServiceClientImpl(
            http_client=OTELAsyncHTTPClient(
                timeout=self._config_loader.get_int(REQUEST_TIMEOUT_IN_SECONDS)
            ),
            config=FileConverterConfig(
                host=self._config_loader.get_str(FILE_CONVERTER_API)
            ),
        )

        ConvertFileUsecase.create(
            file_database=file_database,
            project_database=project_database,
            file_converter_service=file_converter_service,
            application_version=1,
        )

        client = OpenAIAsyncLLM(
            ConfigOpenAI(
                model=self._config_loader.get_str(openai_env.OPENAI_MODEL),
                max_tokens=self._config_loader.get_int(openai_env.MAX_TOKENS),
                api_key=self._config_loader.get_str(openai_env.OPENAI_KEY),
                timeout=self._config_loader.get_int(openai_env.LLM_REQUEST_TIMEOUT),
                temperature=self._config_loader.get_float(openai_env.TEMPERATUR),
                context_cutoff=int(128_000 * 0.90),
            )
        )

        connection = MinioConnection.get_instance(self._config_loader.get_str(S3_HOST))

        description_config = DescribeImageUsecaseConfig(
            system_prompt=self._config_loader.get_str(SYSTEM_PROMPT),
            prompt=self._config_loader.get_str(PROMPT),
        )

        DescribeImageUsecase.create(
            async_ollama_client=client,
            config=description_config,
            file_storage=MinioFileStorage(minio=connection),
        )
