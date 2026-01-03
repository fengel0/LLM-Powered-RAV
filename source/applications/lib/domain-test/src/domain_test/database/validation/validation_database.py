# domain_test/database/validation/validation_db_extended.py
import logging
import uuid

from domain.database.validation.interface import EvaluationDatabase, EvaluatorDatabase

from domain_test import AsyncTestBase
from core.hash import compute_mdhash_id

from domain.database.validation.model import (
    TestSample,
    RAGSystemAnswer,
    Evaluator,
    RatingLLM,
    RatingUser,
    RatingQuery,
    WhatToFetch,
)

logger = logging.getLogger(__name__)


# ----------------------------- tiny helpers ----------------------------- #
def uid() -> str:
    return uuid.uuid4().hex


def make_evaluator(username: str = "alice") -> Evaluator:
    return Evaluator(id=uid(), username=username)


def make_answer(config_id: str = "answer-1") -> RAGSystemAnswer:
    return RAGSystemAnswer(
        id="",
        answer="42",
        given_rag_context=["context"],
        config_id=config_id,
        retrieval_latency_ms=1.0,
        generation_latency_ms=2.0,
        token_count_prompt=10,
        facts=["fact_one", "fact_tow"],
        token_count_completion=20,
        number_of_facts_in_answer=20,
        number_of_facts_in_context=20,
        answer_confidence=None,
    )


def make_sample(dataset_id: str = "dataset_id") -> TestSample:
    return TestSample(
        id=uid(),
        dataset_id=dataset_id,
        retrival_complexity=0.5,
        question_hash=compute_mdhash_id(str(uuid.uuid4())),
        question="What is the answer to life?",
        expected_answer="42",
        expected_facts=["42"],
        expected_context="42",
        question_type="numeric",
        metatdata={"lol": "i"},
        metatdata_filter={"tmp": ["lol", "lol"]},
    )


