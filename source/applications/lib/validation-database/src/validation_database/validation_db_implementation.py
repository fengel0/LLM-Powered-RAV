import logging
from typing import TypeVar
from core.model import DublicateException
from core.result import Result
from domain.database.validation.interface import (
    EvaluationDatabase,
    EvaluatorDatabase,
)

from opentelemetry import trace

from database.session import BaseDatabase, NotFoundException
from pydantic import BaseModel
from tortoise.query_utils import Prefetch
from validation_database.model import (
    TestSample as TestSampleDB,
    db_to_dto,
    db_to_dto_rag_system_answer,
    db_to_dto_rag_system_answer_with_rating,
    db_to_dto_rating_llm,
    db_to_dto_rating_user,
    dto_to_db,
    dto_to_db_rag_system_answer,
    dto_to_db_rating_llm,
    dto_to_db_rating_user,
)
from validation_database.model import Evaluator as EvaluatorDB
from validation_database.model import RatingUser as RatingUserDB
from validation_database.model import RatingLLM as RatingLLMDB
from validation_database.model import RAGSystemAnswer as SystemAnswerDB
from domain.database.validation.model import (
    RatingQuery,
    WhatToFetch,
    TestSample,
    RatingLLM,
    RatingUser,
    RAGSystemAnswer,
    RAGSystemAnswerRatings,
    Evaluator,
    RatingGeneral,
)

logger = logging.getLogger(__name__)


class _InternPostgresDBTestSample(BaseDatabase[TestSampleDB]):
    def __init__(
        self,
    ):
        super().__init__(TestSampleDB)


class _InternPostgresDBRatingLLM(BaseDatabase[RatingLLMDB]):
    def __init__(
        self,
    ):
        super().__init__(RatingLLMDB)


class _InternPostgresDBRatingUser(BaseDatabase[RatingUserDB]):
    def __init__(
        self,
    ):
        super().__init__(RatingUserDB)


class _InternPostgresDBSystemAnswer(BaseDatabase[SystemAnswerDB]):
    def __init__(
        self,
    ):
        super().__init__(SystemAnswerDB)


class _InternPostgresDBEvaluator(BaseDatabase[EvaluatorDB]):
    def __init__(
        self,
    ):
        super().__init__(EvaluatorDB)


T = TypeVar("T", bound=BaseModel)


class PostgresDBEvaluatorDatabase(EvaluatorDatabase):
    _db_evaluator: _InternPostgresDBEvaluator
    tracer: trace.Tracer

    def __init__(self) -> None:
        super().__init__()
        self._db_evaluator = _InternPostgresDBEvaluator()
        self.tracer = trace.get_tracer("Evaluator-Database")

    def _convert_to_domain(self, obj: EvaluatorDB) -> Evaluator:
        return Evaluator(id=str(obj.id), username=obj.username)

    def _convert_to_db(self, obj: Evaluator) -> EvaluatorDB:
        try:
            return EvaluatorDB(id=str(obj.id), username=obj.username)
        except Exception as _:
            return EvaluatorDB(username=obj.username)

    async def create(self, obj: Evaluator) -> Result[str]:
        return await self._db_evaluator.create(self._convert_to_db(obj))

    async def update(self, obj: Evaluator) -> Result[None]:
        return await self._db_evaluator.update(obj=self._convert_to_db(obj))

    async def delete(self, id: str) -> Result[None]:
        return await self._db_evaluator.delete(id=id)

    async def get(self, id: str) -> Result[Evaluator | None]:
        result = await self._db_evaluator.get(id=id)
        if result.is_error():
            return result.propagate_exception()
        obj = result.get_ok()
        if obj:
            return Result.Ok(self._convert_to_domain(obj=obj))

        return Result.Ok(None)

    async def get_all(self) -> Result[list[Evaluator]]:
        result = await self._db_evaluator.get_all()
        if result.is_error():
            return result.propagate_exception()
        objs = result.get_ok()
        return Result.Ok([self._convert_to_domain(obj) for obj in objs])

    async def get_evalutor_by_name(self, username: str) -> Result[Evaluator | None]:
        with self.tracer.start_as_current_span("get-evaluator-by-name"):
            query = {"username": username}
            result = await self._db_evaluator.run_query(query)
            if result.is_error():
                return result.propagate_exception()
            objs = result.get_ok()
            if len(objs) == 0:
                return Result.Ok(None)
            obj = objs[0]
            return Result.Ok(self._convert_to_domain(obj=obj))


