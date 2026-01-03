import logging
from domain.database.validation.model import TestSample

from evaluation_service.usecase.evaluation import EvaluationServiceUsecases
from core.hash import compute_mdhash_id

logger = logging.getLogger(__name__)

counter = 0


async def upload_question(
    dataset_name: str,
    question: str,
    expected_answer: str,
    expected_context: str,
    expected_facts: list[str] = [],
    metadata: dict[str, str] = {},
    metatdata_filter: dict[str, list[str]] = {},
):
    global counter
    result = await EvaluationServiceUsecases.Instance().get_question_by_hash(
        hash=compute_mdhash_id(question)
    )
    if result.is_error():
        raise result.get_error()
    sample = result.get_ok()

    if sample:
        counter = counter + 1
        return

    result = await EvaluationServiceUsecases.Instance().add_question(
        admin_token="",
        question=TestSample(
            id="",
            dataset_id=dataset_name,
            retrival_complexity=0.0,
            expected_facts=expected_facts,
            question=question,
            question_hash=compute_mdhash_id(question),
            expected_answer=expected_answer,
            expected_context=expected_context,
            question_type="unknown",  # Literal["factoid", "list", "numeric", "table_lookup", "aggregation"],
            metatdata=metadata,
            metatdata_filter=metatdata_filter,
        ),
    )
    if result.is_error():
        raise result.get_error()
    logger.info(f"created {question}")
