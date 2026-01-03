# tests/test_project_database_postgres.py
import logging

from domain.database.project.model import Address, Project, Coordinates

from domain_test import AsyncTestBase
from domain.database.project.interface import ProjectDatabase

logger = logging.getLogger(__name__)


class TestProjectDatabase(AsyncTestBase):
    db: ProjectDatabase

    # --------------------------------------------------------------------- #
    # test data builder
    # --------------------------------------------------------------------- #
    def _create_test_project(self) -> Project:
        return Project(
            id="",
            version=0,
            name="tes-project",
            year=2025,
            address=Address(
                county="Ilmkreis",
                country="Deutschland",
                state="Thüringen",
                city="Erfurt",
                street="Altonarer Strasse 12",
                zip_code="99085",
                coordinates=Coordinates(lat=0.0, long=0.0),
            ),
        )

    # --------------------------------------------------------------------- #
    # tests
    # --------------------------------------------------------------------- #
    async def test_create_and_get(self):
        project = self._create_test_project()

        create_res = await self.db.create(project)
        if create_res.is_error():
            logger.error(create_res.get_error())
        assert create_res.is_ok()

        project_id = create_res.get_ok()

        get_res = await self.db.get(project_id)
        if get_res.is_error():
            logger.error(get_res.get_error())
        assert get_res.is_ok()

        fetched = get_res.get_ok()
        assert fetched is not None
        assert fetched.name == project.name
        assert fetched.version == project.version
        assert fetched.id == project_id

    async def test_fetch_by_name(self):
        project = self._create_test_project()
        result = await self.db.create(project)
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()

        res = await self.db.fetch_by_name(project.name)
        if res.is_error():
            logger.error(res.get_error())
        assert res.is_ok()

        fetched = res.get_ok()
        assert fetched is not None
        assert fetched.name == project.name

    async def test_fetch_by_year(self):
        project = self._create_test_project()
        result = await self.db.create(project)
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()

        res = await self.db.fetch_by_year(project.year)
        if res.is_error():
            logger.error(res.get_error())
        assert res.is_ok()

        projects = res.get_ok()
        assert any(p.name == project.name for p in projects)

    async def test_fetch_by_country(self):
        project = self._create_test_project()
        result = await self.db.create(project)
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()
        assert project.address

        res = await self.db.fetch_by_country(project.address.country)
        if res.is_error():
            logger.error(res.get_error())
        assert res.is_ok()

        projects = res.get_ok()
        assert any(p.name == project.name for p in projects)

    async def test_fetch_by_state(self):
        project = self._create_test_project()
        result = await self.db.create(project)
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()
        assert project.address

        res = await self.db.fetch_by_state(project.address.state)
        if res.is_error():
            logger.error(res.get_error())
        assert res.is_ok()

        projects = res.get_ok()
        assert any(p.name == project.name for p in projects)

    async def test_fetch_by_coordinates(self):
        project = self._create_test_project()
        result = await self.db.create(project)
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()
        assert project.address

        res = await self.db.fetch_by_coordinates(
            coordinates=project.address.coordinates,
            radius_in_meter=1000,
        )
        if res.is_error():
            logger.error(res.get_error())
        assert res.is_ok()

        projects = res.get_ok()
        assert any(p.name == project.name for p in projects)

    async def test_search_by_name(self):
        project = self._create_test_project()
        result = await self.db.create(project)
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()

        res = await self.db.search_by_name("tes")  # partial match
        if res.is_error():
            logger.error(res.get_error())
        assert res.is_ok()

        projects = res.get_ok()
        assert any(p.name == project.name for p in projects)

    async def test_search_by_country(self):
        project = self._create_test_project()
        result = await self.db.create(project)
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()
        assert project.address

        res = await self.db.search_by_country(project.address.country[:4])
        if res.is_error():
            logger.error(res.get_error())
        assert res.is_ok()

        projects = res.get_ok()
        for p in projects:
            assert p.address
            assert p.address.country == project.address.country

    async def test_search_by_state(self):
        project = self._create_test_project()
        result = await self.db.create(project)
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()
        assert project.address

        res = await self.db.search_by_state(project.address.state[:4])
        if res.is_error():
            logger.error(res.get_error())
        assert res.is_ok()

        projects = res.get_ok()
        for p in projects:
            assert p.address
            assert p.address.state == project.address.state

