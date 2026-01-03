from uuid import UUID
from tortoise.contrib.postgres.indexes import GinIndex
from database.session import DatabaseBaseModel
from domain.database.validation.model import TestSample as TestSampleDomain
from domain.database.validation.model import RatingUser as RatingUserDomain
from domain.database.validation.model import RatingLLM as RatingLLMDomain
from domain.database.validation.model import RAGSystemAnswer as RAGSystemAnswerDomain
from domain.database.validation.model import (
    RAGSystemAnswerRatings as RAGSystemAnswerRatingsDomain,
)
from tortoise import fields
from tortoise.fields import Field
from tortoise.contrib.postgres.fields import ArrayField


class Evaluator(DatabaseBaseModel):
    username = fields.CharField(max_length=128, unique=True)


class RatingUser(DatabaseBaseModel):
    system_answer = fields.ForeignKeyField(  # type: ignore
        "models.RAGSystemAnswer", related_name="ratings_user"
    )  # type: ignore
    rationale = fields.TextField()
    creator = fields.CharField(max_length=128)
    correctness = fields.FloatField()
    relevant_chunks: Field[list[int]] = ArrayField(element_type="int")
    completeness: Field[list[bool]] = ArrayField(element_type="bool")
    completeness_in_data: Field[list[bool]] = ArrayField(element_type="bool")


class RatingLLM(DatabaseBaseModel):
    system_answer = fields.ForeignKeyField(  # type: ignore
        "models.RAGSystemAnswer", related_name="ratings_llm"
    )  # type: ignore
    rationale = fields.TextField()
    config_id = fields.CharField(max_length=128)
    correctness = fields.FloatField()
    relevant_chunks: Field[list[int]] = ArrayField(element_type="int")
    completeness: Field[list[bool]] = ArrayField(element_type="bool")
    completeness_in_data: Field[list[bool]] = ArrayField(element_type="bool")


class RAGSystemAnswer(DatabaseBaseModel):
    # basic information
    test_sample = fields.ForeignKeyField("models.TestSample", related_name="answers")  # type: ignore
    answer = fields.TextField()
    given_rag_context: Field[list[str]] = ArrayField(element_type="text")
    facts: Field[list[str]] = ArrayField(element_type="text")
    config_id = fields.CharField(max_length=128)
    #  metriken
    retrieval_latency_ms = fields.FloatField()
    generation_latency_ms = fields.FloatField()
    number_of_facts_in_context = fields.IntField()
    number_of_facts_in_answer = fields.IntField()
    ratings_user: fields.ReverseRelation["RatingUser"]
    ratings_llm: fields.ReverseRelation["RatingLLM"]


class TestSample(DatabaseBaseModel):
    dataset_id = fields.CharField(max_length=128)
    # paper referenz
    question_hash = fields.CharField(max_length=256, default="", unique=True)
    retrival_complexity = fields.FloatField()
    question = fields.TextField()
    expected_answer = fields.TextField()
    expected_facts: Field[list[str]] = ArrayField(element_type="text")
    expected_context = fields.TextField()
    question_type = fields.CharField(max_length=128)
    metatdata = fields.JSONField[dict[str, str]]()
    metadata_filter = fields.JSONField[dict[str, list[str]]]()

    class Meta:
        indexes = [GinIndex(fields=["metatdata"])]


def db_to_dto(db_obj: TestSample) -> TestSampleDomain:
    return TestSampleDomain(
        id=str(db_obj.id),
        dataset_id=db_obj.dataset_id,
        retrival_complexity=db_obj.retrival_complexity,
        question_hash=db_obj.question_hash,
        question=db_obj.question,
        expected_answer=db_obj.expected_answer,
        expected_facts=db_obj.expected_facts,
        expected_context=db_obj.expected_context,
        question_type=db_obj.question_type,
        metatdata=db_obj.metatdata or {},
        metatdata_filter=db_obj.metadata_filter,
    )


def dto_to_db(dto: TestSampleDomain) -> TestSample:
    test_sample = TestSample(
        dataset_id=dto.dataset_id,
        retrival_complexity=dto.retrival_complexity,
        question=dto.question,
        expected_answer=dto.expected_answer,
        question_hash=dto.question_hash,
        expected_facts=dto.expected_facts,
        expected_context=dto.expected_context,
        question_type=dto.question_type,
        metatdata=dto.metatdata or {},
        metadata_filter=dto.metatdata_filter or {},
    )

    try:
        test_sample.id = UUID(dto.id)
    except Exception as _:
        ...

    return test_sample


