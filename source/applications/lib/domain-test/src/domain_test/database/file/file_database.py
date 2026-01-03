import logging
import uuid
from datetime import datetime
from typing import List
from domain.database.file.interface import FileDatabase

from domain.database.file.model import (
    File,
    FilePage,
    FileMetadata,
    PageMetadata,
    PageFragement,
    FragementTypes,
)
from domain_test import AsyncTestBase

logger = logging.getLogger(__name__)


class TestFileDatabase(AsyncTestBase):
    db:FileDatabase

    def _create_test_file(self) -> File:
        """Construct a complete File domain object with required fields filled."""
        return File(
            id="",  # let DAL allocate UUID
            filepath="/some/path/file.pdf",
            filename="file.pdf",
            bucket="my-bucket",
            metadata=FileMetadata(
                project_id=str(uuid.uuid4()),
                project_year=2024,
                file_creation=datetime.now(),
                file_updated=datetime.now(),
                version=0,
                other_metadata={"author": "unit-tester"},
            ),
            pages=[
                FilePage(
                    bucket="my-bucket",
                    fragements=[
                        PageFragement(
                            fragement_type=FragementTypes.TEXT,
                            fragement_number=1,
                            storage_filename="hello.md",
                        )
                    ],
                    page_number=1,
                    metadata=PageMetadata(
                        project_id=str(uuid.uuid4()),
                        project_year=2024,
                        file_creation=datetime.now(),
                        file_updated=datetime.now(),
                        version=0,
                    ),
                )
            ],
        )

    # ---------------------------- tests ---------------------------

    async def test_create_and_get(self):
        f = self._create_test_file()

        res = await self.db.create(f)
        if res.is_error():
            logger.error(res.get_error())
        assert res.is_ok()
        file_id = res.get_ok()

        get_res = await self.db.get(file_id)
        if get_res.is_error():
            logger.error(get_res.get_error())
        assert get_res.is_ok()

        fetched = get_res.get_ok()
        assert fetched is not None
        assert fetched.filename == f.filename
        assert len(fetched.pages) == len(f.pages)
        assert len(fetched.pages[0].fragements) == len(f.pages[0].fragements)
        # NEW: other_metadata is persisted
        assert fetched.metadata.other_metadata == f.metadata.other_metadata

    async def test_update(self):
        f = self._create_test_file()
        create = await self.db.create(f)
        if create.is_error():
            logger.error(create.get_error())
        assert create.is_ok()
        file_id = create.get_ok()

        updated = f.model_copy(update={"id": file_id, "filename": "updated_file.pdf"})
        upd_res = await self.db.update(updated)
        if upd_res.is_error():
            logger.error(upd_res.get_error())
        assert upd_res.is_ok()

        get_res = await self.db.get(file_id)
        if get_res.is_error():
            logger.error(get_res.get_error())
        assert get_res.is_ok()
        assert get_res.get_ok().filename == "updated_file.pdf"
        # other_metadata should survive unchanged
        assert get_res.get_ok().metadata.other_metadata == f.metadata.other_metadata

    async def test_delete(self):
        f = self._create_test_file()
        create = await self.db.create(f)
        if create.is_error():
            logger.error(create.get_error())
        assert create.is_ok()
        file_id = create.get_ok()

        del_res = await self.db.delete(file_id)
        if del_res.is_error():
            logger.error(del_res.get_error())
        assert del_res.is_ok()

        # ensure it’s gone
        assert (await self.db.get(file_id)).get_ok() is None

    async def test_fetch_by_path(self):
        f = self._create_test_file()
        create = await self.db.create(f)
        if create.is_error():
            logger.error(create.get_error())
        assert create.is_ok()

        res = await self.db.fetch_by_path(f.filepath)
        if res.is_error():
            logger.error(res.get_error())
        assert res.is_ok()
        fetched = res.get_ok()
        assert fetched.filepath == f.filepath
        assert fetched.metadata.other_metadata == f.metadata.other_metadata

    async def test_search_by_name(self):
        f1 = self._create_test_file()
        f2 = self._create_test_file().model_copy(update={"filename": "another.pdf"})
        result = await self.db.create(f1)
        if result.is_error():
            logger.error(f1.get_error())
        assert result.is_ok()

        result = await self.db.create(f2)
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()

        res = await self.db.search_by_name("file")
        if res.is_error():
            logger.error(res.get_error())
        assert res.is_ok()

        filenames = [f.filename for f in res.get_ok()]
        assert "file.pdf" in filenames

    async def test_fetch_by_project(self):
        project_id = str(uuid.uuid4())
        f1 = self._create_test_file()
        f1.metadata.project_id = project_id
        f2 = self._create_test_file()
        f2.metadata.project_id = project_id

        result = await self.db.create(f1)
        if result.is_error():
            logger.error(f1.get_error())
        assert result.is_ok()

        result = await self.db.create(f2)
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()

        res = await self.db.fetch_by_project(project_id)
        if res.is_error():
            logger.error(res.get_error())
        assert res.is_ok()

        for file in res.get_ok():
            assert file.metadata.project_id == project_id
            assert file.metadata.other_metadata == f1.metadata.other_metadata

    async def test_fetch_files_below_version(self):
        f1 = self._create_test_file()
        f1.metadata.version = 1
        f2 = self._create_test_file()
        f2.metadata.version = 2
        f3 = self._create_test_file()
        f3.metadata.version = 3

        result = await self.db.create(f1)
        if result.is_error():
            logger.error(f1.get_error())
        assert result.is_ok()

        result = await self.db.create(f2)
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()

        result = await self.db.create(f3)
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()


        # Keep method name as defined in your DAL
        res = await self.db.fetch_files_blow_a_certain_version(3)
        if res.is_error():
            logger.error(res.get_error())
        assert res.is_ok()

        versions: List[int] = [f.metadata.version for f in res.get_ok()]
        assert all(v < 3 for v in versions)
        assert len(versions) == 2
        # all should still carry their metadata dict
        assert all(
            file.metadata.other_metadata == {"author": "unit-tester"}
            for file in res.get_ok()
        )

    async def test_fetch_file_pages_below_version(self):
        page_old = FilePage(
            bucket="my-bucket",
            fragements=[],
            page_number=1,
            metadata=PageMetadata(
                project_id=str(uuid.uuid4()),
                project_year=2023,
                file_creation=datetime.now(),
                file_updated=datetime.now(),
                version=1,
            ),
        )
        page_new = FilePage(
            bucket="my-bucket",
            fragements=[
                PageFragement(
                    fragement_type=FragementTypes.TEXT,
                    fragement_number=1,
                    storage_filename="hello.md",
                )
            ],
            page_number=2,
            metadata=PageMetadata(
                project_id=str(uuid.uuid4()),
                project_year=2024,
                file_creation=datetime.now(),
                file_updated=datetime.now(),
                version=5,
            ),
        )

        f = self._create_test_file()
        f.pages = [page_old, page_new]
        result = await self.db.create(f)
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()

        # Keep method name as defined in your DAL
        res = await self.db.fetch_file_pages_blow_a_certain_version(5)
        if res.is_error():
            logger.error(res.get_error())
        assert res.is_ok()

        pages = res.get_ok()
        assert len(pages) == 1
        assert pages[0].metadata.version == 1