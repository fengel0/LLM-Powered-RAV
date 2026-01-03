# tests/test_evaluation_service_usecases.py
import logging
from unittest.mock import AsyncMock, MagicMock

from core.singelton import SingletonMeta
from core.result import Result
from domain.database.validation.model import (
    Evaluator,
    RAGSystemAnswer,
    TestSample,
    RatingUser,
    RatingLLM,
    RAGSystemAnswerRatings,
)
from evaluation_service.usecase.evaluation import (
    EvaluationServiceUsecases,
    EvaluationServiceConfig,
)
from domain_test import AsyncTestBase

ADMIN_TOKEN = "secret-admin-token"

logger = logging.getLogger(__name__)


class TestEvaluationServiceUsecases(AsyncTestBase):
    """Unit-tests for the *service* layer. Every outward-facing method is
    exercised here by mocking both database adapters.
    """

    __test__ = True

    # ---------------------------------------------------------------------
    # Test harness setup / teardown
    # ---------------------------------------------------------------------
    def setup_method_sync(self, test_name: str):
        # ----- mock EvaluatorDatabase -------------------------------------
        self.evaluator_db = MagicMock()
        self.evaluator_db.get_evalutor_by_name = AsyncMock()
        self.evaluator_db.create = AsyncMock()
        self.evaluator_db.get_all = AsyncMock()

        # ----- mock EvaluationDatabase ------------------------------------
        self.evaluation_db = MagicMock()
        self.evaluation_db.create = AsyncMock()
        self.evaluation_db.add_user_rating = AsyncMock()
        self.evaluation_db.add_llm_rating = AsyncMock()
        self.evaluation_db.add_system_answer = AsyncMock()
        self.evaluation_db.fetch_dataset_question = AsyncMock()
        self.evaluation_db.fetch_dataset_question_number = AsyncMock()
        self.evaluation_db.fetch_datasets = AsyncMock()
        self.evaluation_db.fetch_answers_and_ratings = AsyncMock()
        self.evaluation_db.fetch_ratings_of_config = AsyncMock()
        self.evaluation_db.fetch_ratings_of_user = AsyncMock()
        self.evaluation_db.fetch_ratings_from_dataset_for_certain_config = AsyncMock()
        self.evaluation_db.fetch_ratings_from_dataset = AsyncMock()
        self.evaluation_db.get_sample_by_hash = AsyncMock()

        # ----- service instance -------------------------------------------
        cfg = EvaluationServiceConfig(admin_token=ADMIN_TOKEN)
        self.svc = EvaluationServiceUsecases.__new__(EvaluationServiceUsecases)
        self.svc._init_once(
            evaluator_database=self.evaluator_db,
            evaluation_database=self.evaluation_db,
            config=cfg,
        )

    def teardown_method_sync(self, test_name: str):
        SingletonMeta.clear_all()

    # ---------------------------------------------------------------------
    # create / add-question ------------------------------------------------
    # ---------------------------------------------------------------------
    async def test_add_question_success(self):
        question = MagicMock(spec=TestSample)
        question.question = "lol"
        self.evaluation_db.create.return_value = Result.Ok("q-id")
        self.evaluation_db.get_sample_by_hash.return_value = Result.Ok(None)

        res = await self.svc.add_question(question, ADMIN_TOKEN)

        self.evaluation_db.create.assert_awaited_once_with(obj=question)
        assert res.is_ok()
        assert res.get_ok() == "q-id"

    async def test_add_question_invalid_token(self):
        question = MagicMock(spec=TestSample)

        res = await self.svc.add_question(question, "wrong")

        self.evaluation_db.create.assert_not_called()
        assert res.is_error()
        assert isinstance(res.get_error(), PermissionError)

    # ---------------------------------------------------------------------
    # add-user -------------------------------------------------------------
    # ---------------------------------------------------------------------
    async def test_add_user_success(self):
        self.evaluator_db.get_evalutor_by_name.return_value = Result.Ok(None)
        self.evaluator_db.create.return_value = Result.Ok("user-id")

        res = await self.svc.add_user("alice", ADMIN_TOKEN)

        self.evaluator_db.get_evalutor_by_name.assert_awaited_once_with(
            username="alice"
        )
        self.evaluator_db.create.assert_awaited_once()
        assert res.is_ok()
        assert res.get_ok() == "user-id"

    async def test_add_user_username_taken(self):
        self.evaluator_db.get_evalutor_by_name.return_value = Result.Ok(
            Evaluator(id="1", username="bob")
        )

        res = await self.svc.add_user("bob", ADMIN_TOKEN)

        self.evaluator_db.create.assert_not_called()
        assert res.is_error()
        assert "username is taken" in str(res.get_error())

    async def test_add_user_invalid_token(self):
        res = await self.svc.add_user("anyone", "bad-token")

        self.evaluator_db.get_evalutor_by_name.assert_not_called()
        assert res.is_error()
        assert isinstance(res.get_error(), PermissionError)

    # ---------------------------------------------------------------------
    # get-users ------------------------------------------------------------
    # ---------------------------------------------------------------------
    async def test_get_users_success(self):
        expected = [Evaluator(id="1", username="eva")]
        self.evaluator_db.get_all.return_value = Result.Ok(expected)

        res = await self.svc.get_users(ADMIN_TOKEN)

        self.evaluator_db.get_all.assert_awaited_once()
        assert res.is_ok()
        assert res.get_ok() == expected

    async def test_get_users_invalid_token(self):
        res = await self.svc.get_users("bad")

        self.evaluator_db.get_all.assert_not_called()
        assert res.is_error()
        assert isinstance(res.get_error(), PermissionError)

    # ---------------------------------------------------------------------
    # add-user-evaluation ---------------------------------------------------
    # ---------------------------------------------------------------------
    async def test_add_user_evaluation_success(self):
        evaluator = Evaluator(id="9", username="rater")
        self.evaluator_db.get_evalutor_by_name.return_value = Result.Ok(evaluator)
        rating = MagicMock(spec=RatingUser, creator="rater")
        self.evaluation_db.add_user_rating.return_value = Result.Ok(None)

        res = await self.svc.add_user_evaluation("ans-1", rating)

        self.evaluator_db.get_evalutor_by_name.assert_awaited_once_with(
            username="rater"
        )
        self.evaluation_db.add_user_rating.assert_awaited_once_with(
            answer_id="ans-1", rating=rating
        )
        assert res.is_ok()

    async def test_add_user_evaluation_propagates_error(self):
        self.evaluator_db.get_evalutor_by_name.return_value = Result.Err(
            RuntimeError("DB down")
        )
        rating = MagicMock(spec=RatingUser, creator="no-one")

        res = await self.svc.add_user_evaluation("a", rating)

        self.evaluation_db.add_user_rating.assert_not_called()
        assert res.is_error()
        assert "DB down" in str(res.get_error())

    # ---------------------------------------------------------------------
    # add-llm-evaluation ----------------------------------------------------
    # ---------------------------------------------------------------------
    async def test_add_llm_evaluation_success(self):
        rating = MagicMock(spec=RatingLLM)
        self.evaluation_db.add_llm_rating.return_value = Result.Ok(None)

        res = await self.svc.add_llm_evaluation("ans", rating, ADMIN_TOKEN)

        self.evaluation_db.add_llm_rating.assert_awaited_once_with(
            answer_id="ans", rating=rating
        )
        assert res.is_ok()

    async def test_add_llm_evaluation_invalid_token(self):
        rating = MagicMock(spec=RatingLLM)

        res = await self.svc.add_llm_evaluation("a", rating, "bad")

        self.evaluation_db.add_llm_rating.assert_not_called()
        assert res.is_error()
        assert isinstance(res.get_error(), PermissionError)

    # ---------------------------------------------------------------------
    # add-system-answer -----------------------------------------------------
    # ---------------------------------------------------------------------
    async def test_add_system_answer_success(self):
        answer = MagicMock(spec=RAGSystemAnswer)
        self.evaluation_db.add_system_answer.return_value = Result.Ok(None)

        res = await self.svc.add_system_answer("sample-id", answer, ADMIN_TOKEN)

        self.evaluation_db.add_system_answer.assert_awaited_once_with(
            sample_id="sample-id", system_answer=answer
        )
        assert res.is_ok()

    async def test_add_system_answer_invalid_token(self):
        answer = MagicMock(spec=RAGSystemAnswer)

        res = await self.svc.add_system_answer("sample-id", answer, "no-token")

        self.evaluation_db.add_system_answer.assert_not_called()
        assert res.is_error()
        assert isinstance(res.get_error(), PermissionError)

    # ---------------------------------------------------------------------
    # dataset helpers -------------------------------------------------------
    # ---------------------------------------------------------------------
    async def test_fetch_dataset_question(self):
        expected = [MagicMock(spec=TestSample)]
        self.evaluation_db.fetch_dataset_question.return_value = Result.Ok(expected)

        res = await self.svc.fetch_dataset_question("ds-1", 0, 10, 0)

        self.evaluation_db.fetch_dataset_question.assert_awaited_once_with(
            dataset_id="ds-1", from_number=0, to_number=10, number_of_facts=0
        )
        assert res.is_ok()
        assert res.get_ok() == expected

    async def test_fetch_dataset_question_number(self):
        self.evaluation_db.fetch_dataset_question_number.return_value = Result.Ok(42)

        res = await self.svc.fetch_dataset_question_number("ds-id")

        self.evaluation_db.fetch_dataset_question_number.assert_awaited_once_with(
            dataset_id="ds-id"
        )
        assert res.is_ok()
        assert res.get_ok() == 42

    # ---------------------------------------------------------------------
    # ratings queries (newly added) ----------------------------------------
    # ---------------------------------------------------------------------
    async def test_fetch_ratings_of_config(self):
        ratings = [MagicMock(spec=RatingLLM)]
        self.evaluation_db.fetch_ratings_of_config.return_value = Result.Ok(ratings)

        res = await self.svc.fetch_ratings_of_config("conf-A")

        self.evaluation_db.fetch_ratings_of_config.assert_awaited_once_with(
            config_id="conf-A"
        )
        assert res.is_ok()
        assert res.get_ok() == ratings

    async def test_fetch_ratings_of_user(self):
        ratings = [MagicMock(spec=RatingUser)]
        self.evaluation_db.fetch_ratings_of_user.return_value = Result.Ok(ratings)

        res = await self.svc.fetch_ratings_of_user("alice")

        self.evaluation_db.fetch_ratings_of_user.assert_awaited_once_with(
            username="alice"
        )
        assert res.is_ok()
        assert res.get_ok() == ratings

    async def test_fetch_ratings_from_dataset(self):
        ratings = [MagicMock(spec=RatingLLM), MagicMock(spec=RatingUser)]
        self.evaluation_db.fetch_ratings_from_dataset.return_value = Result.Ok(ratings)

        res = await self.svc.fetch_ratings_from_dataset("ds-Z")

        self.evaluation_db.fetch_ratings_from_dataset.assert_awaited_once_with(
            dataset_name="ds-Z"
        )
        assert res.is_ok()
        assert res.get_ok() == ratings

    # ---------------------------------------------------------------------
    # answers with rating ---------------------------------------------------
    # ---------------------------------------------------------------------
    async def test_fetch_answers_with_rating(self):
        answers = [MagicMock(spec=RAGSystemAnswerRatings)]
        self.evaluation_db.fetch_answers_and_ratings.return_value = Result.Ok(answers)

        res = await self.svc.fetch_answers_with_rating("sample-1")

        self.evaluation_db.fetch_answers_and_ratings.assert_awaited_once_with(
            "sample-1"
        )
        assert res.is_ok()
        assert res.get_ok() == answers
