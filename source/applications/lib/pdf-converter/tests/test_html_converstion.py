import logging

from core.logger import init_logging
from domain.file_converter.model import ImageFragment, TableFragement
from domain_test import AsyncTestBase

from pdf_converter.html_converter import SimpleHTMLConverter

# --------------------------------------------------------------------------- #
#  Logging setup (same pattern you already use)
# --------------------------------------------------------------------------- #
init_logging("debug")
logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
#  Test fixtures – adjust paths to whatever HTML samples you keep in tests/
# --------------------------------------------------------------------------- #
files = [
    "./tests/test_files/tabel.html",
    "./tests/test_files/arnold.html",
]

"""
The SimpleHTMLConverter treats the entire HTML file as a single page.  Markdown
quality will depend on `markdownify`; headings like

    <h1>Test</h1>
    <h2>Sub-Test</h2>

should come back as

    # Test
    ## Sub-Test

If the output diverges slightly that’s acceptable for this integration test;
we only assert that the conversion completes without raising and returns an
`Ok` Result containing at least one Page object.
"""


class TestSimpleHTMLConverterIntegration(AsyncTestBase):
    __test__ = True

    @classmethod
    def setup_class_sync(cls):
        cls.converter = SimpleHTMLConverter()

    # --------------------------------------------------------------------- #
    #  Basic file-type check
    # --------------------------------------------------------------------- #
    def test_does_convert_filetype(self):
        assert self.converter.does_convert_filetype("html")
        assert self.converter.does_convert_filetype("HTM")
        assert not self.converter.does_convert_filetype("pdf")

    # --------------------------------------------------------------------- #
    #  Happy-path conversions
    # --------------------------------------------------------------------- #
    def test_convert_file_returns_ok_result(self):
        for file in files:
            result = self.converter.convert_file(file)
            logger.info("Convert file %s", file)

            # Result wrapper assertions
            assert result.is_ok(), f"Conversion failed for {file}"
            pages = result.get_ok()
            assert len(pages) > 0

            # Drill down into fragments for manual inspection in logs
            for idx, page in enumerate(pages, start=1):
                logger.info(
                    "Page %d – fragment count: %d", idx, len(page.document_fragements)
                )
                for fragment in page.document_fragements:
                    if isinstance(fragment, ImageFragment):  # unlikely per assumption
                        logger.info("Image: %s", fragment.filename)
                    elif isinstance(fragment, TableFragement):
                        logger.info("Table:\n%s", fragment.full_tabel)
                    else:
                        logger.info("Text:\n%s", fragment)

    # --------------------------------------------------------------------- #
    #  Error handling for missing file
    # --------------------------------------------------------------------- #
    def test_convert_file_with_invalid_path_returns_error(self):
        result = self.converter.convert_file("nonexistent_file.html")
        assert result.is_error()
        assert isinstance(result.get_error(), Exception)
