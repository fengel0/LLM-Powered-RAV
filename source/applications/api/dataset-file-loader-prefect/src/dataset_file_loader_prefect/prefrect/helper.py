from typing import Any
from domain.database.validation.model import TestSample

from evaluation_service.usecase.evaluation import EvaluationServiceUsecases


async def upload_question(
    dataset_name: str,
    question_id: str,
    question: str,
    expected_answer: str,
    expected_context: str,
    expected_facts: list[str] = [],
    metadata: dict[str, Any] = {},
):
    result = await EvaluationServiceUsecases.Instance().add_question(
        admin_token="",
        question=TestSample(
            id="",
            question_id=question_id,
            dataset_id=dataset_name,
            retrival_complexity=0.0,
            expected_facts=expected_facts,
            question=question,
            expected_answer=expected_answer,
            expected_context=expected_context,
            question_type="unknown",  # Literal["factoid", "list", "numeric", "table_lookup", "aggregation"],
            candidates={},
            metatdata=metadata,
        ),
    )
    if result.is_error():
        raise result.get_error()
