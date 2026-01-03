from core.result import Result
from domain.database import BaseDatabase
from domain.database.file.model import File, FilePage


class FileDatabase(BaseDatabase[File]):

    """
    File database interface.
    Stores the original file information
    """

    async def fetch_by_path(self, path: str) -> Result[File | None]: ...

    async def search_by_path(self, path: str) -> Result[list[File]]: ...

    async def fetch_by_name(self, name: str) -> Result[File | None]: ...

    async def search_by_name(self, name: str) -> Result[list[File]]: ...

    async def fetch_by_project(self, project_id: str) -> Result[list[File]]: ...

    async def fetch_files_blow_a_certain_version(
        self, version: int
    ) -> Result[list[File]]: ...

    async def fetch_file_pages_blow_a_certain_version(
        self, version: int
    ) -> Result[list[FilePage]]: ...
