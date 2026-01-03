from enum import Enum
from pydantic import BaseModel
from datetime import datetime


class PageMetadata(BaseModel):
    project_id: str
    project_year: int
    version: int
    file_creation: datetime
    file_updated: datetime


class FragementTypes(Enum):
    TEXT = "TEXT"
    TABEL = "TABEL"
    IMAGE = "IMAGE"


class PageFragement(BaseModel):
    fragement_type: FragementTypes
    storage_filename: str
    fragement_number: int

    def get_image_description_filename(self) -> str:
        if self.fragement_type != FragementTypes.IMAGE:
            raise ValueError("Fragement Type does not have a description")
        return f"{self.storage_filename}.md"


class FilePage(BaseModel):
    bucket: str
    fragements: list[PageFragement]
    page_number: int
    metadata: PageMetadata


class FileMetadata(BaseModel):
    project_id: str
    project_year: int
    version: int
    file_creation: datetime
    file_updated: datetime
    other_metadata: dict[str, str | int | float]


class File(BaseModel):
    id: str
    filepath: str
    filename: str
    bucket: str
    metadata: FileMetadata
    pages: list[FilePage]

    def get_file_suffix(self) -> str:
        elements = self.filename.split(".")
        if len(elements) >= 2:
            return elements[-1]
        return ""

    def get_file_without_suffix(self) -> str:
        suffix = self.get_file_suffix()
        return self.filename.replace(f".{suffix}", "")
