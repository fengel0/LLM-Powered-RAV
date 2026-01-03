import logging

import file_database.model as file_models
import project_database.model as project_models
from deployment_base.application import Application
from deployment_base.enviroment.minio_env import S3_HOST
from deployment_base.startup_sequence.log import LoggerStartupSequence
from deployment_base.startup_sequence.postgres import PostgresStartupSequence
from deployment_base.startup_sequence.s3 import MinioStartupSequence
from file_database.file_db_implementation import PostgresFileDatabase
from file_uploader_service.usecase.upload_files import UploadeFilesUsecase
from project_database.project_db_implementation import PostgresDBProjectDatbase
from s3.minio import MinioConnection, MinioFileStorage

from file_uploader_prefect.settings import (
    API_NAME,
    API_VERSION,
    FILE_TYPES_TO_OBSERVE,
    OBSERVE_DIR,
    SETTINGS,
)

logger = logging.getLogger(__name__)


class FileUploaderPrefect(Application):
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
        result = self._config_loader.load_values(SETTINGS)
        if result.is_error():
            raise result.get_error()

        connection = MinioConnection.get_instance(self._config_loader.get_str(S3_HOST))
        root_dir = self._config_loader.get_str(OBSERVE_DIR)
        supported_file_types = self._config_loader.get_str(FILE_TYPES_TO_OBSERVE).split(
            " "
        )

        if len(supported_file_types) == 0:
            raise Exception("no File types set to observe")

        UploadeFilesUsecase.create(
            file_storage=MinioFileStorage(minio=connection),
            file_database=PostgresFileDatabase(),
            project_database=PostgresDBProjectDatbase(),
            supported_file_types=supported_file_types,
            root_dir=root_dir,
            application_version=0,
        )
