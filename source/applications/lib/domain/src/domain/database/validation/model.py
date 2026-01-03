from __future__ import annotations
from enum import Enum
from pydantic import BaseModel, Field
from typing import Literal, Optional, Dict, Any


class Evaluator(BaseModel):
    id: str
    username: str


class RatingUser(BaseModel):
    rationale: str
    creator: str
    correctness: float = Field(ge=0, le=1)
    relevant_chunks: list[int] = Field([])
    completeness: list[bool] = Field([])
    completeness_in_data: list[bool] = Field([])


class RatingLLM(BaseModel):
    rationale: str
    config_id: str
    correctness: float = Field(ge=0, le=1)
    relevant_chunks: list[int] = Field([])
    completeness: list[bool] = Field([])
    completeness_in_data: list[bool] = Field([])


class RatingGeneral(BaseModel):
    question_id: str
    rationale: str
    source: str
    source_type: Literal["user", "llm"]
    correctness: float = Field(ge=0, le=1)
    completeness: list[bool] = Field([])
    completeness_in_data: list[bool] = Field([])
    relevant_chunks: list[int] = Field([])
    number_of_chunks: int
    number_of_facts_in_context: int
    number_of_facts_in_answer: int


class WhatToFetch(Enum):
    both = "both"
    llm = "llm"
    user = "user"


class RatingQuery(BaseModel):
    dataset_id: Optional[str] = None
    system_config: Optional[str] = None
    grading_config: Optional[str] = None
    evaluator_user: Optional[str] = None
    what_to_fetch: WhatToFetch = WhatToFetch.both
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Partial JSON document that must be contained in TestSample.metadata",
    )


class RAGSystemAnswer(BaseModel):
    # basic information
    id: str
    answer: str
    given_rag_context: list[str]
    config_id: str
    #  metriken
    retrieval_latency_ms: float
    generation_latency_ms: float
    token_count_prompt: int
    token_count_completion: int
    number_of_facts_in_context: int
    number_of_facts_in_answer: int
    facts: list[str]
    answer_confidence: float | None = None


class RAGSystemAnswerRatings(BaseModel):
    # basic information
    id: str
    answer: str
    given_rag_context: list[str]
    facts: list[str]
    number_of_facts_in_context: int
    number_of_facts_in_answer: int
    config_id: str
    #  metriken
    retrieval_latency_ms: float
    generation_latency_ms: float
    token_count_prompt: int
    token_count_completion: int
    answer_confidence: float | None = None
    llm_ratings: list[RatingLLM]
    human_ratings: list[RatingUser]


class TestSample(BaseModel):
    id: str
    dataset_id: str
    # paper referenz
    retrival_complexity: float
    question_hash: str
    question: str
    expected_answer: str
    expected_facts: list[str]
    expected_context: str
    question_type: str
    # candidates: dict[str, RAGSystemAnswer]
    metatdata: dict[str, str] = {}
    metatdata_filter: dict[str, list[str]] = {}
