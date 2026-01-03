from opentelemetry import trace
from core.result import Result
from core.model import NotFoundException
import logging
from core.singelton import BaseSingleton
from domain.database.file.interface import FileDatabase
from domain.database.project.interface import ProjectDatabase
from domain.database.file.model import (
    File,
    FilePage,
    FragementTypes,
    PageMetadata,
    PageFragement,
)
from domain.file_converter.interface import FileConverterServiceClient


logger = logging.getLogger(__name__)


class ConvertFileUsecase(BaseSingleton):


    """
    ConvertFileUsecase usecase
    allows to convert files to markdown
    usecase for the pipline
    it should call a remote services to do this the service write the files to s3 bucket
    """

    file_converter_service: FileConverterServiceClient
    file_database: FileDatabase
    project_database: ProjectDatabase
    application_version: int
    tracer: trace.Tracer

    def _init_once(
        self,
        file_database: FileDatabase,
        project_database: ProjectDatabase,
        file_converter_service: FileConverterServiceClient,
        application_version: int,
    ):
        logger.info("created ConvertFile Usecase")
        self.tracer = trace.get_tracer("ConvertFileUsecase")
        self.file_database = file_database
        self.project_database = project_database
        self.application_version = application_version
        self.file_converter_service = file_converter_service

    async def convert_file(self, file_id: str) -> Result[File]:
        with self.tracer.start_as_current_span("converting files"):
            try:
                with self.tracer.start_as_current_span("fetch file from db"):
                    fetch_file_result = await self.file_database.get(id=file_id)
                    if fetch_file_result.is_error():
                        logger.error(fetch_file_result.get_error())
                        return fetch_file_result.propagate_exception()

                    file = fetch_file_result.get_ok()
                    if file is None:
                        return Result.Err(
                            NotFoundException(f"File {file_id} not found")
                        )

                    fetch_project_result = await self.project_database.get(
                        id=file.metadata.project_id
                    )

                    if fetch_project_result.is_error():
                        logger.error(fetch_project_result.get_error())
                        return fetch_project_result.propagate_exception()

                    project = fetch_project_result.get_ok()
                    if project is None:
                        return Result.Err(
                            NotFoundException(
                                f"Project {file.metadata.project_id} not found"
                            )
                        )
                with self.tracer.start_as_current_span("convert file"):
                    result_pages = await self.file_converter_service.convert_file(
                        filename=file.filename, bucket=file.metadata.project_id
                    )

                    if result_pages.is_error():
                        return result_pages.propagate_exception()

                    pages = result_pages.get_ok()

                if len(pages) == 0:
                    logger.warning(f"File {file_id} was converted but got no pages")
                file.pages = []

                with self.tracer.start_as_current_span("store changes in db"):
                    for index, page in enumerate(pages):
                        db_page = FilePage(
                            bucket=file.metadata.project_id,
                            page_number=index + 1,
                            fragements=[],
                            metadata=PageMetadata(
                                project_id=file.metadata.project_id,
                                project_year=file.metadata.project_year,
                                version=self.application_version,
                                file_creation=file.metadata.file_creation,
                                file_updated=file.metadata.file_updated,
                            ),
                        )
                        for fragement in page.fragments:
                            db_page.fragements.append(
                                PageFragement(
                                    fragement_type=FragementTypes(
                                        fragement.fragement_type.value
                                    ),
                                    storage_filename=fragement.filename,
                                    fragement_number=fragement.fragement_number,
                                )
                            )
                        file.pages.append(db_page)

                    result = await self.file_database.update(obj=file)
                    if result.is_error():
                        return result.propagate_exception()
                return Result.Ok(file)
            except Exception as e:
                return Result.Err(e)
