import logging

from deployment_base.application import Application

from deployment_base.enviroment.minio_env import S3_HOST

from deployment_base.startup_sequence.log import LoggerStartupSequence
from s3.minio import MinioFileStorage, MinioConnection
from deployment_base.startup_sequence.s3 import MinioStartupSequence

from pdf_converter.marker import MarkerPDFConverter, MarkerPDFConverterConfig
from word_converter import OfficeToPDFConverter
from pdf_converter.html_converter import SimpleHTMLConverter
from pdf_converter.txt_converter import SimpleTXTConverter

from word_converter.excel_converter import ExcelToMarkdownConverter

from file_converter_api.settings import (
    API_NAME,
    API_VERSION,
    DEVICE,
    SETTINGS,
)
from file_converter_service.usecase.convert_file import ConvertFileToMarkdown

logger = logging.getLogger(__name__)


class FileConverterAPIApplication(Application):
    def get_application_name(self) -> str:
        return f"{API_NAME}-{API_VERSION}"

    def _add_components(self):
        self._with_component(
            component=LoggerStartupSequence(
                application_name=self.get_application_name(),
                application_version=API_VERSION,
            )
        )._with_acomponent(component=MinioStartupSequence())

    async def _create_usecase(self):
        result = self._config_loader.load_values(SETTINGS)
        if result.is_error():
            raise result.get_error()
        pdf_convert = MarkerPDFConverter(
            config=MarkerPDFConverterConfig(
                ollama_host=None,
                use_llm=False,
                model=None,
                device=self._config_loader.get_str(DEVICE),
            )
        )

        html_converter = SimpleHTMLConverter()
        word_converter = OfficeToPDFConverter(pdf_converter=pdf_convert)
        exel_converter = ExcelToMarkdownConverter()
        txt_converter = SimpleTXTConverter()

        connection = MinioConnection.get_instance(self._config_loader.get_str(S3_HOST))

        ConvertFileToMarkdown.create(
            file_storage=MinioFileStorage(minio=connection),
            file_converter=[
                pdf_convert,
                word_converter,
                exel_converter,
                html_converter,
                txt_converter,
            ],
        )
