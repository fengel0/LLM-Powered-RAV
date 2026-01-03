# tests/test_grading_service_usecases.py
import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from core.result import Result
from core.singelton import SingletonMeta

from domain.database.validation.interface import EvaluationDatabase
from domain.database.validation.model import RAGSystemAnswer, TestSample
from domain.database.config.model import Config, GradingServiceConfig
from domain.database.facts.interface import FactStore
from domain.hippo_rag.interfaces import OpenIEInterface
from domain.llm.interface import AsyncLLM

from domain_test import AsyncTestBase

from grading_service.usecase.grading import (
    GradingServiceUsecases,
    SmallRating,
    IsTheFactInTheResponse,
)

logger = logging.getLogger(__name__)


class TestGradingServiceUsecases(AsyncTestBase):
    __test__ = True

    def setup_method_sync(self, _name: str):
        # reset singleton

        # deps
        self.llm: AsyncLLM = AsyncMock()
        self.fact_store: FactStore = AsyncMock()
        self.db: EvaluationDatabase = AsyncMock()
        self.openie: OpenIEInterface = AsyncMock()

        # minimal config stub
        cfg_data = SimpleNamespace(
            system_prompt_correctnes="rate correctness",
            system_prompt_completness="is fact in answer",
            system_prompt_completness_context="is fact in context",
        )
        self.config: Config[GradingServiceConfig] = SimpleNamespace(
            id="cfg-1", data=cfg_data
        )  # type: ignore[assignment]

        # create SUT
        self.sut = GradingServiceUsecases.create(
            llm=self.llm,
            openie=self.openie,
            fact_store=self.fact_store,
            config=self.config,  # type: ignore[arg-type]
            database=self.db,
            worker_count=2,
        )

        # fixtures
        self.sample: TestSample = SimpleNamespace(
            id="s1",
            question="What is X?",
            expected_answer="X is Y.",
            expected_facts=["f1", "f2"],
        )
        self.answer: RAGSystemAnswer = SimpleNamespace(
            id="a1",
            answer="The answer mentions f1 and f2.",
            given_rag_context=["ctx A", "ctx B"],
        )

    def teardown_method_sync(self, _name: str):
        SingletonMeta.clear_all()

    # ------------------------------ helpers ---------------------------------

    async def _stub_llm_yes_for_facts_and_good_rating(self, *_args, **kwargs):
        model = kwargs.get("model")
        if model is IsTheFactInTheResponse:
            return Result.Ok(IsTheFactInTheResponse(is_fact_in_response=True))
        if model is SmallRating:
            return Result.Ok(SmallRating(correctness=0.9, reasoning="good"))
        raise AssertionError("Unexpected model passed to LLM")

    # ----------------------------- evaluate_answer ---------------------------

    async def test_evaluate_answer_returns_ok_when_already_evaluated(self):
        # _can_evaluation_begin path: sample + answer exist; already evaluated => no work
        self.db.get.return_value = Result.Ok(self.sample)
        self.db.was_question_already_answered_by_config.return_value = Result.Ok(
            self.answer
        )
        self.db.was_answer_of_question_already_evaled_by_system.return_value = (
            Result.Ok(True)
        )

        with patch(
            "grading_service.usecase.grading.index_with_queue",
            new=AsyncMock(return_value=Result.Ok(None)),
        ):
            res = await self.sut.evaluate_answer("s1", "rag-1")

        assert res.is_ok()
        self.db.add_llm_rating.assert_not_awaited()
        self.db.add_fact_counts_to_system_id.assert_not_awaited()

    async def test_evaluate_answer_happy_path(self):
        # can begin: sample + answer exist; not evaluated yet
        self.db.get.return_value = Result.Ok(self.sample)
        self.db.was_question_already_answered_by_config.return_value = Result.Ok(
            self.answer
        )
        self.db.was_answer_of_question_already_evaled_by_system.return_value = (
            Result.Ok(False)
        )
        self.db.add_fact_counts_to_system_id.return_value = Result.Ok(None)
        self.db.add_llm_rating.return_value = Result.Ok(None)

        # facts extraction: miss cache -> openie -> store -> ok
        self.fact_store.get_facts_to_hash.return_value = Result.Ok(None)
        self.openie.openie.return_value = Result.Ok(
            SimpleNamespace(triplets=SimpleNamespace(triples=["t1", "t2"]))
        )
        self.fact_store.store_facts.return_value = Result.Ok(None)

        # LLM: fact checks + final rating
        self.llm.get_structured_output.side_effect = (
            self._stub_llm_yes_for_facts_and_good_rating
        )

        # deterministic queue
        async def _linear_queue(objects, workers, index_one):
            for obj in objects:
                r = await index_one(obj)
                if r.is_error():
                    return r
            return Result.Ok(None)

        with patch(
            "grading_service.usecase.grading.index_with_queue", new=_linear_queue
        ):
            res = await self.sut.evaluate_answer("s1", "rag-1")

        assert res.is_ok()
        self.db.add_fact_counts_to_system_id.assert_awaited()
        self.db.add_llm_rating.assert_awaited()
        assert self.llm.get_structured_output.await_count >= 1

    async def test_evaluate_answer_bubbles_errors_from_dependencies(self):
        # sample fetch error
        self.db.get.return_value = Result.Err(Exception("db-sample"))
        res = await self.sut.evaluate_answer("s1", "rag-1")
        assert res.is_error()
        assert "db-sample" in str(res.get_error())

    # ----------------------------- _extract_facts ----------------------------

    async def test_extract_facts_uses_cache(self):
        self.fact_store.get_facts_to_hash.return_value = Result.Ok(["a", "b"])
        res = await self.sut._extract_facts("some passage")
        assert res.is_ok()
        assert res.get_ok() == ["a", "b"]
        self.openie.openie.assert_not_awaited()
        self.fact_store.store_facts.assert_not_awaited()

    async def test_extract_facts_calls_openie_when_missing(self):
        self.fact_store.get_facts_to_hash.return_value = Result.Ok(None)
        self.openie.openie.return_value = Result.Ok(
            SimpleNamespace(triplets=SimpleNamespace(triples=["x", "y"]))
        )
        self.fact_store.store_facts.return_value = Result.Ok(None)

        res = await self.sut._extract_facts("passage")
        assert res.is_ok()
        assert res.get_ok() == ["x", "y"]
        self.openie.openie.assert_awaited_once()
        self.fact_store.store_facts.assert_awaited_once()

    # ------------------------------ _eval_facts ------------------------------

    async def test_eval_facts_marks_facts_true_in_answer_and_context(self):
        # LLM always says "yes"
        self.llm.get_structured_output.side_effect = (
            self._stub_llm_yes_for_facts_and_good_rating
        )

        async def _linear_queue(objects, workers, index_one):
            for obj in objects:
                r = await index_one(obj)
                if r.is_error():
                    return r
            return Result.Ok(None)

        with patch(
            "grading_service.usecase.grading.index_with_queue", new=_linear_queue
        ):
            res = await self.sut._eval_facts(self.answer, self.sample)

        assert res.is_ok()
        holder = res.get_ok()
        assert holder.anwers == [True, True]
        assert holder.context == [True, True]

    # --------------------------- _can_evaluation_begin -----------------------

    async def test_can_evaluation_begin_sample_missing(self):
        self.db.get.return_value = Result.Ok(None)
        res, flag = await self.sut._can_evaluation_begin("s-missing", "rag-x")
        assert res.is_error()
        assert flag is False

    async def test_can_evaluation_begin_answer_missing(self):
        self.db.get.return_value = Result.Ok(self.sample)
        self.db.was_question_already_answered_by_config.return_value = Result.Ok(None)
        res, flag = await self.sut._can_evaluation_begin("s1", "rag-x")
        assert res.is_error()
        assert flag is False

    async def test_can_evaluation_begin_ok_to_proceed(self):
        self.db.get.return_value = Result.Ok(self.sample)
        self.db.was_question_already_answered_by_config.return_value = Result.Ok(
            self.answer
        )
        self.db.was_answer_of_question_already_evaled_by_system.return_value = (
            Result.Ok(False)
        )
        res, flag = await self.sut._can_evaluation_begin("s1", "rag-x")
        assert res.is_ok()
        assert flag is True
