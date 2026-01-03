import logging
import json
from pathlib import Path
from typing import List, Union, TextIO, Optional, Dict, Any

from pydantic import BaseModel, ValidationError
from prefect import task

from dataset_loader_prefect.prefrect.helper import upload_question

logger = logging.getLogger(__name__)


# ── 1) Pydantic schema for flattened records ────────────────────────────
class SimpleRecord(BaseModel):
    source: str
    question: str
    answer: str
    evidence: List[str]
    metadata: Optional[Dict[str, Any]] = None  # <- optional passthrough


# ── 2) Parser that accepts either flat list OR nested {FSTNR: {qtype: [...]}} ──
def parse_any_json(json_file: Union[str, Path, TextIO]) -> List[SimpleRecord]:
    """
    Accepts:
      A) flat list: [{"source","question","answer","question_type","evidence",...}, ...]
      B) nested dict: { "<FSTNR>": { "<qtype>": [ {BaseQuestion...}, ... ], ... }, ... }

    Returns a flat list of SimpleRecord.
    """
    close_after = False
    if isinstance(json_file, (str, Path)):
        json_file = open(json_file, encoding="utf-8")
        close_after = True

    try:
        data = json.load(json_file)

        if isinstance(data, dict):
            out: List[SimpleRecord] = []
            for fstnr, block in data.items():  # type: ignore
                if not isinstance(block, dict):
                    continue
                for qtype, items in block.items():  # type: ignore
                    if not isinstance(items, list):
                        continue
                    for q in items:  # type: ignore
                        # Expect BaseQuestion-like dicts produced by .model_dump()
                        # keys: source, question, metadata, evidence, answer
                        if not isinstance(q, dict):
                            continue
                        out.append(
                            SimpleRecord(
                                source=q.get("source", ""),  # type: ignore
                                question=q.get("question", ""),  # type: ignore
                                answer=q.get("answer", ""),  # type: ignore
                                evidence=q.get("evidence", []) or [],  # type: ignore
                                metadata=q.get("metadata"),  # type: ignore
                            )
                        )
            return out

        raise ValueError("Unsupported JSON structure: expected list or nested dict")

    except (ValidationError, Exception) as e:
        logger.error(f"Parsing failed: {e}")
        raise
    finally:
        if close_after:
            json_file.close()


# ── 3) Prefect task to upload ───────────────────────────────────────────
@task
async def upload_weimar(json_path: str):
    """
    Reads a JSON file (flat or nested) and pushes every question to the backend.
    Prints a total count.
    """
    records = parse_any_json(json_path)

    total = 0
    for _, rec in enumerate(records, start=1):
        # Compose metadata for the upload
        meta: Dict[str, Any] = {
            "domain": rec.source,
        }

        await upload_question(
            dataset_name="weimar",
            question=rec.question,
            expected_answer=rec.answer,
            expected_context=" || ".join(rec.evidence) if rec.evidence else "",
            expected_facts=rec.evidence,
            metadata=meta,
            metatdata_filter={},
        )
        total += 1
