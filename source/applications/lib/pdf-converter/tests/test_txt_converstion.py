import logging

from core.logger import init_logging
from domain.file_converter.model import TextFragement
from pdf_converter.txt_converter import SimpleTXTConverter
from domain_test import AsyncTestBase

# --------------------------------------------------------------------------- #
#  Logging setup (same pattern the HTML tests use)
# --------------------------------------------------------------------------- #
init_logging("debug")
logger = logging.getLogger(__name__)


class TestSimpleTXTConverter(AsyncTestBase):
    __test__ = True
    """
    Mirrors the HTML-converter test style but mocks out filesystem IO so no real
    files are required.
    """

    @classmethod
    def setup_class(cls):
        cls.converter = SimpleTXTConverter()

    # --------------------------------------------------------------------- #
    #  File-type recognition
    # --------------------------------------------------------------------- #
    def test_does_convert_filetype(self):
        assert self.converter.does_convert_filetype("txt")
        assert self.converter.does_convert_filetype("TEXT")
        assert not self.converter.does_convert_filetype("html")

    # --------------------------------------------------------------------- #
    #  Successful conversion (happy path)
    # --------------------------------------------------------------------- #
    def test_convert_file_returns_ok_result(self):
        result = self.converter.convert_file("./tests/test_files/dummy.txt")

        # Result wrapper assertions
        assert result.is_ok(), "Conversion should succeed"
        pages = result.get_ok()
        assert len(pages) == 1, "Converter must return exactly one page"

        # Page / fragment assertions
        page = pages[0]
        assert len(page.document_fragements) == 1, (
            "TXT converter should yield exactly one fragment"
        )
        fragment = page.document_fragements[0]
        assert isinstance(fragment, TextFragement)
        assert fragment.text == "Hello\nWorld\n"

    # --------------------------------------------------------------------- #
    #  Error path – underlying read fails
    # --------------------------------------------------------------------- #
    def test_convert_file_with_invalid_path_returns_error(self):
        result = self.converter.convert_file("nonexistent.txt")
        assert result.is_error()
        assert isinstance(result.get_error(), Exception)
