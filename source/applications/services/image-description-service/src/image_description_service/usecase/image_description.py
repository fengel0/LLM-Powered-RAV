from domain.storage.model import FileStorageObject
from domain.file_converter.model import FragementLite, FragementTypes
from domain.storage import get_content_type
from opentelemetry import trace
from core.model import NotFoundException
from domain.storage.interface import FileStorage
from domain.llm.interface import AsyncLLM
from core.result import Result
import logging
from core.singelton import BaseSingleton
from pydantic import BaseModel
import base64


logger = logging.getLogger(__name__)


class DescribeImageUsecaseConfig(BaseModel):
    system_prompt: str
    prompt: str


class DescribeImageUsecase(BaseSingleton):

    """
    DescribeImageUsecase
    will describe images based on given context in the data
    """

    _async_ollama_client: AsyncLLM
    _file_storage: FileStorage
    _config: DescribeImageUsecaseConfig
    tracer: trace.Tracer

    def _init_once(
        self,
        async_ollama_client: AsyncLLM,
        config: DescribeImageUsecaseConfig,
        file_storage: FileStorage,
    ):
        logger.info("created DescribeImageUsecase Usecase")
        self.tracer = trace.get_tracer("DescribeImageUsecase")
        self._async_ollama_client = async_ollama_client
        self._file_storage = file_storage
        self._config = config

    async def describe_image(
        self, filename: str, bucket: str, context_files: list[str]
    ) -> Result[None]:
        try:
            with self.tracer.start_as_current_span(f"fetch-{filename}"):
                fetched_image_result = self._file_storage.fetch_file(
                    filename=filename, bucket=bucket
                )
                if fetched_image_result.is_error():
                    return fetched_image_result.propagate_exception()
                fetched_image = fetched_image_result.get_ok()
                if fetched_image is None:
                    return Result.Err(
                        NotFoundException(
                            f"File {filename} in Bucket {bucket} not found"
                        )
                    )

            context = ""
            with self.tracer.start_as_current_span("fetch-context-files"):
                for file in context_files:
                    with self.tracer.start_as_current_span(
                        f"fetch-context-file-{file}"
                    ):
                        fetched_context_result = self._file_storage.fetch_file(
                            filename=file, bucket=bucket
                        )
                        if fetched_context_result.is_error():
                            return fetched_context_result.propagate_exception()
                        fetched_context = fetched_context_result.get_ok()
                        if fetched_context is None:
                            return Result.Err(
                                NotFoundException(
                                    f"File {file} in Bucket {bucket} not found"
                                )
                            )
                        data = fetched_context.content.decode()
                        context = f"{context}\n-----{file}----\n{data} "
            with self.tracer.start_as_current_span("describe file"):
                self._async_ollama_client.run_image_against_multimodal_model
                base64_str = base64.b64encode(fetched_image.content).decode("utf-8")
                description_result = (
                    await self._async_ollama_client.run_image_against_multimodal_model(
                        system_prompt=self._config.system_prompt,
                        prompt=f"{self._config.prompt} \n {context}",
                        base64_image=base64_str,
                    )
                )
                if description_result.is_error():
                    return description_result.propagate_exception()
                description = description_result.get_ok()

                filename_for_description = FragementLite(
                    filename=filename,
                    fragement_number=0,
                    fragement_type=FragementTypes.IMAGE,
                ).get_image_description_filename()
                upload_description = self._file_storage.upload_file(
                    FileStorageObject(
                        content=description.encode("utf-8"),
                        filetype=get_content_type(filetype=filename_for_description),
                        filename=filename_for_description,
                        bucket=bucket,
                    )
                )
                if upload_description.is_error():
                    return upload_description.propagate_exception()
                return Result.Ok()
        except Exception as e:
            return Result.Err(e)
