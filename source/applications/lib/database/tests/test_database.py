# tests/test_base_database_postgres.py
from core.singelton import SingletonMeta
import pytest
import logging

from testcontainers.postgres import PostgresContainer
from tortoise import fields

from core.logger import init_logging
from database.session import (
    DatabaseConfig,
    PostgresSession,
    BaseDatabase,
    DatabaseBaseModel,
)

from domain_test import AsyncTestBase

init_logging("info")
logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
#  Model & database wrapper
# --------------------------------------------------------------------------- #
class ExampleModel(DatabaseBaseModel):
    name = fields.CharField(max_length=255)
    value = fields.IntField()


class ExampleModelDatabase(BaseDatabase[ExampleModel]):
    def __init__(self) -> None:
        super().__init__(ExampleModel)


# --------------------------------------------------------------------------- #
#  Test-case (single class, no helper wrappers)
# --------------------------------------------------------------------------- #
class TestBaseDatabasePostgres(AsyncTestBase):
    __test__ = True

    db: ExampleModelDatabase
    session: PostgresSession
    container: PostgresContainer
    cfg: DatabaseConfig

    # --------------------------- lifecycle ---------------------------------- #
    def setup_method_sync(self, test_name: str):
        # Start ephemeral Postgres container
        self.container = PostgresContainer(
            image="postgres:16-alpine",
            username="test",
            password="test",
            dbname="test_db",
        )
        self.container.start()

        self.cfg = DatabaseConfig(
            host=self.container.get_container_host_ip(),
            port=str(self.container.get_exposed_port(self.container.port)),
            database_name="test_db",
            username="test",
            password="test",
        )

    async def setup_method_async(self, test_name: str):
        # Init session, run migrations, wire SUT
        self.session = PostgresSession.create(  # type: ignore[assignment]
            config=self.cfg,
            models=[__name__],  # register ExampleModel from this module
        )
        await self.session.start()
        await self.session.migrations()

        self.db = ExampleModelDatabase()

    def teardown_method_sync(self, test_name: str):
        # Stop container
        try:
            self.container.stop()
            SingletonMeta.clear_all()
        finally:
            pass  # add SingletonMeta.clear_all() here if your app uses it

    async def teardown_method_async(self, test_name: str):
        await self.session.shutdown()

    # ------------------------------ tests ----------------------------------- #
    async def test_create_and_get(self):
        obj = ExampleModel(name="test", value=42)

        create_res = await self.db.create(obj)
        if create_res.is_error():
            logger.error(create_res.get_error())
        assert create_res.is_ok()
        obj_id = create_res.get_ok()

        get_res = await self.db.get(obj_id)
        if get_res.is_error():
            logger.error(get_res.get_error())
        assert get_res.is_ok()

        fetched = get_res.get_ok()
        assert fetched is not None
        assert fetched.name == "test"
        assert fetched.value == 42

    async def test_throws_exception_at_startup(self):
        # Try to create a brand-new, bad session (outside the container)
        bad_cfg = DatabaseConfig(
            host="127.0.0.1",
            port="1234",  # unused port
            database_name="does_not_exist",
            username="dummy",
            password="dummy",
        )
        with pytest.raises(Exception):
            SingletonMeta.clear_all()
            bad_session = PostgresSession.create(config=bad_cfg, models=[__name__])  # type: ignore
            await bad_session.start()

    async def test_get_all(self):
        create_1 = await self.db.create(ExampleModel(name="A", value=1))
        if create_1.is_error():
            logger.error(create_1.get_error())
        assert create_1.is_ok()

        create_2 = await self.db.create(ExampleModel(name="B", value=2))
        if create_2.is_error():
            logger.error(create_2.get_error())
        assert create_2.is_ok()

        all_res = await self.db.get_all()
        if all_res.is_error():
            logger.error(all_res.get_error())
        assert all_res.is_ok()

        objs = all_res.get_ok()
        assert len(objs) == 2
        names = {o.name for o in objs}
        assert names == {"A", "B"}

    async def test_update(self):
        create = await self.db.create(ExampleModel(name="update", value=1))
        if create.is_error():
            logger.error(create.get_error())
        assert create.is_ok()
        obj_id = create.get_ok()

        update_res = await self.db.update(
            ExampleModel(id=obj_id, name="updated!", value=999)
        )
        if update_res.is_error():
            logger.error(update_res.get_error())
        assert update_res.is_ok()

        get_res = await self.db.get(obj_id)
        if get_res.is_error():
            logger.error(get_res.get_error())
        assert get_res.is_ok()

        fetched = get_res.get_ok()
        assert fetched is not None
        assert fetched.name == "updated!"
        assert fetched.value == 999

    async def test_delete(self):
        create = await self.db.create(ExampleModel(name="delete", value=123))
        if create.is_error():
            logger.error(create.get_error())
        assert create.is_ok()
        obj_id = create.get_ok()

        del_res = await self.db.delete(obj_id)
        if del_res.is_error():
            logger.error(del_res.get_error())
        assert del_res.is_ok()

        get_res = await self.db.get(obj_id)
        if get_res.is_error():
            logger.error(get_res.get_error())
        assert get_res.is_ok()
        assert get_res.get_ok() is None

    async def test_run_query(self):
        res1 = await self.db.create(ExampleModel(name="Q1", value=10))
        if res1.is_error():
            logger.error(res1.get_error())
        assert res1.is_ok()

        res2 = await self.db.create(ExampleModel(name="Q2", value=20))
        if res2.is_error():
            logger.error(res2.get_error())
        assert res2.is_ok()

        query_res = await self.db.run_query({"name": "Q1"})
        if query_res.is_error():
            logger.error(query_res.get_error())
        assert query_res.is_ok()

        docs = query_res.get_ok()
        assert len(docs) == 1
        assert docs[0].name == "Q1"
