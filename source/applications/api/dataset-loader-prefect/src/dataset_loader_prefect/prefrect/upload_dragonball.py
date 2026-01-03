import logging
from pathlib import Path
from typing import List, Union, TextIO

import json
from pydantic import BaseModel, ValidationError
from prefect import task

from dataset_loader_prefect.prefrect.helper import upload_question

logger = logging.getLogger(__name__)


# ── 1. pydantic schemas for the Dragonball format ───────────────────────────────


class DragonballQuery(BaseModel):
    query_id: int
    query_type: str
    content: str  # the *question* text


class DragonballGroundTruth(BaseModel):
    doc_ids: List[int]
    content: str  # the canonical gold answer
    references: List[str]  # short supporting snippets
    keypoints: List[str]  # one-sentence fact statements


class DragonballRecord(BaseModel):
    domain: str
    language: str
    query: DragonballQuery
    ground_truth: DragonballGroundTruth
    prediction: dict  # present but ignored for upload


# ── 2. JSONL-to-model helper ────────────────────────────────────────────────────
def parse_dragonball_jsonl(
    jsonl_file: Union[str, Path, TextIO],
) -> List[DragonballRecord]:
    """
    Read a Dragonball JSON-Lines file and return validated DragonballRecord objects.
    """
    close_after = False
    if isinstance(jsonl_file, (str, Path)):
        jsonl_file = open(jsonl_file, encoding="utf-8")
        close_after = True

    try:
        records: list[DragonballRecord] = []
        for line_no, raw in enumerate(jsonl_file, start=1):
            if not raw.strip():
                continue
            try:
                data = json.loads(raw)
                rec = DragonballRecord(**data)
                records.append(rec)
            except Exception as e:
                # re-raise with a clearer line number
                logger.error(
                    f"Dragonball JSONL validation {e} failed on line {line_no}"
                )
                raise e
        return records
    except Exception as e:
        logger.error(f"Error appeared {e}", exc_info=True)
        raise e
    finally:
        if close_after:
            jsonl_file.close()


# ── 3. Prefect task to upload ───────────────────────────────────────────────────
@task
async def upload_dragonball(jsonl_path: str):
    """
    Push every Dragonball question in the JSONL file to the evaluation backend.
    """
    qa_rows = parse_dragonball_jsonl(jsonl_path)

    for qa in qa_rows:
        if qa.language == "en":
            await upload_question(
                # prefix keeps IDs globally unique
                dataset_name="dragonball",
                question=qa.query.content,
                expected_answer=qa.ground_truth.content or "",
                expected_context=" || ".join(qa.ground_truth.references) or "",
                expected_facts=qa.ground_truth.keypoints,
                metadata={"domain": qa.domain, "query_type": qa.query.query_type},
                metatdata_filter={
                    "doc_id": [str(id) for id in qa.ground_truth.doc_ids]
                },
            )
