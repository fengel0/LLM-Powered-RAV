from core.result import Result
from core.hash import compute_mdhash_id
import logging
from core.singelton import BaseSingleton
from domain.database.validation.interface import EvaluatorDatabase, EvaluationDatabase
from domain.database.validation.model import (
    Evaluator,
    RAGSystemAnswer,
    RatingQuery,
    RatingUser,
    RatingLLM,
    RatingGeneral,
    TestSample,
    RAGSystemAnswerRatings,
)
from pydantic import BaseModel
from opentelemetry import trace

logger = logging.getLogger(__name__)


class EvaluationServiceConfig(BaseModel):
    admin_token: str


class EvaluationServiceUsecases(BaseSingleton):

    """
    Evaluation Service usecase
    allows to run crud operations on question, answers and ratings
    """

    _evaluator_database: EvaluatorDatabase
    _evaluation_database: EvaluationDatabase
    _config: EvaluationServiceConfig
    tracer: trace.Tracer

    def _init_once(
        self,
        evaluator_database: EvaluatorDatabase,
        evaluation_database: EvaluationDatabase,
        config: EvaluationServiceConfig,
    ):
        logger.info("created TextAnalysUsecase Usecase")

        self._evaluator_database = evaluator_database
        self._evaluation_database = evaluation_database
        self._config = config
        self.tracer = trace.get_tracer("EvaluationServiceUsecase")

    async def add_question(self, question: TestSample, admin_token: str) -> Result[str]:
        with self.tracer.start_as_current_span("add-question"):
            if admin_token != self._config.admin_token:
                return Result.Err(PermissionError("Invalid admin token"))
            question.question_hash = compute_mdhash_id(question.question)
            result = await self._evaluation_database.get_sample_by_hash(
                question.question_hash
            )

            if result.is_error():
                return result.propagate_exception()
            question_db = result.get_ok()
            if question_db:
                question.id = question_db.id
                logger.error(question.model_dump())
                result = await self._evaluation_database.update(obj=question)
                if result.is_error():
                    logger.error(result.get_error())
                    return result.propagate_exception()
                return Result.Ok(question_db.id)

            return await self._evaluation_database.create(obj=question)

    async def get_question_by_hash(self, hash: str) -> Result[TestSample | None]:
        with self.tracer.start_as_current_span("get-question-by-hash"):
            return await self._evaluation_database.get_sample_by_hash(hash)

    async def update_question(
        self, question: TestSample, admin_token: str
    ) -> Result[None]:
        with self.tracer.start_as_current_span("update-question"):
            if admin_token != self._config.admin_token:
                return Result.Err(PermissionError("Invalid admin token"))
            return await self._evaluation_database.update(obj=question)

    async def add_user(self, username: str, admin_token: str) -> Result[str]:
        with self.tracer.start_as_current_span("add-user"):
            if admin_token != self._config.admin_token:
                return Result.Err(PermissionError("Invalid admin token"))
            user_result = await self._evaluator_database.get_evalutor_by_name(
                username=username
            )
            if user_result.is_error():
                return user_result.propagate_exception()

            user_optional = user_result.get_ok()
            if user_optional:
                return Result.Err(ValueError(f"username is taken {username}"))

            return await self._evaluator_database.create(
                obj=Evaluator(id="", username=username)
            )

    async def get_users(self, admin_token: str) -> Result[list[Evaluator]]:
        with self.tracer.start_as_current_span("get-users"):
            if admin_token != self._config.admin_token:
                return Result.Err(PermissionError("Invalid admin token"))
            return await self._evaluator_database.get_all()

    async def add_user_evaluation(
        self, answer_id: str, rating: RatingUser
    ) -> Result[str]:
        with self.tracer.start_as_current_span("add-user-evaluation"):
            user_result = await self._evaluator_database.get_evalutor_by_name(
                username=rating.creator
            )
            if user_result.is_error():
                return user_result.propagate_exception()
            return await self._evaluation_database.add_user_rating(
                answer_id=answer_id, rating=rating
            )

    async def add_llm_evaluation(
        self, answer_id: str, rating: RatingLLM, admin_token: str
    ) -> Result[str]:
        with self.tracer.start_as_current_span("add-llm-evaluation"):
            if admin_token != self._config.admin_token:
                return Result.Err(PermissionError("Invalid admin token"))
            return await self._evaluation_database.add_llm_rating(
                answer_id=answer_id, rating=rating
            )

    async def add_system_answer(
        self, sample_id: str, system_answer: RAGSystemAnswer, admin_token: str
    ) -> Result[str]:
        with self.tracer.start_as_current_span("add-llm-answer"):
            if admin_token != self._config.admin_token:
                return Result.Err(PermissionError("Invalid admin token"))
            return await self._evaluation_database.add_system_answer(
                sample_id=sample_id, system_answer=system_answer
            )

    async def fetch_dataset_question(
        self,
        dataset_id: str,
        from_number: int,
        to_number: int,
        number_of_facts: int = 0,
    ) -> Result[list[TestSample]]:
        with self.tracer.start_as_current_span("fetch-dataset-question"):
            return await self._evaluation_database.fetch_dataset_question(
                dataset_id=dataset_id,
                from_number=from_number,
                to_number=to_number,
                number_of_facts=number_of_facts,
            )

    async def fetch_dataset_question_number(self, dataset_id: str) -> Result[int]:
        with self.tracer.start_as_current_span("fetch-dataset-question-number"):
            return await self._evaluation_database.fetch_dataset_question_number(
                dataset_id=dataset_id
            )

    async def fetch_ratings_of_config(self, config_id: str) -> Result[list[RatingLLM]]:
        with self.tracer.start_as_current_span("fetch-ratings-of-config"):
            return await self._evaluation_database.fetch_ratings_of_config(
                config_id=config_id
            )

    async def fetch_ratings_of_user(self, username: str) -> Result[list[RatingUser]]:
        with self.tracer.start_as_current_span("fetch-ratings-of-user"):
            return await self._evaluation_database.fetch_ratings_of_user(
                username=username
            )

    async def fetch_ratings_from_dataset(
        self, dataset_name: str
    ) -> Result[list[RatingLLM | RatingUser]]:
        with self.tracer.start_as_current_span("fetch-ratings-of-dataset"):
            return await self._evaluation_database.fetch_ratings_from_dataset(
                dataset_name=dataset_name
            )

    async def fetch_question(self, sample_id: str) -> Result[TestSample | None]:
        with self.tracer.start_as_current_span("fetch-question"):
            return await self._evaluation_database.get(sample_id)

    async def fetch_answers_with_rating(
        self, sample_id: str
    ) -> Result[list[RAGSystemAnswerRatings]]:
        with self.tracer.start_as_current_span("fetch-answers-ratings"):
            return await self._evaluation_database.fetch_answers_and_ratings(sample_id)

    async def fetch_datasets(self) -> Result[list[str]]:
        with self.tracer.start_as_current_span("fetch-datasets"):
            return await self._evaluation_database.fetch_datasets()

    async def fetch_ratings_from_dataset_for_a_certain_sytem(
        self, dataset_name: str, config_id: str
    ) -> Result[list[RatingLLM | RatingUser]]:
        with self.tracer.start_as_current_span(
            "fetch-ratings-from-dataset-for-a-certain-sytem"
        ):
            return await self._evaluation_database.fetch_ratings_from_dataset_for_a_certain_sytem(
                dataset_name=dataset_name, config_id=config_id
            )

    async def fetch_metadata_attributes(
        self,
        dataset_id: str,
    ) -> Result[list[str]]:
        with self.tracer.start_as_current_span("fetch_metadata_attributes"):
            return await self._evaluation_database.fetch_metadata_attributes(
                dataset_id=dataset_id
            )

    async def fetch_ratings(self, criteria: RatingQuery) -> Result[list[RatingGeneral]]:
        with self.tracer.start_as_current_span("fetch_metadata_attributes"):
            return await self._evaluation_database.fetch_ratings(criteria=criteria)

    async def fetch_ratings_from_dataset_from_a_certain_eval_system(
        self, dataset_name: str, config_id: str
    ) -> Result[list[RatingLLM]]:
        with self.tracer.start_as_current_span(
            "fetch-ratings-from-dataset-for-a-certain-eval-sytem"
        ):
            return await self._evaluation_database.fetch_ratings_from_dataset_from_a_certain_eval_system(
                dataset_name=dataset_name, config_id=config_id
            )

    async def fetch_ratings_from_dataset_from_a_certain_system_by_a_certain_system(
        self, dataset_name: str, system_config_id: str, grading_config: str
    ) -> Result[list[RatingLLM]]:
        with self.tracer.start_as_current_span(
            "fetch-ratings-from-dataset-from-a-certain-system-by-a-certain-system"
        ):
            return await self._evaluation_database.fetch_ratings_from_dataset_from_a_certain_system_by_a_certain_system(
                dataset_name=dataset_name,
                system_config_id=system_config_id,
                grading_config=grading_config,
            )

    async def get_questions_that_where_not_validated_by_system(
        self, eval_config: str
    ) -> Result[list[tuple[str, str]]]:
        with self.tracer.start_as_current_span(
            "get_questions_that_where_not_validated_by_system"
        ):
            return await self._evaluation_database.get_questions_that_where_not_validated_by_system(
                eval_config
            )

    async def get_anwers_by_config(
        self, config_id: str, dataset_option: None | str = None
    ) -> Result[list[RAGSystemAnswer]]:
        with self.tracer.start_as_current_span("get_anwers_by_config"):
            return await self._evaluation_database.get_anwers_by_config(
                config_id=config_id, dataset_option=dataset_option
            )