class PostgresDBEvaluation(EvaluationDatabase):
    _db_samples: _InternPostgresDBTestSample
    _db_rating_user: _InternPostgresDBRatingUser
    _db_rating_llm: _InternPostgresDBRatingLLM
    _db_system_rag_answer: _InternPostgresDBSystemAnswer
    _db_evaluator: PostgresDBEvaluatorDatabase
    tracer: trace.Tracer

    def __init__(self) -> None:
        super().__init__()
        self._db_samples = _InternPostgresDBTestSample()
        self._db_rating_user = _InternPostgresDBRatingUser()
        self._db_rating_llm = _InternPostgresDBRatingLLM()
        self._db_system_rag_answer = _InternPostgresDBSystemAnswer()
        self._db_evaluator = PostgresDBEvaluatorDatabase()
        self.tracer = trace.get_tracer("PostgresEvaluation")

    async def create(self, obj: TestSample) -> Result[str]:
        result = await self.get_sample_by_hash(obj.question_hash)
        if result.is_error():
            return result.propagate_exception()
        optional_sample = result.get_ok()
        if optional_sample:
            return Result.Err(DublicateException("Question mit hash already exists"))

        return await self._db_samples.create(dto_to_db(obj))

    async def update(self, obj: TestSample) -> Result[None]:
        return await self._db_samples.update(dto_to_db(obj))

    async def delete(self, id: str) -> Result[None]:
        return await self._db_samples.delete(id=id)

    async def get(self, id: str) -> Result[TestSample | None]:
        result = await self._db_samples.get(id=id)
        if result.is_error():
            return result.propagate_exception()
        obj = result.get_ok()
        if obj:
            return Result.Ok(db_to_dto(obj))

        return Result.Ok(None)

    async def get_all(self) -> Result[list[TestSample]]:
        result = await self._db_samples.get_all()
        if result.is_error():
            return result.propagate_exception()
        objs = result.get_ok()
        return Result.Ok([db_to_dto(obj) for obj in objs])

    async def get_sample_by_hash(self, hash: str) -> Result[TestSample | None]:
        result = await self._db_samples.run_query_first({"question_hash": hash})
        if result.is_error():
            return result.propagate_exception()
        obj = result.get_ok()
        if obj:
            return Result.Ok(db_to_dto(db_obj=obj))

        return Result.Ok(None)

    # --- End CRUD ---

    async def add_llm_rating(self, answer_id: str, rating: RatingLLM) -> Result[str]:
        with self.tracer.start_as_current_span("add-llm-rating"):
            system_answer_result = await self._db_system_rag_answer.get(id=answer_id)
            if system_answer_result.is_error():
                return system_answer_result.propagate_exception()
            system_answer_optional = system_answer_result.get_ok()
            if system_answer_optional is None:
                return Result.Err(
                    NotFoundException(f"System Answer {answer_id} not found")
                )
            system_answer = system_answer_optional
            db_rating = dto_to_db_rating_llm(rating)
            db_rating.system_answer = system_answer

            return await self._db_rating_llm.create_update(db_rating)

    async def add_user_rating(self, answer_id: str, rating: RatingUser) -> Result[str]:
        with self.tracer.start_as_current_span("add-user-rating"):
            system_answer_result = await self._db_system_rag_answer.get(id=answer_id)
            if system_answer_result.is_error():
                return system_answer_result.propagate_exception()
            system_answer_optional = system_answer_result.get_ok()
            if system_answer_optional is None:
                return Result.Err(
                    NotFoundException(f"System Answer {answer_id} not found")
                )
            system_answer = system_answer_optional
            db_rating = dto_to_db_rating_user(rating)
            db_rating.system_answer = system_answer

            return await self._db_rating_user.create_update(db_rating)

    async def add_system_answer(
        self, sample_id: str, system_answer: RAGSystemAnswer
    ) -> Result[str]:
        with self.tracer.start_as_current_span("add-system-answer"):
            found_sample_result = await self._db_samples.get(id=sample_id)
            if found_sample_result.is_error():
                return found_sample_result.propagate_exception()
            found_sample_optional = found_sample_result.get_ok()
            if found_sample_optional is None:
                return Result.Err(
                    NotFoundException(f"Sample Test not found with id {sample_id}")
                )

            assert found_sample_optional
            found_sample = found_sample_optional
            system_answer_db = dto_to_db_rag_system_answer(system_answer)
            system_answer_db.test_sample = found_sample
            return await self._db_system_rag_answer.create(system_answer_db)

    ## -- Adding Answers ---
    async def fetch_metadata_attributes(
        self,
        dataset_id: str,
    ) -> Result[list[str]]:
        with self.tracer.start_as_current_span("fetch-dataset-question"):
            query = {
                "dataset_id": dataset_id,
            }
            result = await self._db_samples.run_query_first(query=query)
            if result.is_error():
                return result.propagate_exception()
            objs = result.get_ok()

            keys = []
            if objs:
                keys = [key for key in objs.metatdata.keys()]

            return Result.Ok(keys)

    async def fetch_dataset_question(
        self,
        dataset_id: str,
        from_number: int,
        to_number: int,
        number_of_facts: int = 0,
    ) -> Result[list[TestSample]]:
        with self.tracer.start_as_current_span("fetch-dataset-question"):
            query = {
                "dataset_id": dataset_id,
            }
            skip = from_number
            limit = to_number - from_number
            result = await self._db_samples.run_query(
                query=query, skip=skip, limit=limit
            )
            if result.is_error():
                return result.propagate_exception()
            objs = result.get_ok()

            return Result.Ok(
                [
                    db_to_dto(obj)
                    for obj in objs
                    if len(obj.expected_facts) >= number_of_facts
                ]
            )

    async def fetch_dataset_question_number(self, dataset_id: str) -> Result[int]:
        with self.tracer.start_as_current_span("fetch-dataset-question-number"):
            query = {"dataset_id": dataset_id}
            result = await self._db_samples.run_query(
                query=query,
            )
            if result.is_error():
                return result.propagate_exception()
            objs = result.get_ok()

            return Result.Ok(len(objs))

    ## -- UI Query

    async def fetch_answers_and_ratings(
        self, question_id: str
    ) -> Result[list[RAGSystemAnswerRatings]]:
        query = {"test_sample_id": question_id}
        try:
            answers: list[RAGSystemAnswerRatings] = []
            system_answer_dbs = await SystemAnswerDB.filter(**query).prefetch_related(
                "ratings_user", "ratings_llm"
            )
            for system_answer_db in system_answer_dbs:
                system_answer = db_to_dto_rag_system_answer_with_rating(
                    system_answer_db
                )
                system_answer.human_ratings = [
                    db_to_dto_rating_user(rating)
                    for rating in system_answer_db.ratings_user
                ]
                system_answer.llm_ratings = [
                    db_to_dto_rating_llm(rating)
                    for rating in system_answer_db.ratings_llm
                ]
                answers.append(system_answer)
            return Result.Ok(answers)
        except Exception as e:
            logger.error(e, exc_info=True)
            return Result.Err(e)

    async def fetch_datasets(self) -> Result[list[str]]:
        with self.tracer.start_as_current_span("fetch-datasets"):
            result = await self._db_samples.get_all()
            if result.is_error():
                return result.propagate_exception()
            objs = result.get_ok()

            return Result.Ok(list(set([obj.dataset_id for obj in objs])))

    async def fetch_ratings(self, criteria: RatingQuery) -> Result[list[RatingGeneral]]:
        try:
            # -----------------------------------------------------------------
            # Base queryset (answers)
            # -----------------------------------------------------------------
            qs = SystemAnswerDB.all().select_related("test_sample")

            if criteria.dataset_id:
                qs = qs.filter(test_sample__dataset_id=criteria.dataset_id)
            if criteria.system_config:
                qs = qs.filter(config_id=criteria.system_config)
            if criteria.metadata:
                # NOTE: fixed typo: test_sample__metadata__contains (was metatdata)
                qs = qs.filter(test_sample__metatdata__contains=criteria.metadata)

            # -----------------------------------------------------------------
            # Build filtered prefetches
            # -----------------------------------------------------------------
            user_qs = RatingUserDB.all()
            if getattr(criteria, "evaluator_user", None):
                user_qs = user_qs.filter(creator=criteria.evaluator_user)

            llm_qs = RatingLLMDB.all()
            if getattr(criteria, "grading_config", None):
                llm_qs = llm_qs.filter(config_id=criteria.grading_config)

            match criteria.what_to_fetch:
                case WhatToFetch.user:
                    qs = qs.prefetch_related(Prefetch("ratings_user", queryset=user_qs))
                case WhatToFetch.llm:
                    qs = qs.prefetch_related(Prefetch("ratings_llm", queryset=llm_qs))
                case WhatToFetch.both:
                    qs = qs.prefetch_related(
                        Prefetch("ratings_user", queryset=user_qs),
                        Prefetch("ratings_llm", queryset=llm_qs),
                    )
                case _:
                    return Result.Err(Exception("invalid enum value for what_to_fetch"))

            answers = await qs  # materialize

            # -----------------------------------------------------------------
            # Map to RatingGeneral
            # -----------------------------------------------------------------
            out: list[RatingGeneral] = []

            want_user = criteria.what_to_fetch in (WhatToFetch.user, WhatToFetch.both)
            want_llm = criteria.what_to_fetch in (WhatToFetch.llm, WhatToFetch.both)

            for ans in answers:
                question_id = str(ans.test_sample_id)
                if want_user:
                    # thanks to prefetch, this is an in-memory list
                    for r in getattr(ans, "ratings_user", []):
                        out.append(
                            RatingGeneral(
                                question_id=question_id,
                                rationale=r.rationale,
                                source=r.creator,
                                source_type="user",
                                correctness=r.correctness,
                                completeness=r.completeness or [],
                                relevant_chunks=r.relevant_chunks or [],
                                completeness_in_data=r.completeness_in_data or [],
                                number_of_facts_in_context=ans.number_of_facts_in_context,
                                number_of_facts_in_answer=ans.number_of_facts_in_answer,
                                number_of_chunks=len(ans.given_rag_context),
                            )
                        )
                if want_llm:
                    for r in getattr(ans, "ratings_llm", []):
                        out.append(
                            RatingGeneral(
                                question_id=question_id,
                                rationale=r.rationale,
                                source=r.config_id,
                                source_type="llm",
                                correctness=r.correctness,
                                completeness=r.completeness or [],
                                completeness_in_data=r.completeness_in_data or [],
                                relevant_chunks=r.relevant_chunks or [],
                                number_of_facts_in_context=ans.number_of_facts_in_context,
                                number_of_facts_in_answer=ans.number_of_facts_in_answer,
                                number_of_chunks=len(ans.given_rag_context),
                            )
                        )

            return Result.Ok(out)

        except Exception as e:
            logger.error(e, exc_info=True)
            return Result.Err(e)

    async def fetch_ratings_of_config(self, config_id: str) -> Result[list[RatingLLM]]:
        """
        Return *all* LLM-generated ratings that belong to the given RAG system
        configuration.
        """
        with self.tracer.start_as_current_span("fetch-ratings-of-config"):
            query = {"config_id": config_id}
            result = await self._db_rating_llm.run_query(query)
            if result.is_error():
                return result.propagate_exception()

            objs = result.get_ok()
            return Result.Ok([db_to_dto_rating_llm(o) for o in objs])

    async def fetch_ratings_of_user(self, username: str) -> Result[list[RatingUser]]:
        """
        Return *all* human ratings authored by the user with ``username``.
        """
        with self.tracer.start_as_current_span("fetch-ratings-of-user"):
            query = {"creator": username}
            result = await self._db_rating_user.run_query(query)
            if result.is_error():
                return result.propagate_exception()

            objs = result.get_ok()
            return Result.Ok([db_to_dto_rating_user(o) for o in objs])

    async def fetch_ratings_from_dataset(
        self, dataset_name: str
    ) -> Result[list[RatingLLM | RatingUser]]:
        """
        Collect every rating (human **and** LLM) that originates from any test
        sample in the specified dataset.
        """
        with self.tracer.start_as_current_span("fetch-ratings-from-dataset"):
            try:
                ratings: list[RatingLLM | RatingUser] = []
                query = {"test_sample__dataset_id": dataset_name}
                answers_result = await self._db_system_rag_answer.run_query(
                    query=query, relation=["ratings_user", "ratings_llm"]
                )
                if answers_result.is_error():
                    return answers_result.propagate_exception()
                answers = answers_result.get_ok()

                for ans in answers:
                    ratings.extend(db_to_dto_rating_llm(r) for r in ans.ratings_llm)
                    ratings.extend(db_to_dto_rating_user(r) for r in ans.ratings_user)

                return Result.Ok(ratings)

            except Exception as e:
                logger.error(e, exc_info=True)
                return Result.Err(e)

    async def fetch_ratings_from_dataset_for_a_certain_sytem(
        self, dataset_name: str, config_id: str
    ) -> Result[list[RatingLLM | RatingUser]]:
        """
        Collect every rating (human **and** LLM) that originates from any test
        sample in the specified dataset.
        """
        with self.tracer.start_as_current_span(
            "fetch-ratings-from_dataset-for-a-certain-sytem"
        ):
            try:
                ratings: list[RatingLLM | RatingUser] = []
                query = {
                    "test_sample__dataset_id": dataset_name,
                    "config_id": config_id,
                }
                answers_result = await self._db_system_rag_answer.run_query(
                    query=query, relation=["ratings_user", "ratings_llm"]
                )
                if answers_result.is_error():
                    return answers_result.propagate_exception()
                answers = answers_result.get_ok()

                for ans in answers:
                    ratings.extend(db_to_dto_rating_llm(r) for r in ans.ratings_llm)
                    ratings.extend(db_to_dto_rating_user(r) for r in ans.ratings_user)

                return Result.Ok(ratings)

            except Exception as e:
                logger.error(e, exc_info=True)
                return Result.Err(e)

    async def fetch_ratings_from_dataset_from_a_certain_eval_system(
        self, dataset_name: str, config_id: str
    ) -> Result[list[RatingLLM]]:
        with self.tracer.start_as_current_span(
            "fetch_ratings-from-dataset-from-a-certain-eval-system"
        ):
            try:
                query = {
                    "system_answer__test_sample__dataset_id": dataset_name,
                    "config_id": config_id,
                }
                ratings_db_result = await self._db_rating_llm.run_query(query=query)
                if ratings_db_result.is_error():
                    ratings_db_result.propagate_exception()
                ratings_db = ratings_db_result.get_ok()

                ratings: list[RatingLLM] = [db_to_dto_rating_llm(r) for r in ratings_db]
                return Result.Ok(ratings)

            except Exception as e:
                logger.error(e, exc_info=True)
                return Result.Err(e)

    async def fetch_ratings_from_dataset_from_a_certain_system_by_a_certain_system(
        self, dataset_name: str, system_config_id: str, grading_config: str
    ) -> Result[list[RatingLLM]]:
        with self.tracer.start_as_current_span(
            "fetch-ratings-from-dataset-from-a-certain-system-by-a-certain-system"
        ):
            try:
                query = {
                    "system_answer__config_id": system_config_id,
                    "system_answer__test_sample__dataset_id": dataset_name,
                    "config_id": grading_config,
                }

                ratings_db_result = await self._db_rating_llm.run_query(query=query)
                if ratings_db_result.is_error():
                    ratings_db_result.propagate_exception()
                ratings_db = ratings_db_result.get_ok()

                ratings: list[RatingLLM] = [db_to_dto_rating_llm(r) for r in ratings_db]
                return Result.Ok(ratings)

            except Exception as e:
                logger.error(e, exc_info=True)
                return Result.Err(e)

    ## --- Helper function

    async def was_answer_of_question_already_evaled_by_system(
        self, sample_id: str, config_eval_id: str, config_rag: str
    ) -> Result[bool]:
        with self.tracer.start_as_current_span(
            "was-answer-of-question-already-evaled-by-system"
        ):
            query: dict[str, str] = {
                "system_answer__config_id": config_rag,
                "config_id": config_eval_id,
                "system_answer__test_sample__id": sample_id,
            }
            result = await self._db_rating_llm.run_query_first(query)
            if result.is_error():
                return result.propagate_exception()

            obj = result.get_ok()
            return Result.Ok(bool(obj))

    async def was_question_already_answered_by_config(
        self, sample_id: str, config_id: str
    ) -> Result[RAGSystemAnswer | None]:
        with self.tracer.start_as_current_span(
            "was-question-already-answered-by-config"
        ):
            query = {"test_sample_id": sample_id, "config_id": config_id}
            answer_result = await self._db_system_rag_answer.run_query_first(query)
            if answer_result.is_error():
                return answer_result.propagate_exception()
            optional_answer = answer_result.get_ok()
            if optional_answer:
                return Result.Ok(db_to_dto_rag_system_answer(optional_answer))
            return Result.Ok(None)

    async def get_questions_that_where_not_validated_by_system(
        self, eval_config_id: str
    ) -> Result[list[tuple[str, str]]]:
        with self.tracer.start_as_current_span(
            "was-question-already-answered-by-config"
        ):
            try:
                bad_ids = await RatingLLMDB.filter(
                    config_id=eval_config_id
                ).values_list("system_answer_id", flat=True)
                answers = await SystemAnswerDB.exclude(id__in=bad_ids)
                return Result.Ok(
                    [
                        (answer.config_id, str(answer.test_sample_id))  # type: ignore
                        for answer in answers
                    ]  # type: ignore
                )
            except Exception as e:
                logger.error(e, exc_info=True)
                return Result.Err(e)

    async def add_fact_counts_to_system_id(
        self,
        answer_id: str,
        facts: list[str],
        number_of_facts_in_anwer: int,
        number_of_facts_in_context: int,
    ) -> Result[None]:
        with self.tracer.start_as_current_span("update-system-answer"):
            found_rag_system_answer = await self._db_system_rag_answer.get(id=answer_id)
            if found_rag_system_answer.is_error():
                return found_rag_system_answer.propagate_exception()
            found_answer_optional = found_rag_system_answer.get_ok()
            if found_answer_optional is None:
                return Result.Err(
                    NotFoundException(f"SystemAnswer not found with id {answer_id}")
                )

            assert found_answer_optional
            found_answer = found_answer_optional
            found_answer.facts = facts
            found_answer.number_of_facts_in_answer = number_of_facts_in_anwer
            found_answer.number_of_facts_in_context = number_of_facts_in_context
            return await self._db_system_rag_answer.update(found_answer)

    async def get_anwers_by_config(
        self, config_id: str, dataset_option: None | str = None
    ) -> Result[list[RAGSystemAnswer]]:
        with self.tracer.start_as_current_span("get-anwers-by-config-in-dataset"):
            query = {"config_id": config_id}
            if dataset_option:
                query["test_sample__dataset_id"] = dataset_option
            answer_result = await self._db_system_rag_answer.run_query(query)
            if answer_result.is_error():
                return answer_result.propagate_exception()
            answers = answer_result.get_ok()
            return Result.Ok(
                [db_to_dto_rag_system_answer(answer) for answer in answers]
            )
