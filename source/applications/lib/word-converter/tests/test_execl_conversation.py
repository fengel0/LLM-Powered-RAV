import logging
import unittest
from core.logger import init_logging
from domain.file_converter.model import ImageFragment, TableFragement

from word_converter.excel_converter import ExcelToMarkdownConverter
from domain_test import AsyncTestBase

init_logging("debug")
logger = logging.getLogger(__name__)

files = [
    "./tests/test_files/test_file.xlsx",
    "./tests/test_files/test_file.xls",
]


class TestWordConverterIntegration(AsyncTestBase):
    __test__ = True

    @classmethod
    def setup_class_sync(cls):
        cls.converter = ExcelToMarkdownConverter()

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
            for page in pages:
                logger.info(f"fragement count {len(page.document_fragements)}")
                for fragment in page.document_fragements:
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

    def test_convert_file_with_invalid_path_returns_error(self):
        result = self.converter.convert_file("nonexistent_file.pdf")
        assert result.is_error()
        assert isinstance(result.get_error(), Exception)
