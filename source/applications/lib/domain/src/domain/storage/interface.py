from typing import Protocol
from core.result import Result

from domain.storage.model import FileStorageObject, FileStorageObjectMetadata


class FileStorage(Protocol):
    def upload_file(self, file: FileStorageObject) -> Result[None]: ...

    def does_file_exist(self, filename: str, bucket: str) -> Result[bool]: ...

    def get_file_info(
        self, filename: str, bucket: str
    ) -> Result[FileStorageObjectMetadata | None]: ...

    def fetch_file(
        self, filename: str, bucket: str
    ) -> Result[FileStorageObject | None]: ...
