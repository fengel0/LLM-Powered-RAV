from unittest.mock import AsyncMock, MagicMock

from core.result import Result
from core.model import NotFoundException
from core.singelton import SingletonMeta

# domain models / enums
from domain.database.file.model import FragementTypes

# ⚠️ adjust the import below to the real location of your use-case class
# from file_converter_pipline_service.usecase.convert_file import ConvertFileUsecase
from file_converter_pipline_service.usecase.file_converte import ConvertFileUsecase

from domain_test import AsyncTestBase


class TestConvertFileUsecase(AsyncTestBase):
    """Unit-tests for the (new) ConvertFileUsecase."""

    __test__ = True

    # ---------- helpers ----------------------------------------------------
    @staticmethod
    def _make_fragment(idx: int = 1):
        frag = MagicMock()
        frag.fragement_type = FragementTypes.TEXT  # enum value
        frag.filename = f"fragment_{idx}.png"
        frag.fragement_number = idx
        return frag

    @staticmethod
    def _make_page(num_frags: int = 1):
        page = MagicMock()
        page.fragments = [
            TestConvertFileUsecase._make_fragment(i + 1) for i in range(num_frags)
        ]
        return page

    # ---------- test-set-up / tear-down -----------------------------------
    def setup_method_sync(self, test_name: str):
        # reset the singleton between test runs Try via SingletonMeta first; fall back to class-held _instances if present

        self.file_db = AsyncMock()
        self.project_db = AsyncMock()
        self.converter_svc = AsyncMock()

        ConvertFileUsecase.create(
            file_database=self.file_db,
            project_database=self.project_db,
            file_converter_service=self.converter_svc,
            application_version=1,
        )
        self.uc = ConvertFileUsecase.Instance()

        # a dummy File aggregate returned by the repository
        self.fake_file = MagicMock()
        self.fake_file.id = "file-123"
        self.fake_file.filename = "test.pdf"
        self.fake_file.metadata = MagicMock(
            project_id="project-X",
            project_year=2024,
            file_creation="2024-01-01",
            file_updated="2024-02-01",
        )

    def teardown_method_sync(self, test_name: str):
        SingletonMeta.clear_all()

    # ---------- happy path -------------------------------------------------
    async def test_convert_file_success(self):
        # repos return file + project
        self.file_db.get.return_value = Result.Ok(self.fake_file)
        self.project_db.get.return_value = Result.Ok(MagicMock())

        # converter returns 2 pages, each with one fragment
        pages = [self._make_page(), self._make_page()]
        self.converter_svc.convert_file.return_value = Result.Ok(pages)

        # repo update succeeds
        self.file_db.update.return_value = Result.Ok()

        result = await self.uc.convert_file(self.fake_file.id)

        assert result.is_ok()
        # ensure we persisted the file back
        self.file_db.update.assert_awaited_once_with(obj=self.fake_file)

    # ---------- error scenarios -------------------------------------------
    async def test_convert_file_file_not_found(self):
        self.file_db.get.return_value = Result.Ok(None)

        result = await self.uc.convert_file("missing-file")

        assert result.is_error()
        assert isinstance(result.get_error(), NotFoundException)

    async def test_convert_file_project_not_found(self):
        self.file_db.get.return_value = Result.Ok(self.fake_file)
        self.project_db.get.return_value = Result.Ok(None)

        result = await self.uc.convert_file(self.fake_file.id)

        assert result.is_error()
        assert isinstance(result.get_error(), NotFoundException)

    async def test_convert_file_db_get_fails(self):
        self.file_db.get.return_value = Result.Err(Exception("db get error"))

        result = await self.uc.convert_file(self.fake_file.id)

        assert result.is_error()
        assert "db get error" in str(result.get_error())

    async def test_convert_file_project_get_fails(self):
        self.file_db.get.return_value = Result.Ok(self.fake_file)
        self.project_db.get.return_value = Result.Err(Exception("project db error"))

        result = await self.uc.convert_file(self.fake_file.id)

        assert result.is_error()
        assert "project db error" in str(result.get_error())

    async def test_convert_file_converter_fails(self):
        self.file_db.get.return_value = Result.Ok(self.fake_file)
        self.project_db.get.return_value = Result.Ok(MagicMock())
        self.converter_svc.convert_file.return_value = Result.Err(
            Exception("conversion failed")
        )

        result = await self.uc.convert_file(self.fake_file.id)

        assert result.is_error()
        assert "conversion failed" in str(result.get_error())

    async def test_convert_file_converter_returns_empty(self):
        self.file_db.get.return_value = Result.Ok(self.fake_file)
        self.project_db.get.return_value = Result.Ok(MagicMock())
        self.converter_svc.convert_file.return_value = Result.Ok([])
        self.file_db.update.return_value = Result.Ok()

        result = await self.uc.convert_file(self.fake_file.id)

        assert result.is_ok()
        # the use-case clears pages on the aggregate
        assert self.fake_file.pages == []

    async def test_convert_file_invalid_fragment_type(self):
        self.file_db.get.return_value = Result.Ok(self.fake_file)
        self.project_db.get.return_value = Result.Ok(MagicMock())

        bad_fragment = MagicMock()
        bad_fragment.fragement_type.value = "NOT_A_MEMBER"
        bad_fragment.filename = "oops.png"
        bad_fragment.fragement_number = 1

        bad_page = MagicMock()
        bad_page.fragments = [bad_fragment]

        self.converter_svc.convert_file.return_value = Result.Ok([bad_page])

        result = await self.uc.convert_file(self.fake_file.id)
        assert result.is_error()
