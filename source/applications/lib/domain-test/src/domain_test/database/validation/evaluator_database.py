import logging
import uuid

from domain_test import AsyncTestBase
from core.result import Result
from domain.database.validation.model import Evaluator

logger = logging.getLogger(__name__)


def _uid() -> str:
    return uuid.uuid4().hex


def make_evaluator(username: str = "bob") -> Evaluator:
    return Evaluator(id=_uid(), username=username)


class TestDBEvaluatorDatabase(AsyncTestBase):
    """
    Storage-agnostic tests for an Evaluator database implementation.
    Subclasses must assign `self.evaluator_db` in setup_method_async.
    """
    evaluator_db: any

    async def test_create_get_get_by_name_and_get_all(self):
        db = self.evaluator_db

        evaluator = make_evaluator("bob")

        # create
        create_res: Result[str] = await db.create(evaluator)
        if create_res.is_error():
            logger.error(create_res.get_error())
        assert create_res.is_ok()
        evaluator_id = create_res.get_ok()

        # get(id)
        get_res = await db.get(evaluator_id)
        if get_res.is_error():
            logger.error(get_res.get_error())
        assert get_res.is_ok()
        evaluator_db = get_res.get_ok()
        assert evaluator_db is not None
        assert evaluator_db.username == "bob"

        # get_evalutor_by_name
        name_res = await db.get_evalutor_by_name("bob")
        if name_res.is_error():
            logger.error(name_res.get_error())
        assert name_res.is_ok()
        assert name_res.get_ok() is not None

        # get_all
        all_res = await db.get_all()
        assert all_res.is_ok()
        if all_res.is_error():
            logger.error(all_res.get_error())
        assert len(all_res.get_ok()) >= 1