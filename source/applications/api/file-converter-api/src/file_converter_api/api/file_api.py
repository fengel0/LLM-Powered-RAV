import logging
from fastapi_core.base_api import BaseAPI, Lifespan
from file_converter_service.usecase.convert_file import (
    ConvertFileToMarkdown,
    UploadedFiles,
)
from pydantic import BaseModel


class Request(BaseModel):
    source_bucket: str
    destination_bucket: str
    filename: str


summary = """
convert pdf and wordfiles to markdown
fetches file from s3 and stores it in a selected bucket
"""

logger = logging.getLogger(__name__)


class FileConverterApi(BaseAPI):
    summary = """
        This API is in charge to convert abetrie files that have been uploaded to an S3 Bucket
    """

    def __init__(self, title: str, version: str, lifespan: Lifespan):
        super().__init__(title, version, lifespan=lifespan)

    def _register_api_paths(self):
        @self.app.put("/convert", summary=summary)
        async def convert_files(request: Request) -> UploadedFiles:
            # span verarbeitung
            logger.info(request)
            result = ConvertFileToMarkdown.Instance().convert_file(
                filename=request.filename,
                source_bucket=request.source_bucket,
                destination_bucket=request.destination_bucket,
            )
            if result.is_error():
                raise result.get_error()
            return result.get_ok()
