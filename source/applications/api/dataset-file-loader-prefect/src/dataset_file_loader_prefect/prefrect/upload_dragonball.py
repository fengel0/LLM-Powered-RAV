import logging
from domain.pipeline.events import EventName
from pathlib import Path
from typing import List, Union, TextIO

import json
from prefect.events import emit_event
from pydantic import BaseModel, ValidationError
from prefect import task

from file_uploader_service.usecase.upload_files import UploadeFilesUsecase

logger = logging.getLogger(__name__)


# ── 1. pydantic schema for a *document* entry ───────────────────────────────────
class DocRecord(BaseModel):
    domain: str
    language: str
    doc_id: int
    company_name: str | None = None
    content: str


# ── 2. JSONL-to-model helper ────────────────────────────────────────────────────
def parse_doc_jsonl(jsonl_file: Union[str, Path, TextIO]) -> List[DocRecord]:
    """
    Return validated DocRecord objects from a JSON-Lines file.
    """
    close_after = False
    if isinstance(jsonl_file, (str, Path)):
        jsonl_file = open(jsonl_file, encoding="utf-8")
        close_after = True

    try:
        docs: list[DocRecord] = []
        for line_no, raw in enumerate(jsonl_file, start=1):
            if not raw.strip():
                continue
            try:
                data = json.loads(raw)
                docs.append(DocRecord(**data))
            except ValidationError as exc:
                logger.error(f"error {exc} in line {line_no}", exc_info=True)
                raise exc
        return docs
    finally:
        if close_after:
            jsonl_file.close()


# ── 3. Prefect task that uploads each *doc* as a file blob ──────────────────────
@task
async def upload_dragonball(jsonl_path: str):
    """
    Stream every document in a Dragonball-style JSONL to the docbench bucket.
    Each record becomes a tiny `.txt` file whose bytes are sent to
    UploadeFilesUsecase.custom_upload().
    """
    records = parse_doc_jsonl(jsonl_path)

    for rec in records:
        pseudo_path = f"doc_{rec.doc_id}.txt"
        file_bytes = rec.content.encode("utf-8")

        if rec.language == "en":
            result = await UploadeFilesUsecase.Instance().custom_upload(
                filepath=pseudo_path,
                content=file_bytes,
                metdata={  # keep key spelling consistent with your existing call
                    "doc_id": str(rec.doc_id),
                    "domain": rec.domain,
                    "language": rec.language,
                    "company_name": rec.company_name or "unknown",
                    "file_name": pseudo_path,
                },
                project_name="dragonball",
            )

            if result.is_error():
                return result.get_error()
            file_id = result.get_ok()
            emit_event(
                event=EventName.FILE_CREATED_UPDATES.value,
                resource={"prefect.resource.id": f"file/{file_id}"},
            )
            logger.info(f"Emitted file ID {file_id}")