class TestDBValidationDatabaseExtended(AsyncTestBase):
    """
    Storage-agnostic validation DB test suite.
    Subclasses must set:
      - self.eval_db  -> implements PostgresDBEvaluation-compatible API
      - self.evaluator_db -> implements PostgresDBEvaluatorDatabase-compatible API
    """

    eval_db: EvaluationDatabase
    evaluator_db: EvaluatorDatabase

    # ----------------------------- helpers ----------------------------- #
    def _assert_all_config_id(self, ratings: list[RatingLLM], config_id: str):
        assert ratings, "ratings list is empty – unexpected in this test"
        assert all(r.config_id == config_id for r in ratings)

    async def _create_sample_with_answer_and_ratings(
        self,
        *,
        dataset_id: str,
        rag_cfg: str,
        grader_cfgs: list[str],
        user_names: list[str],
    ) -> tuple[str, str]:
        """Insert one sample, one system answer, LLM & user ratings."""
        sample = make_sample(dataset_id=dataset_id)
        result = await self.eval_db.create(sample)
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()
        sample_id = result.get_ok()

        result = await self.eval_db.add_system_answer(
            sample_id, make_answer(config_id=rag_cfg)
        )
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()
        answer_id = result.get_ok()

        for cfg in grader_cfgs:
            result = await self.eval_db.add_llm_rating(
                answer_id,
                RatingLLM(
                    rationale=f"llm-{cfg}",
                    config_id=cfg,
                    correctness=0.8,
                    relevant_chunks=[1],
                    completeness=[],
                    completeness_in_data=[],
                ),
            )
            if result.is_error():
                logger.error(result.get_error())
            assert result.is_ok()

        for username in user_names:
            # ensure evaluator exists
            result = await self.evaluator_db.create(make_evaluator(username))
            if result.is_error():
                logger.error(result.get_error())
            assert result.is_ok()

            result = await self.eval_db.add_user_rating(
                answer_id,
                RatingUser(
                    rationale=f"human-{username}",
                    creator=username,
                    correctness=0.9,
                    relevant_chunks=[1],
                    completeness=[],
                    completeness_in_data=[],
                ),
            )
            if result.is_error():
                logger.error(result.get_error())
            assert result.is_ok()

        return sample_id, answer_id

    # ------------------------------- tests ------------------------------ #
    async def test_crud_lifecycle_for_test_sample(self):
        from core.model import DublicateException

        # create
        sample = make_sample()
        result = await self.eval_db.create(sample)
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()
        sample_id = result.get_ok()
        assert sample_id

        # get
        res = await self.eval_db.get(sample_id)
        if res.is_error():
            logger.error(res.get_error())
        assert res.is_ok()
        stored = res.get_ok()
        assert stored is not None

        # get by hash
        res = await self.eval_db.get_sample_by_hash(hash=stored.question_hash)
        if res.is_error():
            logger.error(res.get_error())
        assert res.is_ok()
        assert res.get_ok() is not None

        # duplicate create should error
        result = await self.eval_db.create(sample)
        if result.is_ok():
            logger.error("duplicate create unexpectedly succeeded")
        assert result.is_error()
        assert isinstance(result.get_error(), DublicateException)

        # update
        stored.question = "What is the capital of France?"
        result = await self.eval_db.update(stored)
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()

        res2 = await self.eval_db.get(sample_id)
        if res2.is_error():
            logger.error(res2.get_error())
        assert res2.is_ok()
        q = res2.get_ok()
        assert q and q.question == "What is the capital of France?"

        # get_all
        all_res = await self.eval_db.get_all()
        if all_res.is_error():
            logger.error(all_res.get_error())
        assert all_res.is_ok()
        assert sample_id in [s.id for s in all_res.get_ok()]

        # delete
        del_res = await self.eval_db.delete(sample_id)
        if del_res.is_error():
            logger.error(del_res.get_error())
        assert del_res.is_ok()

        # get (None)
        res_deleted = await self.eval_db.get(sample_id)
        if res_deleted.is_error():
            logger.error(res_deleted.get_error())
        assert res_deleted.is_ok()
        assert res_deleted.get_ok() is None

    async def test_fetch_dataset_question_with_pagination_and_fact_filter(self):
        DATASET = "ds-PAGE"
        for i in range(10):
            s = make_sample(dataset_id=DATASET)
            s.expected_facts = [f"fact-{j}" for j in range(i)]
            result = await self.eval_db.create(s)
            if result.is_error():
                logger.error(result.get_error())
            assert result.is_ok()

        res = await self.eval_db.fetch_dataset_question(
            DATASET, from_number=3, to_number=7, number_of_facts=3
        )
        if res.is_error():
            logger.error(res.get_error())
        assert res.is_ok()
        items = res.get_ok()
        assert len(items) == 4
        assert all(len(it.expected_facts) >= 3 for it in items)

    async def test_update_answer(self):
        DATASET = "ds-COMBINED"
        sample = make_sample(DATASET)
        answer = make_answer(config_id="config-id")

        result = await self.eval_db.create(sample)
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()
        sample_id = result.get_ok()

        result = await self.eval_db.add_system_answer(
            sample_id=sample_id, system_answer=answer
        )
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()
        answer_id = result.get_ok()

        result = await self.eval_db.was_question_already_answered_by_config(
            sample_id=sample_id, config_id="config-id"
        )
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()
        found = result.get_ok()
        assert found and found.id == answer_id

        found.facts = [*found.facts, "ich love cookies"]
        found.number_of_facts_in_answer += 10
        found.number_of_facts_in_context += 10

        upd = await self.eval_db.add_fact_counts_to_system_id(
            answer_id=answer_id,
            facts=found.facts,
            number_of_facts_in_anwer=found.number_of_facts_in_answer,
            number_of_facts_in_context=found.number_of_facts_in_context,
        )
        if upd.is_error():
            logger.error(upd.get_error())
        assert upd.is_ok()

        again = await self.eval_db.was_question_already_answered_by_config(
            sample_id=sample_id, config_id="config-id"
        )
        if again.is_error():
            logger.error(again.get_error())
        assert again.is_ok()
        after = again.get_ok()
        assert after and after.id == answer_id
        assert after.number_of_facts_in_context == found.number_of_facts_in_context
        assert len(after.facts) == len(found.facts)

    async def test_fetch_answers_and_ratings_returns_combined_lists(self):
        DATASET = "ds-COMBINED"
        sample_id, _ = await self._create_sample_with_answer_and_ratings(
            dataset_id=DATASET,
            rag_cfg="rag-Z",
            grader_cfgs=["grader-1", "grader-2"],
            user_names=["alice", "bob"],
        )

        res = await self.eval_db.fetch_answers_and_ratings(str(sample_id))
        if res.is_error():
            logger.error(res.get_error())
        assert res.is_ok()
        answers = res.get_ok()
        assert len(answers) == 1
        first = answers[0]
        assert len(first.facts) == 2
        assert first.number_of_facts_in_context == 20
        assert first.number_of_facts_in_answer == 20
        assert len(first.llm_ratings) == 2
        assert len(first.human_ratings) == 2
        assert len(first.human_ratings[0].relevant_chunks) == 1
        assert len(first.llm_ratings[0].relevant_chunks) == 1

    async def test_fetch_datasets_returns_unique_ids(self):
        for ds in ["ds-A", "ds-B", "ds-A", "ds-C"]:
            result = await self.eval_db.create(make_sample(dataset_id=ds))
            if result.is_error():
                logger.error(result.get_error())
            assert result.is_ok()

        res = await self.eval_db.fetch_datasets()
        if res.is_error():
            logger.error(res.get_error())
        assert res.is_ok()
        assert set(res.get_ok()) == {"ds-A", "ds-B", "ds-C"}

    async def test_fetch_ratings_from_dataset_for_a_certain_system(self):
        DATASET = "ds-TARGET-SYS"
        RAG_MATCH = "rag-MATCH"

        _ = await self._create_sample_with_answer_and_ratings(
            dataset_id=DATASET,
            rag_cfg=RAG_MATCH,
            grader_cfgs=["grader-X"],
            user_names=["user-1"],
        )
        _ = await self._create_sample_with_answer_and_ratings(
            dataset_id=DATASET,
            rag_cfg="rag-OTHER",
            grader_cfgs=["grader-X"],
            user_names=[],
        )

        res = await self.eval_db.fetch_ratings_from_dataset_for_a_certain_sytem(
            DATASET, RAG_MATCH
        )
        if res.is_error():
            logger.error(res.get_error())
        assert res.is_ok()
        ratings = res.get_ok()
        assert len(ratings) == 2  # 1 human + 1 llm from the matching answer

    async def test_fetch_ratings_from_dataset_from_a_certain_eval_system(self):
        DATASET = "ds-EVAL-FILTER"
        GRADER_MATCH = "grader-MATCH"

        _ = await self._create_sample_with_answer_and_ratings(
            dataset_id=DATASET,
            rag_cfg="rag-A",
            grader_cfgs=[GRADER_MATCH],
            user_names=[],
        )
        _ = await self._create_sample_with_answer_and_ratings(
            dataset_id=DATASET,
            rag_cfg="rag-B",
            grader_cfgs=["grader-OTHER"],
            user_names=[],
        )

        res = await self.eval_db.fetch_ratings_from_dataset_from_a_certain_eval_system(
            DATASET, GRADER_MATCH
        )
        if res.is_error():
            logger.error(res.get_error())
        assert res.is_ok()
        ratings = res.get_ok()
        assert len(ratings) == 1 and ratings[0].config_id == GRADER_MATCH

    async def test_fetch_ratings_of_config(self):
        result = await self.eval_db.create(make_sample())
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()
        sample_id = result.get_ok()

        ans_match = make_answer(config_id="conf-MATCH")
        ans_other = make_answer(config_id="conf-OTHER")

        result = await self.eval_db.add_system_answer(sample_id, ans_match)
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()
        ans_match_id = result.get_ok()

        result = await self.eval_db.add_system_answer(sample_id, ans_other)
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()

        result = await self.eval_db.add_llm_rating(
            ans_match_id,
            RatingLLM(
                rationale="solid",
                config_id="conf-MATCH",
                correctness=0.9,
                completeness=[],
                relevant_chunks=[1],
                completeness_in_data=[],
            ),
        )
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()

        result = await self.eval_db.add_llm_rating(
            ans_match_id,
            RatingLLM(
                rationale="meh",
                config_id="conf-OTHER",
                correctness=0.5,
                completeness=[],
                relevant_chunks=[1],
                completeness_in_data=[],
            ),
        )
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()

        res = await self.eval_db.fetch_ratings_of_config("conf-MATCH")
        if res.is_error():
            logger.error(res.get_error())
        assert res.is_ok()
        self._assert_all_config_id(res.get_ok(), "conf-MATCH")

    async def test_fetch_ratings_of_user(self):
        result = await self.eval_db.create(make_sample())
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()
        sample_id = result.get_ok()

        result = await self.eval_db.add_system_answer(sample_id, make_answer())
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()
        answer_id = result.get_ok()

        target = make_evaluator("alice")
        other = make_evaluator("bob")

        r = await self.evaluator_db.create(target)
        if r.is_error():
            logger.error(r.get_error())
        assert r.is_ok()

        r = await self.evaluator_db.create(other)
        if r.is_error():
            logger.error(r.get_error())
        assert r.is_ok()

        r = await self.eval_db.add_user_rating(
            answer_id,
            RatingUser(
                rationale="great",
                creator=target.username,
                correctness=0.95,
                relevant_chunks=[1],
                completeness=[True],
                completeness_in_data=[True],
            ),
        )
        if r.is_error():
            logger.error(r.get_error())
        assert r.is_ok()

        r = await self.eval_db.add_user_rating(
            answer_id,
            RatingUser(
                rationale="meh",
                creator=other.username,
                correctness=0.2,
                relevant_chunks=[1],
                completeness=[False],
                completeness_in_data=[False],
            ),
        )
        if r.is_error():
            logger.error(r.get_error())
        assert r.is_ok()

        res = await self.eval_db.fetch_ratings_of_user(target.username)
        if res.is_error():
            logger.error(res.get_error())
        assert res.is_ok()
        ratings = res.get_ok()
        assert ratings and all(r.creator == target.username for r in ratings)

    async def test_fetch_ratings_from_dataset(self):
        sample_ds = make_sample()
        sample_ds.dataset_id = "ds-TARGET"
        result = await self.eval_db.create(sample_ds)
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()
        sample_ds_id = result.get_ok()

        result = await self.eval_db.add_system_answer(sample_ds_id, make_answer())
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()
        answer_ds_id = result.get_ok()

        sample_other = make_sample()
        sample_other.dataset_id = "ds-OTHER"
        result = await self.eval_db.create(sample_other)
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()
        sample_other_id = result.get_ok()

        result = await self.eval_db.add_system_answer(sample_other_id, make_answer())
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()
        answer_other_id = result.get_ok()

        r = await self.eval_db.add_llm_rating(
            answer_ds_id,
            RatingLLM(
                rationale="good",
                config_id="conf-X",
                correctness=0.8,
                relevant_chunks=[1],
                completeness=[],
                completeness_in_data=[],
            ),
        )
        if r.is_error():
            logger.error(r.get_error())
        assert r.is_ok()

        r = await self.eval_db.add_llm_rating(
            answer_other_id,
            RatingLLM(
                rationale="bad",
                config_id="conf-Y",
                correctness=0.1,
                relevant_chunks=[1],
                completeness=[],
                completeness_in_data=[],
            ),
        )
        if r.is_error():
            logger.error(r.get_error())
        assert r.is_ok()

        r = await self.evaluator_db.create(make_evaluator("carol"))
        if r.is_error():
            logger.error(r.get_error())
        assert r.is_ok()

        r = await self.eval_db.add_user_rating(
            answer_ds_id,
            RatingUser(
                rationale="great",
                creator="carol",
                correctness=0.95,
                relevant_chunks=[1],
                completeness=[],
                completeness_in_data=[],
            ),
        )
        if r.is_error():
            logger.error(r.get_error())
        assert r.is_ok()

        r = await self.eval_db.add_user_rating(
            answer_other_id,
            RatingUser(
                rationale="meh",
                creator="carol",
                correctness=0.3,
                relevant_chunks=[1],
                completeness=[],
                completeness_in_data=[],
            ),
        )
        if r.is_error():
            logger.error(r.get_error())
        assert r.is_ok()

        res = await self.eval_db.fetch_ratings_from_dataset("ds-TARGET")
        if res.is_error():
            logger.error(res.get_error())
        assert res.is_ok()
        assert len(res.get_ok()) == 2

    async def test_fetch_dataset_question_number(self):
        for _ in range(5):
            s = make_sample()
            s.dataset_id = "ds-COUNT"
            result = await self.eval_db.create(s)
            if result.is_error():
                logger.error(result.get_error())
            assert result.is_ok()

        res = await self.eval_db.fetch_dataset_question_number("ds-COUNT")
        if res.is_error():
            logger.error(res.get_error())
        assert res.is_ok()
        assert res.get_ok() == 5

    async def test_fetch_ratings_from_dataset_from_a_certain_system_by_a_certain_system(
        self,
    ):
        tgt_dataset = "ds-SYS-GRADE"
        rag_system_cfg = "rag-SYS-A"
        grading_cfg = "grader-A"

        result = await self.eval_db.create(make_sample(dataset_id=tgt_dataset))
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()
        sample_tgt_id = result.get_ok()

        result = await self.eval_db.add_system_answer(
            sample_tgt_id, make_answer(config_id=rag_system_cfg)
        )
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()
        answer_match_id = result.get_ok()

        answers_result = await self.eval_db.get_anwers_by_config(
            config_id=rag_system_cfg
        )
        if answers_result.is_error():
            logger.error(answers_result.get_error())
        assert answers_result.is_ok()
        assert len(answers_result.get_ok()) == 1

        answers_result = await self.eval_db.get_anwers_by_config(
            config_id=rag_system_cfg, dataset_option=tgt_dataset
        )
        if answers_result.is_error():
            logger.error(answers_result.get_error())
        assert answers_result.is_ok()
        assert len(answers_result.get_ok()) == 1

        answers_result = await self.eval_db.get_anwers_by_config(
            config_id=rag_system_cfg, dataset_option="none"
        )
        if answers_result.is_error():
            logger.error(answers_result.get_error())
        assert answers_result.is_ok()
        assert len(answers_result.get_ok()) == 0

        answers_result = await self.eval_db.get_anwers_by_config(config_id="hfsd")
        if answers_result.is_error():
            logger.error(answers_result.get_error())
        assert answers_result.is_ok()
        assert len(answers_result.get_ok()) == 0

        r = await self.eval_db.add_llm_rating(
            answer_match_id,
            RatingLLM(
                rationale="good",
                config_id=grading_cfg,
                correctness=0.9,
                relevant_chunks=[1],
                completeness=[],
                completeness_in_data=[],
            ),
        )
        if r.is_error():
            logger.error(r.get_error())
        assert r.is_ok()

        r = await self.eval_db.add_llm_rating(
            answer_match_id,
            RatingLLM(
                rationale="wrong grader",
                config_id="grader-B",
                correctness=0.1,
                relevant_chunks=[1],
                completeness=[],
                completeness_in_data=[],
            ),
        )
        if r.is_error():
            logger.error(r.get_error())
        assert r.is_ok()

        result = await self.eval_db.add_system_answer(
            sample_tgt_id, make_answer(config_id="rag-SYS-B")
        )
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()
        answer_other_sys_id = result.get_ok()

        r = await self.eval_db.add_llm_rating(
            answer_other_sys_id,
            RatingLLM(
                rationale="other sys",
                config_id=grading_cfg,
                correctness=0.7,
                relevant_chunks=[1],
                completeness=[],
                completeness_in_data=[],
            ),
        )
        if r.is_error():
            logger.error(r.get_error())
        assert r.is_ok()

        result = await self.eval_db.create(make_sample(dataset_id="ds-CTRL"))
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()
        sample_ctrl_id = result.get_ok()

        result = await self.eval_db.add_system_answer(
            sample_ctrl_id, make_answer(config_id=rag_system_cfg)
        )
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()
        answer_ctrl_id = result.get_ok()

        r = await self.eval_db.add_llm_rating(
            answer_ctrl_id,
            RatingLLM(
                relevant_chunks=[1],
                rationale="ctrl",
                config_id=grading_cfg,
                correctness=0.3,
                completeness=[],
                completeness_in_data=[],
            ),
        )
        if r.is_error():
            logger.error(r.get_error())
        assert r.is_ok()

        res = await self.eval_db.fetch_ratings_from_dataset_from_a_certain_system_by_a_certain_system(
            tgt_dataset, rag_system_cfg, grading_cfg
        )
        if res.is_error():
            logger.error(res.get_error())
        assert res.is_ok()
        ratings = res.get_ok()
        assert len(ratings) == 1
        self._assert_all_config_id(ratings, grading_cfg)

    async def test_was_question_already_answered_by_config(self):
        result = await self.eval_db.create(make_sample())
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()
        sample_id = result.get_ok()

        result = await self.eval_db.add_system_answer(
            sample_id, make_answer(config_id="conf-X")
        )
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()
        answer_id = result.get_ok()

        res_present = await self.eval_db.was_question_already_answered_by_config(
            sample_id, "conf-X"
        )
        if res_present.is_error():
            logger.error(res_present.get_error())
        assert res_present.is_ok()
        present = res_present.get_ok()
        assert present and present.id == answer_id

        res_absent = await self.eval_db.was_question_already_answered_by_config(
            sample_id, "conf-Y"
        )
        if res_absent.is_error():
            logger.error(res_absent.get_error())
        assert res_absent.is_ok() and res_absent.get_ok() is None

    async def test_get_evaluator_by_name(self):
        r = await self.evaluator_db.create(make_evaluator("alice"))
        if r.is_error():
            logger.error(r.get_error())
        assert r.is_ok()

        r = await self.evaluator_db.create(make_evaluator("bob"))
        if r.is_error():
            logger.error(r.get_error())
        assert r.is_ok()

        res = await self.evaluator_db.get_evalutor_by_name("alice")
        if res.is_error():
            logger.error(res.get_error())
        assert res.is_ok()
        ev = res.get_ok()
        assert ev and ev.username == "alice"

        res_none = await self.evaluator_db.get_evalutor_by_name("charlie")
        if res_none.is_error():
            logger.error(res_none.get_error())
        assert res_none.is_ok()
        assert res_none.get_ok() is None

    async def test_was_answer_of_question_already_evaled_by_system(self):
        result = await self.eval_db.create(make_sample())
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()
        sample_id = result.get_ok()

        rag_config_id = "rag-1"
        eval_config_id = "eval-1"

        result = await self.eval_db.add_system_answer(
            sample_id, make_answer(config_id=rag_config_id)
        )
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()
        answer_id = result.get_ok()

        res_none = await self.eval_db.was_answer_of_question_already_evaled_by_system(
            sample_id, config_eval_id=eval_config_id, config_rag=rag_config_id
        )
        if res_none.is_error():
            logger.error(res_none.get_error())
        assert res_none.is_ok()
        assert res_none.get_ok() is False

        r = await self.eval_db.add_llm_rating(
            answer_id,
            RatingLLM(
                rationale="well reasoned",
                config_id=eval_config_id,
                correctness=0.95,
                relevant_chunks=[1],
                completeness=[True],
                completeness_in_data=[True],
            ),
        )
        if r.is_error():
            logger.error(r.get_error())
        assert r.is_ok()

        res_found = await self.eval_db.was_answer_of_question_already_evaled_by_system(
            sample_id, config_eval_id=eval_config_id, config_rag=rag_config_id
        )
        if res_found.is_error():
            logger.error(res_found.get_error())
        assert res_found.is_ok()
        assert res_found.get_ok() is True

        # unknown sample id
        res_found = await self.eval_db.was_answer_of_question_already_evaled_by_system(
            "1b5bbea4-c778-4e6f-8c52-fa89d10be38c",
            config_eval_id=eval_config_id,
            config_rag=rag_config_id,
        )
        if res_found.is_error():
            logger.error(res_found.get_error())
        assert res_found.is_ok()
        assert res_found.get_ok() is False

    async def test_fetch_ratings_with_all_criteria_and_modes(self):
        DATASET = "ds-QUERY"
        SYS_CFG = "rag-SYSTEM"
        GRADER_CFG = "grader-LLM"
        OTHER_GRADER = "grader-OTHER"
        EVAL_USER = "eva-user"
        OTHER_USER = "bob"
        META = {"source": "journal-a"}

        sample = make_sample(dataset_id=DATASET)
        sample.metatdata = META
        result = await self.eval_db.create(sample)
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()
        sample_id = result.get_ok()

        result = await self.eval_db.add_system_answer(
            sample_id, make_answer(config_id=SYS_CFG)
        )
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()
        answer_id = result.get_ok()

        result = await self.eval_db.get_questions_that_where_not_validated_by_system(
            GRADER_CFG
        )
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()
        assert len(result.get_ok()) == 1
        assert result.get_ok()[0][0] == SYS_CFG
        assert result.get_ok()[0][1] == sample_id

        r = await self.eval_db.add_llm_rating(
            answer_id,
            RatingLLM(
                rationale="ok",
                config_id=GRADER_CFG,
                correctness=0.85,
                completeness=[],
                completeness_in_data=[],
            ),
        )
        if r.is_error():
            logger.error(r.get_error())
        assert r.is_ok()

        result = await self.eval_db.get_questions_that_where_not_validated_by_system(
            GRADER_CFG
        )
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()
        assert len(result.get_ok()) == 0

        r = await self.eval_db.add_llm_rating(
            answer_id,
            RatingLLM(
                rationale="other",
                config_id=OTHER_GRADER,
                correctness=0.6,
                completeness=[],
                completeness_in_data=[],
            ),
        )
        if r.is_error():
            logger.error(r.get_error())
        assert r.is_ok()

        r = await self.evaluator_db.create(make_evaluator(EVAL_USER))
        if r.is_error():
            logger.error(r.get_error())
        assert r.is_ok()

        r = await self.evaluator_db.create(make_evaluator(OTHER_USER))
        if r.is_error():
            logger.error(r.get_error())
        assert r.is_ok()

        r = await self.eval_db.add_user_rating(
            answer_id,
            RatingUser(
                rationale="good-human",
                creator=EVAL_USER,
                correctness=0.95,
                completeness=[],
                completeness_in_data=[],
            ),
        )
        if r.is_error():
            logger.error(r.get_error())
        assert r.is_ok()

        r = await self.eval_db.add_user_rating(
            answer_id,
            RatingUser(
                rationale="meh",
                creator=OTHER_USER,
                correctness=0.4,
                completeness=[],
                completeness_in_data=[],
            ),
        )
        if r.is_error():
            logger.error(r.get_error())
        assert r.is_ok()

        q_both = RatingQuery(
            what_to_fetch=WhatToFetch.both,
            dataset_id=DATASET,
            system_config=SYS_CFG,
        )
        r_both = await self.eval_db.fetch_ratings(q_both)
        if r_both.is_error():
            logger.error(r_both.get_error())
        assert r_both.is_ok()
        assert len(r_both.get_ok()) == 4

        q_user = RatingQuery(
            what_to_fetch=WhatToFetch.user,
            evaluator_user=EVAL_USER,
            dataset_id=DATASET,
            system_config=SYS_CFG,
        )
        r_user = await self.eval_db.fetch_ratings(q_user)
        if r_user.is_error():
            logger.error(r_user.get_error())
        assert r_user.is_ok()
        ratings_user = r_user.get_ok()
        assert len(ratings_user) == 1
        assert all(r.source_type == "user" for r in ratings_user)
        assert ratings_user[0].source == EVAL_USER

        q_llm = RatingQuery(
            what_to_fetch=WhatToFetch.llm,
            grading_config=GRADER_CFG,
            dataset_id=DATASET,
            system_config=SYS_CFG,
        )
        r_llm = await self.eval_db.fetch_ratings(q_llm)
        if r_llm.is_error():
            logger.error(r_llm.get_error())
        assert r_llm.is_ok()
        ratings_llm = r_llm.get_ok()
        assert len(ratings_llm) == 1
        assert all(r.source_type == "llm" for r in ratings_llm)
        assert ratings_llm[0].source == GRADER_CFG

        q_meta = RatingQuery(
            what_to_fetch=WhatToFetch.both,
            metadata=META,
            dataset_id=DATASET,
            system_config=SYS_CFG,
        )
        r_meta = await self.eval_db.fetch_ratings(q_meta)
        if r_meta.is_error():
            logger.error(r_meta.get_error())
        assert r_meta.is_ok()
        assert len(r_meta.get_ok()) == 4

        q_combo = RatingQuery(
            what_to_fetch=WhatToFetch.both,
            dataset_id=DATASET,
            system_config=SYS_CFG,
            grading_config=GRADER_CFG,
            evaluator_user=EVAL_USER,
            metadata=META,
        )
        r_combo = await self.eval_db.fetch_ratings(q_combo)
        if r_combo.is_error():
            logger.error(r_combo.get_error())
        assert r_combo.is_ok()
        assert len(r_combo.get_ok()) == 2

        q_none = RatingQuery(
            what_to_fetch=WhatToFetch.both,
            dataset_id="nope",
            grading_config="none",
        )
        r_none = await self.eval_db.fetch_ratings(q_none)
        if r_none.is_error():
            logger.error(r_none.get_error())
        assert r_none.is_ok()
        assert len(r_none.get_ok()) == 0

    async def test_returns_attribute_keys(self):
        META_KEYS = {"source": "journal-a", "lang": "en"}
        dataset_id = "ds-META-A"

        sample = make_sample(dataset_id=dataset_id)
        sample.metatdata = META_KEYS
        result = await self.eval_db.create(sample)
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()

        res = await self.eval_db.fetch_metadata_attributes(dataset_id)
        if res.is_error():
            logger.error(res.get_error())
        assert res.is_ok()
        keys = res.get_ok()
        assert set(keys) == {"source", "lang"}

    async def test_returns_empty_when_metadata_is_empty(self):
        dataset_id = "ds-META-EMPTY"
        sample = make_sample(dataset_id=dataset_id)
        sample.metatdata = {}
        result = await self.eval_db.create(sample)
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()

        res = await self.eval_db.fetch_metadata_attributes(dataset_id)
        if res.is_error():
            logger.error(res.get_error())
        assert res.is_ok()
        assert res.get_ok() == []

    async def test_returns_empty_when_dataset_not_found(self):
        res = await self.eval_db.fetch_metadata_attributes("does-not-exist")
        if res.is_error():
            logger.error(res.get_error())
        assert res.is_ok()
        assert res.get_ok() == []
