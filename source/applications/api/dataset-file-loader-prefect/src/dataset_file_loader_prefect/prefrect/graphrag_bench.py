# graphrag_bench_uploader.py
import logging
from prefect.events import emit_event
from domain.pipeline.events import EventName
from enum import Enum
from pathlib import Path
from typing import List, Union, TextIO
from file_uploader_service.usecase.upload_files import UploadeFilesUsecase

import json
from prefect import task
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)


class FileType(Enum):
    medical = "medical"
    novel = "novel"


class Files(BaseModel):
    corpus_name: str
    context: str


# ── 2. JSON-to-model helper ──────────────────────────────────────────────────────
def parse_json_to_models(json_file: Union[str, Path, TextIO]) -> List[Files]:
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
        records: list[Files] = []
        for i, obj in enumerate(raw_data, start=1):
            try:
                records.append(Files(**obj))
            except ValidationError as exc:
                raise ValidationError(exc.errors()) from ValueError(
                    f"JSON validation failed on element {i}"
                )
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
        result = await UploadeFilesUsecase.Instance().custom_upload(
            filepath=f"{qa.corpus_name}.txt",
            content=qa.context.encode(),
            metdata={"source": qa.corpus_name},
            project_name=f"graphrag_bench_{file_type.value}",
        )
        if result.is_error():
            raise result.get_error()

        file_id = result.get_ok()

        emit_event(
            event=EventName.FILE_CREATED_UPDATES.value,
            resource={"prefect.resource.id": f"file/{file_id}"},
        )
        logger.info(f"Emitted file ID {file_id}")