def db_to_dto_rating_user(db_obj: RatingUser) -> RatingUserDomain:
    return RatingUserDomain(
        rationale=db_obj.rationale,
        creator=db_obj.creator,
        correctness=db_obj.correctness,
        relevant_chunks=db_obj.relevant_chunks,
        completeness=db_obj.completeness or [],
        completeness_in_data=db_obj.completeness_in_data or [],
    )


def dto_to_db_rating_user(dto: RatingUserDomain) -> RatingUser:
    rating = RatingUser(
        rationale=dto.rationale,
        creator=dto.creator,
        correctness=dto.correctness,
        relevant_chunks=dto.relevant_chunks,
        completeness=dto.completeness or [],
        completeness_in_data=dto.completeness_in_data or [],
    )
    return rating


def db_to_dto_rating_llm(db_obj: RatingLLM) -> RatingLLMDomain:
    return RatingLLMDomain(
        rationale=db_obj.rationale,
        config_id=db_obj.config_id,
        correctness=db_obj.correctness,
        relevant_chunks=db_obj.relevant_chunks,
        completeness=db_obj.completeness or [],
        completeness_in_data=db_obj.completeness_in_data or [],
    )


def dto_to_db_rating_llm(dto: RatingLLMDomain) -> RatingLLM:
    rating = RatingLLM(
        rationale=dto.rationale,
        config_id=dto.config_id,
        correctness=dto.correctness,
        relevant_chunks=dto.relevant_chunks,
        completeness=dto.completeness or [],
        completeness_in_data=dto.completeness_in_data or [],
    )
    return rating


def db_to_dto_rag_system_answer(db_obj: RAGSystemAnswer) -> RAGSystemAnswerDomain:
    return RAGSystemAnswerDomain(
        id=str(db_obj.id),
        answer=db_obj.answer,
        given_rag_context=db_obj.given_rag_context,
        facts=db_obj.facts,
        config_id=db_obj.config_id,
        retrieval_latency_ms=db_obj.retrieval_latency_ms,
        generation_latency_ms=db_obj.generation_latency_ms,
        number_of_facts_in_context=db_obj.number_of_facts_in_context,
        number_of_facts_in_answer=db_obj.number_of_facts_in_answer,
        token_count_prompt=0,  # not present in DB model yet
        token_count_completion=0,  # not present in DB model yet
        answer_confidence=None,  # not present in DB model yet
    )


def db_to_dto_rag_system_answer_with_rating(
    db_obj: RAGSystemAnswer,
) -> RAGSystemAnswerRatingsDomain:
    return RAGSystemAnswerRatingsDomain(
        id=str(db_obj.id),
        answer=db_obj.answer,
        given_rag_context=db_obj.given_rag_context,
        config_id=db_obj.config_id,
        retrieval_latency_ms=db_obj.retrieval_latency_ms,
        generation_latency_ms=db_obj.generation_latency_ms,
        facts=db_obj.facts,
        number_of_facts_in_answer=db_obj.number_of_facts_in_answer,
        number_of_facts_in_context=db_obj.number_of_facts_in_context,
        token_count_prompt=0,  # not present in DB model yet
        token_count_completion=0,  # not present in DB model yet
        answer_confidence=None,  # not present in DB model yet
        llm_ratings=[],
        human_ratings=[],
    )


def dto_to_db_rag_system_answer(dto: RAGSystemAnswerDomain) -> RAGSystemAnswer:
    rag_answer = RAGSystemAnswer(
        answer=dto.answer,
        given_rag_context=dto.given_rag_context,
        config_id=dto.config_id,
        facts=dto.facts,
        retrieval_latency_ms=dto.retrieval_latency_ms,
        generation_latency_ms=dto.generation_latency_ms,
        number_of_facts_in_context=dto.number_of_facts_in_context,
        number_of_facts_in_answer=dto.number_of_facts_in_answer,
    )

    try:
        rag_answer.id = UUID(dto.id)
    except Exception:
        pass

    return rag_answer
