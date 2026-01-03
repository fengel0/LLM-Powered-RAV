import logging
from core.result import Result
from domain.http_client.async_client import AsyncHttpClient
from domain.file_converter.model import PageLite
from domain.file_converter.interface import FileConverterServiceClient
from pydantic import BaseModel

from opentelemetry import trace

logger = logging.getLogger(__name__)


class FileConverterConfig(BaseModel):
    host: str


class FileConverterServiceClientImpl(FileConverterServiceClient):
    tracer: trace.Tracer

    def __init__(self, config: FileConverterConfig, http_client: AsyncHttpClient):
        self._config = config
        self._http = http_client
        self._url = f"{self._config.host}/convert"
        self.tracer = trace.get_tracer("File-Converter-Client")

    async def convert_file(self, filename: str, bucket: str) -> Result[list[PageLite]]:
        with self.tracer.start_as_current_span(f"convert-file-{filename}-in-{bucket}"):
            json_payload = {
                "filename": filename,
                "source_bucket": bucket,
                "destination_bucket": bucket,
            }

            result = await self._http.put(self._url, header={}, json=json_payload)

            if result.is_ok():
                response = result.get_ok()
                try:
                    parsed = [PageLite(**page) for page in response.body]
                    return Result.Ok(parsed)
                except Exception as parse_error:
                    logger.error(f"Failed to parse page result: {parse_error} original body: {response.body}")
                    return Result.Err(parse_error)
            else:
                logger.error(f"File conversion failed: {result.get_error()}")
                return Result.Err(result.get_error())
