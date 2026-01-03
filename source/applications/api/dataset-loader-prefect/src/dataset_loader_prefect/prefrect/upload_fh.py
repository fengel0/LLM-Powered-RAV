import logging
import json
from pathlib import Path
from typing import List, Union, TextIO

from pydantic import BaseModel, ValidationError
from prefect import task

from dataset_loader_prefect.prefrect.helper import upload_question

logger = logging.getLogger(__name__)


# ── 1. Pydantic schema for the new format ───────────────────────────────
class SimpleRecord(BaseModel):
    source: str
    question: str
    answer: str
    question_type: str
    evidence: List[str]


# ── 2. JSON-to-model helper ─────────────────────────────────────────────
def parse_simple_json(
    json_file: Union[str, Path, TextIO],
) -> List[SimpleRecord]:
    """
    Read a plain JSON file (list of objects) and return validated SimpleRecord objects.
    """
    close_after = False
    if isinstance(json_file, (str, Path)):
        json_file = open(json_file, encoding="utf-8")
        close_after = True

    try:
        data = json.load(json_file)
        return [SimpleRecord(**rec) for rec in data]
    except ValidationError as e:
        logger.error(f"Validation failed: {e}")
        raise
    finally:
        if close_after:
            json_file.close()


# ── 3. Prefect task to upload ──────────────────────────────────────────
@task
async def upload_fh(json_path: str):
    """
    Push every question in the simple JSON file to the evaluation backend.
    """
    records = parse_simple_json(json_path)

    for i, rec in enumerate(records, start=1):
        await upload_question(
            dataset_name="fachhochschule_erfurt",
            question=rec.question,
            expected_answer=rec.answer,
            expected_context=" || ".join(rec.evidence) if rec.evidence else "",
            expected_facts=rec.evidence,  # no explicit keypoints in this format
            metadata={"domain": rec.source, "query_type": rec.question_type},
            metatdata_filter={},  # no doc_ids available
        )
