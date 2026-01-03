# domain_test/storage/file_storage.py
import logging
from typing import Any

from core.result import Result
from domain.storage.model import FileStorageObjectMetadata, FileStorageObject
from domain.storage.interface import FileStorage
from domain_test import AsyncTestBase

logger = logging.getLogger(__name__)


class TestDBFileStorage(AsyncTestBase):
    storage: FileStorage
    bucket: str = "test_bucket"

    # ---- hooks ------------------------------------------------------------ #
    def make_file(
        self,
        *,
        filename: str,
        content: bytes,
        bucket: str,
        filetype: str,
        metadata: FileStorageObjectMetadata,
    ) -> Any:
        return FileStorageObject(
            filename=filename,
            content=content,
            bucket=bucket,
            filetype=filetype,
            metadata=metadata,
        )

    def _assert_ok(self, result: Result[Any]):
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()

    # ---- tests ------------------------------------------------------------ #
    def test_upload_and_fetch_file(self):
        version = 14
        new_version = 15
        db_id = "dummy_id"
        filename = "test.txt"
        content = b"Hello from unittest"
        new_content = b"new content"

        file_obj = self.make_file(
            filename=filename,
            content=content,
            bucket=self.bucket,
            filetype="text/plain",
            metadata=FileStorageObjectMetadata(version=version, db_id=db_id),
        )

        # upload
        upload_result = self.storage.upload_file(file_obj)
        self._assert_ok(upload_result)

        # fetch
        fetch_result = self.storage.fetch_file(filename, bucket=self.bucket)
        assert fetch_result
        file = fetch_result.get_ok()
        assert file is not None

        assert file.filename == filename
        assert file.content == content
        assert file.filetype == "text/plain"
        assert file.metadata.version == version
        assert file.metadata.db_id == db_id

        # overwrite (version & content)
        file_obj.metadata.version = new_version
        file_obj.content = new_content

        upload_result = self.storage.upload_file(file_obj)
        self._assert_ok(upload_result)

        fetch_result = self.storage.fetch_file(filename, bucket=self.bucket)
        self._assert_ok(fetch_result)
        file = fetch_result.get_ok()
        assert file is not None

        assert file.filename == filename
        assert file.content == new_content
        assert file.filetype == "text/plain"
        assert file.metadata.version == new_version
        assert file.metadata.db_id == db_id

        # info
        info_result = self.storage.get_file_info(filename, bucket=self.bucket)
        self._assert_ok(info_result)

        metadata = info_result.get_ok()
        assert metadata is not None
        assert metadata.version == new_version
        assert metadata.db_id == db_id

    def test_does_file_exist(self):
        filename = "existence-check.txt"
        content = b"check me"
        version = 14
        db_id = "dummy_id"

        file_obj = self.make_file(
            filename=filename,
            content=content,
            bucket=self.bucket,
            filetype="text/plain",
            metadata=FileStorageObjectMetadata(version=version, db_id=db_id),
        )

        result = self.storage.upload_file(file_obj)
        self._assert_ok(result)

        result = self.storage.does_file_exist(filename, bucket=self.bucket)
        self._assert_ok(result)
        assert result.get_ok()

    def test_does_file_not_exist(self):
        result = self.storage.does_file_exist("ghost.txt", bucket=self.bucket)
        self._assert_ok(result)
        assert not result.get_ok()

    def test_fetch_file_non_existing_bucket(self):
        # fetch_file
        result = self.storage.fetch_file("file.txt", "non_existing_bucket")
        self._assert_ok(result)
        assert result.get_ok() is None

        # get_file_info
        result = self.storage.get_file_info("file.txt", "non_existing_bucket")
        self._assert_ok(result)
        assert result.get_ok() is None

