from typing import TypeVar

from core.result import Result
from pydantic import BaseModel
from domain.database import BaseDatabase
from domain.database.validation.model import (
    Evaluator,
    RAGSystemAnswer,
    RAGSystemAnswerRatings,
    RatingGeneral,
    RatingQuery,
    RatingUser,
    RatingLLM,
    TestSample,
)


class EvaluatorDatabase(BaseDatabase[Evaluator]):

    """
    Asynchronous read‑only repository that provides access to :class:`Evaluator`
    records (i.e. users or services that can score answers).
    """

    async def get_evalutor_by_name(self, username: str) -> Result[Evaluator | None]: ...


T = TypeVar("T", bound=BaseModel)


class EvaluationDatabase(BaseDatabase[TestSample]):

    """
    Asynchronous repository that stores and retrieves everything needed to
    evaluate a Retrieval‑Augmented Generation (RAG) system:

    • Test samples (questions, expected answers, metadata)
    • System‑generated answers
    • Ratings from LLMs and human users
    • Fact‑count statistics for answers
    • Various query helpers (by dataset, config, user, …)

    The interface purposefully stays *declarative* – it tells the caller *what*
    operations are available and the shape of the results, while leaving the
    concrete storage mechanism (SQL, document DB, in‑memory cache, etc.) to the
    implementation.

    All methods are **asynchronous** and return a ``Result`` object that wraps
    either the successful payload or the exception that occurred.
    """


    # insert Operation for Ratings and System Answers

    async def add_llm_rating(
        self, answer_id: str, rating: RatingLLM
    ) -> Result[str]: ...
    async def add_user_rating(
            self, answer_id: str, rating: RatingUser
    ) -> Result[str]: ...

    async def add_system_answer(
            self, sample_id: str, system_answer: RAGSystemAnswer
    ) -> Result[str]: ...


    # relevant for system evaluation
    async def add_fact_counts_to_system_id(
            self,
            answer_id: str,
            facts: list[str],
            number_of_facts_in_anwer: int,
            number_of_facts_in_context: int,
    ) -> Result[None]: ...

    # Fast Check helper

    async def get_sample_by_hash(self, hash: str) -> Result[TestSample | None]: ...

    async def was_question_already_answered_by_config(
        self, sample_id: str, config_id: str
    ) -> Result[RAGSystemAnswer | None]: ...

    async def was_answer_of_question_already_evaled_by_system(
        self, sample_id: str, config_eval_id: str, config_rag: str
    ) -> Result[bool]: ...

    # Datafetching

    async def fetch_dataset_question(
        self,
        dataset_id: str,
        from_number: int,
        to_number: int,
        number_of_facts: int,
    ) -> Result[list[TestSample]]: ...

    async def fetch_answers_and_ratings(
        self, question_id: str
    ) -> Result[list[RAGSystemAnswerRatings]]: ...


    async def fetch_ratings(
        self, criteria: RatingQuery
    ) -> Result[list[RatingGeneral]]: ...

    async def fetch_metadata_attributes(
        self,
        dataset_id: str,
    ) -> Result[list[str]]: ...

    async def fetch_dataset_question_number(self, dataset_id: str) -> Result[int]: ...

    async def fetch_datasets(self) -> Result[list[str]]: ...

    async def fetch_ratings_of_config(
        self, config_id: str
    ) -> Result[list[RatingLLM]]: ...

    async def fetch_ratings_of_user(
        self, username: str
    ) -> Result[list[RatingUser]]: ...

    async def fetch_ratings_from_dataset(
        self, dataset_name: str
    ) -> Result[list[RatingLLM | RatingUser]]: ...

    async def fetch_ratings_from_dataset_for_a_certain_sytem(
        self, dataset_name: str, config_id: str
    ) -> Result[list[RatingLLM | RatingUser]]: ...

    async def fetch_ratings_from_dataset_from_a_certain_eval_system(
        self, dataset_name: str, config_id: str
    ) -> Result[list[RatingLLM]]: ...

    async def fetch_ratings_from_dataset_from_a_certain_system_by_a_certain_system(
        self, dataset_name: str, system_config_id: str, grading_config: str
    ) -> Result[list[RatingLLM]]: ...


    async def get_anwers_by_config(
        self, config_id: str, dataset_option: None | str = None
    ) -> Result[list[RAGSystemAnswer]]: ...
