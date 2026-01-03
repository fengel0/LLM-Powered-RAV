import logging
from core.logger import init_logging
from domain.file_converter.model import ImageFragment, TableFragement
from word_converter import OfficeToPDFConverter
from pdf_converter.marker import (
    MarkerPDFConverter,
    MarkerPDFConverterConfig,
)

from domain_test import AsyncTestBase

init_logging("debug")
logger = logging.getLogger(__name__)

files = [
    # "./tests/test_files/test_file.doc",
    # "./tests/test_files/test_file.pptx",
    # "./tests/test_files/empty_file.doc",
    # "./tests/test_files/test_file_page_split_with_text.doc",
    # "./tests/test_files/test_file.docx",
    # "./tests/test_files/empty_file.docx",
    # "./tests/test_files/test_file_page_split_with_text.docx",
    # "./tests/test_files/Leubingen09100Abschlussbericht.doc",
    "./tests/test_files/Anlage_5_2_WetterauerGrabung09_100.doc"
]


class TestWordConverterIntegration(AsyncTestBase):
    __test__ = True

    @classmethod
    def setup_class_sync(cls):
        cls.converter = OfficeToPDFConverter(
            pdf_converter=MarkerPDFConverter(
                MarkerPDFConverterConfig(
                    ollama_host=None, model=None, use_llm=False, device="cpu"
                )
            )
        )

    def test_convert_file_returns_ok_result(self):
        file_count = 0
        for file in files:
            result = self.converter.convert_file(file)
            logger.info(f"Convert file{file}")
            if result.is_error():
                logger.error(result.get_error())
            assert result.is_ok()
            pages = result.get_ok()
            page_count = 0
            fragemnt_count = 0
            for page in pages:
                logger.info(f"fragement count {len(page.document_fragements)}")
                for fragment in page.document_fragements:
                    fragemnt_count = fragemnt_count + 1
                    if isinstance(fragment, ImageFragment):
                        logger.info(fragment.filename)
                        continue
                    if isinstance(fragment, TableFragement):
                        logger.info(fragment.full_tabel)
                        continue
                    else:
                        logger.info(fragment)
                page_count = page_count + 1
            file_count = file_count + 1
            logger.error(f"page_count:{page_count} {file}")
            logger.error(f"fragement count:{fragemnt_count} {file}")

    def test_convert_file_with_invalid_path_returns_error(self):
        result = self.converter.convert_file("nonexistent_file.pdf")
        assert result.is_error()
        assert isinstance(result.get_error(), Exception)
