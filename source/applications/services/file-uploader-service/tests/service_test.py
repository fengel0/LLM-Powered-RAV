# tests/test_upload_files_usecase.py
import os
from typing import Any
from datetime import datetime
import tempfile
from unittest.mock import AsyncMock, Mock, call, patch, mock_open

from core.result import Result
from core.logger import logging
from core.singelton import SingletonMeta

from file_uploader_service.usecase.upload_files import (
    ReasonForUpdate,
    UploadeFilesUsecase,
)

from domain_test import AsyncTestBase

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Test-fixture paths
# ---------------------------------------------------------------------------

root_dir = "./tests/test_files"
files_that_should_be_found = [f"{root_dir}/test_file.pdf"]


class TestUploadFilesUsecase(AsyncTestBase):
    """Unit-tests for :class:`UploadeFilesUsecase`.  Each test clears the
    singleton cache to guarantee isolation.
    """

    __test__ = True

    # ------------------------------------------------------------------
    # Common test setup/teardown helpers
    # ------------------------------------------------------------------
    def setup_method_sync(self, test_name: str):
        self.mock_storage = Mock()
        self.mock_file_database = AsyncMock()
        self.mock_project_database = AsyncMock()

        self.usecase = UploadeFilesUsecase.create(
            file_storage=self.mock_storage,
            file_database=self.mock_file_database,
            project_database=self.mock_project_database,
            supported_file_types=[".txt", ".pdf"],
            root_dir=root_dir,
            application_version=1,
        )

    def teardown_method_sync(self, test_name: str):
        SingletonMeta.clear_all()

    # ------------------------------------------------------------------
    # get_all_files_from_root_dir
    # ------------------------------------------------------------------
    async def test_get_all_files_from_root_dir_returns_supported_files(self):
        files = self.usecase.get_all_files_from_root_dir()
        assert files == files_that_should_be_found

    async def test_get_all_files_from_root_dir_ignores_unsupported(self):
        """Recursive, case-insensitive filtering by extension."""
        with tempfile.TemporaryDirectory() as tmpdir:
            supported = os.path.join(tmpdir, "file1.PDF")
            unsupported = os.path.join(tmpdir, "image.png")
            os.makedirs(os.path.join(tmpdir, "nested"))
            nested_supported = os.path.join(tmpdir, "nested", "nested.txt")
            for p in (supported, unsupported, nested_supported):
                with open(p, "wb") as fh:
                    fh.write(b"x")
            self.usecase.root_dir = tmpdir
            files = self.usecase.get_all_files_from_root_dir()
            assert set(files) == {supported, nested_supported}

    # ------------------------------------------------------------------
    # should_file_be_uploaded
    # ------------------------------------------------------------------
    async def test_should_file_be_uploaded_new_file(self):
        self.mock_file_database.fetch_by_path.return_value = Result.Ok(None)
        res = await self.usecase.should_file_be_uploaded("dummy.pdf")
        assert res.is_ok()
        assert res.get_ok() == (True, ReasonForUpdate.NotExisting)

    async def test_should_file_be_uploaded_old_app_version(self):
        self.mock_file_database.fetch_by_path.return_value = Result.Ok(
            Mock(metadata=Mock(version=0, file_updated=datetime(2000, 1, 1)))
        )
        res = await self.usecase.should_file_be_uploaded("dummy.pdf")
        assert res.is_ok()
        should_upload, reason = res.get_ok()
        assert should_upload
        assert reason == ReasonForUpdate.NewVersionOfApplication

    async def test_should_file_be_uploaded_new_version_of_file(self):
        old_ts = datetime(2000, 1, 1)
        new_ts = datetime(2025, 1, 1)
        self.mock_file_database.fetch_by_path.return_value = Result.Ok(
            Mock(metadata=Mock(version=1, file_updated=old_ts))
        )
        with patch.object(
            self.usecase, "_get_creation_updatestemp", return_value=(old_ts, new_ts)
        ):
            res = await self.usecase.should_file_be_uploaded("dummy.pdf")
        assert res.is_ok()
        assert res.get_ok() == (True, ReasonForUpdate.NewVersionOfFile)

    async def test_should_file_be_uploaded_no_upload_needed(self):
        now = datetime.now()
        self.mock_file_database.fetch_by_path.return_value = Result.Ok(
            Mock(metadata=Mock(version=1, file_updated=now))
        )
        with patch.object(
            self.usecase, "_get_creation_updatestemp", return_value=(now, now)
        ):
            res = await self.usecase.should_file_be_uploaded("dummy.pdf")
        assert res.is_ok()
        assert res.get_ok() == (False, ReasonForUpdate.NoReasonForUpdate)

    # ------------------------------------------------------------------
    # upload_files orchestrator
    # ------------------------------------------------------------------
    @patch.object(UploadeFilesUsecase, "get_all_files_from_root_dir")
    @patch.object(UploadeFilesUsecase, "should_file_be_uploaded")
    @patch.object(UploadeFilesUsecase, "upload_file")
    async def test_upload_files_success(self, m_upload_file, m_should, m_get):
        m_get.return_value = ["file1.pdf"]
        m_should.return_value = Result.Ok((True, ReasonForUpdate.NotExisting))
        m_upload_file.return_value = Result.Ok("id1")

        results = await self.usecase.upload_files()

        assert len(results) == 1
        assert results[0].is_ok()
        m_upload_file.assert_called_once_with("file1.pdf")

    @patch.object(UploadeFilesUsecase, "get_all_files_from_root_dir")
    @patch.object(UploadeFilesUsecase, "should_file_be_uploaded")
    async def test_upload_files_skip_when_not_needed(self, m_should, m_get):
        m_get.return_value = ["file1.pdf"]
        m_should.return_value = Result.Ok((False, ReasonForUpdate.NoReasonForUpdate))

        results = await self.usecase.upload_files()
        assert results == []

    @patch.object(UploadeFilesUsecase, "get_all_files_from_root_dir")
    @patch.object(UploadeFilesUsecase, "should_file_be_uploaded")
    @patch.object(UploadeFilesUsecase, "upload_file")
    async def test_upload_files_failure_bubbled(self, m_upload_file, m_should, m_get):
        m_get.return_value = ["file1.pdf"]
        m_should.return_value = Result.Ok((True, ReasonForUpdate.NotExisting))
        m_upload_file.return_value = Result.Err(Exception("fail"))

        results = await self.usecase.upload_files()
        assert len(results) == 1
        assert results[0].is_error()
        assert str(results[0].get_error()) == "fail"

    # ------------------------------------------------------------------
    # upload_file – low-level behaviour
    # ------------------------------------------------------------------
    @patch("builtins.open", side_effect=FileNotFoundError)
    async def test_upload_file_open_error(self, _m_open):
        res = await self.usecase.upload_file("/missing.pdf")
        assert res.is_error()
        assert isinstance(res.get_error(), FileNotFoundError)

    @patch("builtins.open", new_callable=mock_open, read_data=b"data")
    async def test_upload_file_success_with_existing_project(self, _m_open):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(b"data")
            path = tmp.name
        try:
            # mocks
            self.mock_file_database.fetch_by_path.return_value = Result.Ok(None)
            proj = Mock(id="proj1")
            self.mock_project_database.fetch_by_name.return_value = Result.Ok(proj)
            self.mock_file_database.create.return_value = Result.Ok("db1")
            self.mock_storage.upload_file.return_value = Result.Ok("stored")

            res = await self.usecase.upload_file(path)
            assert res.is_ok()
            assert res.get_ok() == "db1"
            self.mock_project_database.create.assert_not_called()
        finally:
            os.remove(path)

    @patch("builtins.open", new_callable=mock_open, read_data=b"data")
    async def test_upload_file_creates_project_if_missing(self, _m_open):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(b"data")
            path = tmp.name
        try:
            self.mock_file_database.fetch_by_path.return_value = Result.Ok(None)
            self.mock_project_database.fetch_by_name.return_value = Result.Ok(None)
            self.mock_project_database.create.return_value = Result.Ok("proj2")
            self.mock_file_database.create.return_value = Result.Ok("db2")
            self.mock_storage.upload_file.return_value = Result.Ok("stored")

            res = await self.usecase.upload_file(path)
            assert res.is_ok()
            assert res.get_ok() == "db2"
            self.mock_project_database.create.assert_called_once()
        finally:
            os.remove(path)

    @patch("builtins.open", new_callable=mock_open, read_data=b"data")
    async def test_upload_file_rollback_on_failure(self, _m_open):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(b"data")
            path = tmp.name
        try:
            existing = Mock(id="exist1")
            self.mock_file_database.fetch_by_path.return_value = Result.Ok(existing)
            self.mock_file_database.update.return_value = Result.Ok(True)
            self.mock_storage.upload_file.return_value = Result.Err(Exception("boom"))
            self.mock_project_database.fetch_by_name.return_value = Result.Ok(
                Mock(id="proj1")
            )

            res = await self.usecase.upload_file(path)
            assert res.is_error()
            self.mock_file_database.update.assert_has_calls([call(obj=existing)])
        finally:
            os.remove(path)

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------
    def test_get_creation_updatestemp_stat_failure(self):
        with patch("os.stat", side_effect=Exception("stat fail")):
            created, updated = self.usecase._get_creation_updatestemp("whatever")
        assert isinstance(created, datetime)
        assert isinstance(updated, datetime)
        assert abs((updated - created).total_seconds()) <= 1

    @patch("domain.storage.get_content_type", return_value="application/pdf")
    def test_build_file_storage_object(self, _m_get_ct):
        obj = self.usecase._build_file_storage_object(
            filename="doc.pdf",
            data=b"x",
            destination_bucket="bucket1",
            db_id="dbid",
        )
        assert obj.filetype == "application/pdf"
        assert obj.bucket == "bucket1"
        assert obj.metadata.db_id == "dbid"
        assert obj.metadata.version == 1
