# tests/test_evaluation_service_config_usecases.py
import logging
from unittest.mock import AsyncMock, MagicMock
from types import SimpleNamespace

from core.singelton import SingletonMeta
from pydantic import BaseModel

from core.logger import init_logging
from core.result import Result
from config_service.usecase.config_eval import ConfigServiceUsecases
from domain_test import AsyncTestBase

init_logging("info")
logger = logging.getLogger(__name__)


class _DummyConfigTypeA(BaseModel):
    system_name: str | None = None
    name: str | None = None


class TestEvaluationServiceConfigUsecases(AsyncTestBase):
    """Unit-tests for the configuration helpers of *EvaluationServiceUsecases*."""

    __test__ = True

    # ------------------------------------------------------------------
    # test-harness setup
    # ------------------------------------------------------------------
    def setup_method_sync(self, test_name: str):
        # system config DB (used by get_grading_configs)
        self.cfg_db = MagicMock()
        self.cfg_db.fetch_by_config_type = AsyncMock()

        # RAG config DB (used by get_system_configs)
        self.rag_db = MagicMock()
        self.rag_db.fetch_all = AsyncMock()

        # bypass the singleton’s __init__
        self.svc = ConfigServiceUsecases.__new__(ConfigServiceUsecases)
        self.svc._init_once(  # type: ignore[arg-type]
            config_database=self.cfg_db,
            rag_database=self.rag_db,
        )

    def teardown_method_sync(self, test_name: str):
        SingletonMeta.clear_all()

    # ------------------------------------------------------------------
    # get_grading_configs ----------------------------------------------
    # ------------------------------------------------------------------
    async def test_get_grading_configs_success(self):
        """Configs are returned as (label, id) tuples built from system_name, model, and id."""
        cfgs = {
            "c1": {"id": "c1", "system_name": "name", "model": "model"},
            "c3": {"id": "c3", "system_name": "name", "model": "model"},
        }
        self.cfg_db.fetch_by_config_type.return_value = Result.Ok(cfgs)

        res = await self.svc.get_grading_configs()

        self.cfg_db.fetch_by_config_type.assert_awaited_once()
        assert res.is_ok()
        assert set([x[1] for x in res.get_ok()]) == {"c1", "c3"}

    async def test_get_grading_configs_propagates_error(self):
        self.cfg_db.fetch_by_config_type.return_value = Result.Err(
            RuntimeError("DB failure")
        )

        res = await self.svc.get_grading_configs()

        self.cfg_db.fetch_by_config_type.assert_awaited_once()
        assert res.is_error()
        assert "DB failure" in str(res.get_error())

    # ------------------------------------------------------------------
    # get_system_configs -----------------------------------------------
    # ------------------------------------------------------------------
    async def test_get_system_configs_success(self):
        """System configs come from the RAG database and are returned as (label, id) tuples."""
        cfgs = [
            SimpleNamespace(id="a", name="name"),
            SimpleNamespace(id="c", name="name"),
        ]

        self.rag_db.fetch_all.return_value = Result.Ok(cfgs)

        res = await self.svc.get_system_configs()

        self.rag_db.fetch_all.assert_awaited_once()
        assert res.is_ok()
        assert set([x[1] for x in res.get_ok()]) == {"a", "c"}

    async def test_get_system_configs_propagates_error(self):
        self.rag_db.fetch_all.return_value = Result.Err(RuntimeError("boom"))

        res = await self.svc.get_system_configs()

        self.rag_db.fetch_all.assert_awaited_once()
        assert res.is_error()
        assert "boom" in str(res.get_error())

