import logging

from core.logger import init_logging
from pdf_converter.marker import MarkerPDFConverter, MarkerPDFConverterConfig
from domain.file_converter.model import ImageFragment, TableFragement
from domain_test import AsyncTestBase

init_logging("debug")
logger = logging.getLogger(__name__)

files = [
    "./tests/test_files/llama2.pdf",
    # "./tests/test_files/empty_file.pdf",
]


"""
The content of the pages is not guaranteed to be perfect.
For example, ideally:

# test
## test
### test

But marker isn't perfect, so slight variations are acceptable.
"""


class TestMarkerPDFConverterIntegration(AsyncTestBase):
    __test__ = True

    @classmethod
    def setup_class(cls):
        cls.config = MarkerPDFConverterConfig(
            ollama_host=None,  # or a real endpoint if needed
            model=None,
            use_llm=False,
            device="mps",
        )
        cls.converter = MarkerPDFConverter(config=cls.config)

    def test_does_convert_filetype(self):
        assert self.converter.does_convert_filetype("pdf")
        assert self.converter.does_convert_filetype("PDF")
        assert not self.converter.does_convert_filetype("doc")

    def test_convert_file_returns_ok_result(self):
        file_count = 0
        for file in files:
            result = self.converter.convert_file(file)
            logger.info(f"Convert file {file}")

            if result.is_error():
                logger.error(result.get_error())

            assert result.is_ok(), f"Conversion failed for {file}"
            pages = result.get_ok()
            assert len(pages) >= 0  # Should at least return an empty list
            page_count = 0
            for page in pages:
                logger.info(f"fragment count {len(page.document_fragements)}")
                for fragment in page.document_fragements:
                    if isinstance(fragment, ImageFragment):
                        logger.info(fragment.filename)
                    elif isinstance(fragment, TableFragement):
                        logger.info(fragment.full_tabel)
                    else:
                        logger.info(fragment)
                page_count = page_count + 1
            file_count = file_count + 1
            logger.error(f"page count {page_count} {file}")

    def test_convert_file_with_invalid_path_returns_error(self):
        result = self.converter.convert_file("nonexistent_file.pdf")
        assert result.is_error()
        assert isinstance(result.get_error(), Exception)
