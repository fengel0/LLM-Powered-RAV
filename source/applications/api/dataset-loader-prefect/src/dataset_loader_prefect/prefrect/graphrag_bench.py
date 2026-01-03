# graphrag_bench_uploader.py
from enum import Enum
import logging
from pathlib import Path
from typing import List, Union, TextIO

import json
from prefect import task
from pydantic import BaseModel, Field, ValidationError

from dataset_loader_prefect.prefrect.helper import upload_question

logger = logging.getLogger(__name__)


class FileType(Enum):
    medical = "medical"
    novel = "novel"


# ── 1. pydantic schema ───────────────────────────────────────────────────────────
# class QuestionTypeGR(str, Enum):
# FACT_RETRIEVAL = "Fact Retrieval"
# add other types that appear in graphrag-bench if you need them


class QARecordGR(BaseModel):
    id: str
    source: str
    question: str
    answer: str
    question_type: str  # keep open-ended in case new labels show up
    evidence: list[str] = Field(default_factory=list)
    # evidence_triple: List[str] | None = None


# ── 2. JSON-to-model helper ──────────────────────────────────────────────────────
def parse_json_to_models(json_file: Union[str, Path, TextIO]) -> List[QARecordGR]:
    """
    Read the GraphRAG-Bench questions JSON (array-of-objects) and
    return validated QARecordGR objects.
    """
    close_after = False
    if isinstance(json_file, (str, Path)):
        json_file = open(json_file, encoding="utf-8")
        close_after = True

    try:
        raw_data = json.load(json_file)  # full file is a JSON array
        records: list[QARecordGR] = []
        for i, obj in enumerate(raw_data, start=1):
            try:
                records.append(QARecordGR(**obj))
            except ValidationError as exc:
                logger.error(f"Error on item {i} {exc}", exc_info=True)
                raise exc
        return records
    finally:
        if close_after:
            json_file.close()


# ── 3. Prefect task to upload ────────────────────────────────────────────────────
@task
async def upload_graphrag_bench(json_path: str, file_type: FileType):
    """
    Push every question from the GraphRAG-Bench JSON file to the evaluation backend.
    """
    qa_rows = parse_json_to_models(json_path)

    for qa in qa_rows:
        expected_context = " || ".join(qa.evidence) if qa.evidence else ""
        # expected_facts = qa.evidence_triple or [qa.answer]

        await upload_question(
            dataset_name=f"graphrag_bench_{file_type.value}",
            expected_answer=qa.answer,
            expected_context=expected_context,
            question=qa.question,
            expected_facts=qa.evidence,
            metadata={
                "question_type_from_dataset": str(qa.question_type),
                "source": qa.source,
            },
            metatdata_filter={},
        )
