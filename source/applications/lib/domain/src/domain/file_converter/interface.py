from typing import Protocol, runtime_checkable
from core.result import Result
from domain.file_converter.model import Page, PageLite


@runtime_checkable
class FileConverter(Protocol):
    def does_convert_filetype(self, filetype: str) -> bool: ...

    def convert_file(self, file: str) -> Result[list[Page]]: ...


class FileConverterServiceClient(Protocol):
    async def convert_file(
        self, filename: str, bucket: str
    ) -> Result[list[PageLite]]: ...
