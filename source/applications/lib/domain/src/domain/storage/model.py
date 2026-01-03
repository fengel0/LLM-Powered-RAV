from pydantic import BaseModel


class FileStorageObjectMetadata(BaseModel):
    version: int
    db_id: str


class FileStorageObject(BaseModel):
    filetype: str
    content: bytes
    bucket: str
    filename: str
    metadata: FileStorageObjectMetadata = FileStorageObjectMetadata(version=0, db_id="")

    def get_file_suffix(self) -> str:
        elements = self.filename.split(".")
        if len(elements) >= 2:
            return elements[-1]
        return ""

    def get_file_without_suffix(self) -> str:
        suffix = self.get_file_suffix()
        return self.filename.replace(f".{suffix}", "")
