import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from pydantic import BaseModel

from core.logger import init_logging
from core.result import Result

# project imports
from config_service.usecase.config_storage import ConfigLoaderUsecase
from domain.database.config.model import Config
from domain_test import AsyncTestBase

init_logging("info")
logger = logging.getLogger(__name__)


class _DummyModel(BaseModel):
    foo: str | None = None
    bar: int | None = None


def _make_cfg(cfg_id: str, foo_val: str) -> Config[_DummyModel]:
    cfg = Config(id=cfg_id, data=_DummyModel(foo=foo_val))
    cfg.compute_config_hash()
    return cfg


class TestConfigLoaderUsecase(AsyncTestBase):
    """Tests for ConfigLoaderUsecase.load_config_update_config"""

    __test__ = True

    def setup_method_sync(self, test_name: str):
        # mock DB with updated method names
        self.db = MagicMock()
        self.db.get_config_by_id = AsyncMock()
        self.db.create_config = AsyncMock()
        self.db.get_config_by_hash = AsyncMock()

        # mock ConfigLoader
        self.cfg_loader = MagicMock()
        self.cfg_loader.get_model = MagicMock()
        self.cfg_loader.get_file_attribute = MagicMock(return_value="FILE_ATTR")
        self.cfg_loader.write_config = MagicMock()

        # instantiate use-case (skip singleton ctor)
        self.uc = ConfigLoaderUsecase(
            model=Config[_DummyModel],
            db=self.db,
            config_loader=self.cfg_loader,
        )

    # 1) holder has id, no stored_config  → _load_from_id (uses db.get_config_by_id)
    async def test_load_from_id_success(self):
        holder = SimpleNamespace(id="c1", stored_config=None)
        self.cfg_loader.get_model.return_value = holder

        cfg_in_db = _make_cfg("c1", "x")
        self.db.get_config_by_id.return_value = Result.Ok(cfg_in_db)

        res = await self.uc.load_config_update_config("key-1", lambda cfg, cl: cfg)

        self.cfg_loader.get_model.assert_called_once_with(
            key="key-1", model=Config[_DummyModel]
        )
        self.db.get_config_by_id.assert_awaited_once_with(id="c1")
        assert res.is_ok()
        assert res.get_ok() is cfg_in_db

    async def test_load_from_id_db_error(self):
        holder = SimpleNamespace(id="c1", stored_config=None)
        self.cfg_loader.get_model.return_value = holder
        self.db.get_config_by_id.return_value = Result.Err(RuntimeError("db-boom"))

        res = await self.uc.load_config_update_config("key-1", lambda cfg, cl: cfg)

        assert res.is_error()
        assert "db-boom" in str(res.get_error())

    # 2) holder has id & stored_config  → _load_update_attributes
    #    Uses db.get_config_by_hash; does NOT call db.get_config_by_id here.
    async def test_update_no_change__found_by_hash__writes_file_no_create(self):
        """
        When the updated payload matches an existing hash:
        - do NOT create a new DB record
        - DO write the config file (implementation always writes)
        """
        # stored_config must be a Config (ConfigInterface), not the raw model
        holder = SimpleNamespace(id="c2", stored_config=_make_cfg("c2", "same"))
        self.cfg_loader.get_model.return_value = holder

        # Build the would-be object to get its hash; DB returns an existing config
        existing_cfg = _make_cfg("c2", "same")
        self.db.get_config_by_hash.return_value = Result.Ok(
            existing_cfg
        )  # found by hash

        res = await self.uc.load_config_update_config("key-2", lambda cfg, cl: cfg)

        self.db.get_config_by_id.assert_not_awaited()
        self.db.get_config_by_hash.assert_awaited_once()
        self.db.create_config.assert_not_awaited()

        self.cfg_loader.get_file_attribute.assert_called_once_with(key="key-2")
        self.cfg_loader.write_config.assert_called_once()

        assert res.is_ok()
        out_cfg = res.get_ok()
        # ID is set to the DB config's id in implementation
        assert out_cfg.id == existing_cfg.id
        assert out_cfg.hash == existing_cfg.hash

    async def test_update_with_change__creates_and_writes_file(self):
        """When no config exists for the new hash, create in DB and write file."""
        holder = SimpleNamespace(id="c3", stored_config=_make_cfg("c3", "old"))
        self.cfg_loader.get_model.return_value = holder

        # No config with the new hash exists
        self.db.get_config_by_hash.return_value = Result.Ok(None)

        def _modify(cfg: Config[_DummyModel], _loader) -> Config[_DummyModel]:
            # mutate the wrapped model and recompute hash as your implementation expects
            cfg.data.foo = "new"
            cfg.compute_config_hash()
            return cfg

        # DB returns the newly created config object with its new id
        created_cfg = _make_cfg("new-id", "new")
        self.db.create_config.return_value = Result.Ok(created_cfg)

        res = await self.uc.load_config_update_config("key-3", _modify)

        # In update-path we should NOT call db.get_config_by_id (by id)
        self.db.get_config_by_id.assert_not_awaited()
        self.db.get_config_by_hash.assert_awaited_once()
        self.db.create_config.assert_awaited_once()

        self.cfg_loader.get_file_attribute.assert_called_once_with(key="key-3")
        self.cfg_loader.write_config.assert_called_once()

        # Inspect write_config args for sanity
        _, kwargs = self.cfg_loader.write_config.call_args
        assert kwargs.get("attribute") == "FILE_ATTR"
        written_obj = kwargs.get("config")
        assert written_obj is not None
        assert getattr(written_obj, "id", None) == "new-id"
        # stored_config is a Config; its .data is the Pydantic model
        assert getattr(getattr(written_obj, "stored_config", None), "data").foo == "new"

        assert res.is_ok()
        new_cfg = res.get_ok()
        assert new_cfg.id == "new-id"
        assert new_cfg.data.foo == "new"

    # 3) cfg_loader returned no holder  → Err
    async def test_no_holder_returns_error(self):
        self.cfg_loader.get_model.return_value = None

        res = await self.uc.load_config_update_config("key-4", lambda cfg, cl: cfg)

        assert res.is_error()
        assert "no object" in str(res.get_error())

    async def test_update_lambda_receives_copy_and_does_not_mutate_holder(self):
        """
        update_lambda should receive a deep copy (via model_copy) of the stored_config.
        Mutating it must NOT mutate the original holder.stored_config.
        """
        # Arrange: holder has a stored config "orig"
        holder = SimpleNamespace(id="c4", stored_config=_make_cfg("c4", "orig"))
        self.cfg_loader.get_model.return_value = holder

        # Force "create" path so we fully propagate the updated object
        self.db.get_config_by_hash.return_value = Result.Ok(None)

        # Track the object identity we receive in the lambda to ensure it's not the same as the holder's
        seen = {"obj_id": None}

        def _modify(cfg: Config[_DummyModel], _loader) -> Config[_DummyModel]:
            # capture identity of the object passed to lambda
            seen["obj_id"] = id(cfg)
            # mutate the copy and recompute hash
            cfg.data.foo = "mut"
            cfg.compute_config_hash()
            return cfg

        # DB returns the created config reflecting the "mut" change
        created_cfg = _make_cfg("new-id-2", "mut")
        self.db.create_config.return_value = Result.Ok(created_cfg)

        # Act
        res = await self.uc.load_config_update_config("key-copy", _modify)

        # Assert: lambda got a different object than the holder's stored_config
        assert seen["obj_id"] is not None
        assert seen["obj_id"] != id(holder.stored_config), (
            "lambda must receive a copy, not the original"
        )

        # We created + wrote the updated config
        self.db.get_config_by_id.assert_not_awaited()
        self.db.get_config_by_hash.assert_awaited_once()
        self.db.create_config.assert_awaited_once()

        self.cfg_loader.get_file_attribute.assert_called_once_with(key="key-copy")
        self.cfg_loader.write_config.assert_called_once()
        _, kwargs = self.cfg_loader.write_config.call_args
        written_obj = kwargs.get("config")
        assert written_obj is not None
        assert written_obj.stored_config.data.foo == "mut"
        assert written_obj.id == "new-id-2"

        # Result reflects the updated data
        assert res.is_ok()
        out_cfg = res.get_ok()
        assert out_cfg.id == "new-id-2"
        assert out_cfg.data.foo == "mut"
