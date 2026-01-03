import logging
from core.logger import init_logging
from domain.file_converter.interface import FileConverterServiceClient
from domain_test import AsyncTestBase

init_logging("info")
logger = logging.getLogger(__name__)


class TestFileConverterServiceClient(AsyncTestBase):
    """Verify that the async client handles *happy* and *unhappy* paths."""
    client: FileConverterServiceClient

    async def test_convert_file_success(self):
        result = await self.client.convert_file("test.pdf", "bucket-a")
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()

        pages = result.get_ok()

        # --- Top-level assertions ---
        assert isinstance(pages, list)
        assert len(pages) == 2

        # --- First Page ---
        first_page = pages[0]
        assert first_page.page_number == 1
        assert len(first_page.fragments) == 2

        img_fragment = first_page.fragments[0]
        assert img_fragment.filename == "img1.png"
        assert img_fragment.fragement_number == 0
        assert img_fragment.fragement_type.value == "IMAGE"

    async def test_convert_file_failure(self):
        result = await self.client.convert_file("fail.pdf", "bucket-x")
        # It's expected to be an error, but still log details for visibility.
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_error()
        assert "Network error" in str(result.get_error())

    async def test_convert_file_invalid_body(self):
        result = await self.client.convert_file("weird.pdf", "bucket-y")
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_error()
        assert isinstance(result.get_error(), Exception)