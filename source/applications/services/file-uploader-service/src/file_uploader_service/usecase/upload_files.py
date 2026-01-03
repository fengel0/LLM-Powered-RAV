from datetime import datetime
from enum import Enum
import os
from core.hash import compute_mdhash_id
from typing import Tuple
from domain.database.project.model import Project
from opentelemetry import trace
from pathlib import Path
from core.result import Result
import logging
from core.singelton import BaseSingleton
from domain.storage.interface import FileStorage
from domain.storage import get_content_type
from domain.storage.model import FileStorageObject, FileStorageObjectMetadata
from domain.database.file.interface import FileDatabase
from domain.database.file.model import File, FileMetadata
from domain.database.project.interface import ProjectDatabase
from pydantic import RootModel

from file_uploader_service.defaults import DEFAULT_PROJECT_NAME


class UploadedFiles(RootModel[list[str]]): ...


class ReasonForUpdate(Enum):
    NotExisting = "NotExisting"
    NewVersionOfApplication = "NewVersionOfApplication"
    NewVersionOfFile = "NewVersionOfFile"
    NoReasonForUpdate = "NoReasonForUpdate"


logger = logging.getLogger(__name__)


class UploadeFilesUsecase(BaseSingleton):

    """
    Upload file usecase
    i think the file handling logic should be handeled in a seperate usecase
    so that this class only uploade files
    """

    file_storage: FileStorage
    file_database: FileDatabase
    project_database: ProjectDatabase
    supported_file_types: list[str]
    root_dir: str
    application_version: int
    tracer: trace.Tracer

    def _init_once(
        self,
        file_storage: FileStorage,
        file_database: FileDatabase,
        project_database: ProjectDatabase,
        supported_file_types: list[str],
        root_dir: str,
        application_version: int,
    ):
        logger.info("created UploadFiles Usecase")
        logger.info(
            f"will search  for {supported_file_types} numbers: {len(supported_file_types)}"
        )
        self.tracer = trace.get_tracer("UploadeFilesUsecase")
        self.file_storage = file_storage
        self.file_database = file_database
        self.supported_file_types = supported_file_types
        self.root_dir = root_dir
        self.application_version = application_version
        self.project_database = project_database

    def get_all_files_from_root_dir(self) -> list[str]:
        with self.tracer.start_as_current_span("read-all-existing-files"):
            found_list: list[str] = []
            for root, _, files in os.walk(self.root_dir):
                for file_name in files:
                    file_path = os.path.join(root, file_name)
                    for file_type in self.supported_file_types:
                        if file_name.lower().endswith(file_type):
                            found_list.append(file_path)
                            break

        logger.debug(f"found files: {len(found_list)}")
        return found_list

    async def should_file_be_uploaded(
        self, filepath: str
    ) -> Result[Tuple[bool, ReasonForUpdate]]:
        fetched_file_result = await self.file_database.fetch_by_path(path=filepath)
        if fetched_file_result.is_error():
            return fetched_file_result.propagate_exception()

        fetched_file = fetched_file_result.get_ok()

        if fetched_file is None:
            return Result.Ok((True, ReasonForUpdate.NotExisting))
        if fetched_file.metadata.version < self.application_version:
            return Result.Ok((True, ReasonForUpdate.NewVersionOfApplication))

        _, update_date = self._get_creation_updatestemp(filepath=filepath)
        if fetched_file.metadata.file_updated < update_date:
            return Result.Ok((True, ReasonForUpdate.NewVersionOfFile))

        return Result.Ok((False, ReasonForUpdate.NoReasonForUpdate))

    async def custom_upload(
        self,
        filepath: str,
        content: bytes,
        metdata: dict[str, str],
        project_name: str,
        create_date: datetime = datetime.now(),
        update_date: datetime = datetime.now(),
    ) -> Result[str]:
        filename = os.path.basename(filepath)

        filename = f"{compute_mdhash_id(filepath)}-{filename}"

        result = await self.file_database.fetch_by_path(path=filepath)
        if result.is_error():
            return result.propagate_exception()

        existing_file = result.get_ok()

        result_project = await self.project_database.fetch_by_name(project_name)
        if result_project.is_error():
            return result_project.propagate_exception()

        project_optional = result_project.get_ok()
        if project_optional:
            project_id = project_optional.id
        else:
            project = Project(
                id="",
                version=self.application_version,
                year=0,
                name=project_name,
                address=None,
            )
            result_create = await self.project_database.create(obj=project)
            if result_create.is_error():
                return result_create.propagate_exception()
            project_id = result_create.get_ok()

        file = File(
            id="",
            filepath=filepath,
            filename=filename,
            bucket=project_id,
            metadata=FileMetadata(
                project_id=project_id,
                project_year=0,
                version=self.application_version,
                file_creation=create_date,
                file_updated=update_date,
                other_metadata=metdata,
            ),
            pages=[],
        )

        if existing_file:
            file.id = existing_file.id
            result_db_action = await self.file_database.update(obj=file)
            if result_db_action.is_error():
                return result_db_action.propagate_exception()
            db_id = existing_file.id
        else:
            result_db_action = await self.file_database.create(obj=file)
            if result_db_action.is_error():
                return result_db_action.propagate_exception()
            db_id = result_db_action.get_ok()

        result = self.file_storage.upload_file(
            file=self._build_file_storage_object(
                filename=filename,
                data=content,
                destination_bucket=project_id,
                db_id=db_id,
            )
        )
        if result.is_error():
            logger.error(
                f"Failed uploading file: {filepath} Error: {result.get_error()}"
            )
            if existing_file:
                result_db_action = await self.file_database.update(obj=existing_file)
            else:
                result_db_action = await self.file_database.delete(id=db_id)
            if result_db_action.is_error():
                logger.error(f"Failed deleting created File {result_db_action}")

            return Result.Err(result.get_error())

        logger.info(f"uploaded file: {filepath}")
        return Result.Ok(db_id)

    async def upload_file(self, filepath: str) -> Result[str]:
        path_elemtens = Path(filepath).parts
        project_name = DEFAULT_PROJECT_NAME

        if len(path_elemtens) > 1:
            project_name = path_elemtens[1]

        try:
            with open(filepath, "rb") as file_content:
                content = file_content.read()
        except Exception as e:
            return Result.Err(e)

        assert content is not None

        create_date, update_date = self._get_creation_updatestemp(filepath=filepath)
        return await self.custom_upload(
            content=content,
            filepath=filepath,
            metdata={},
            project_name=project_name,
            create_date=create_date,
            update_date=update_date,
        )

    async def upload_files(self) -> list[Result[str]]:
        local_files: list[str] = self.get_all_files_from_root_dir()
        uploaded_file_results: list[Result[str]] = []
        with self.tracer.start_as_current_span("uploade-files"):
            for file in local_files:
                result = await self.should_file_be_uploaded(filepath=file)
                if result.is_error():
                    uploaded_file_results.append(Result.Err(result.get_error()))
                if result.is_ok() and result.get_ok()[0]:
                    result = await self.upload_file(file)
                    uploaded_file_results.append(result)
                    continue

        return uploaded_file_results

    def _build_file_storage_object(
        self, filename: str, data: bytes, destination_bucket: str, db_id: str
    ) -> FileStorageObject:
        return FileStorageObject(
            filetype=get_content_type(filename),
            content=data,
            bucket=destination_bucket,
            filename=filename,
            metadata=FileStorageObjectMetadata(
                db_id=db_id,
                version=self.application_version,
            ),
        )

    def _get_creation_updatestemp(self, filepath: str) -> Tuple[datetime, datetime]:
        try:
            stat_info = os.stat(filepath)
            file_creation_ts = getattr(stat_info, "st_birthtime", stat_info.st_ctime)
            file_updated_ts = stat_info.st_mtime
        except Exception as e:
            logger.warning(f"Could not read file timestamps: {e}")
            file_creation_ts = file_updated_ts = datetime.now().timestamp()

        file_creation = datetime.fromtimestamp(file_creation_ts)
        file_updated = datetime.fromtimestamp(file_updated_ts)
        return (file_creation, file_updated)
