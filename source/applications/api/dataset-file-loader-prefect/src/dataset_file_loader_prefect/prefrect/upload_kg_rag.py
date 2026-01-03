from enum import Enum
from pathlib import Path
from typing import List, Union, TextIO
import csv

from prefect import task
from pydantic import BaseModel, ValidationError

from dataset_loader_prefect.prefrect.helper import upload_question


# ── 1. Pydantic schema ──────────────────────────────────────────────────────────
class QuestionType(str, Enum):
    MULTI_DOC_RAG = "Multi-Doc RAG"
    SINGLE_DOC_SINGLE_CHUNK_RAG = "Single-Doc Single-Chunk RAG"
    SINGLE_DOC_MULTI_CHUNK_RAG = "Single-Doc Multi-Chunk RAG"

    # add other values as they appear in future data


class SourceChunkType(str, Enum):
    TABLE = "Table"
    TEXT = "Text"
    # extend as needed


class QARecord(BaseModel):
    question: str
    source_docs: str
    question_type: QuestionType
    source_chunk_type: SourceChunkType
    answer: str


# ── 2. CSV-to-model helper ──────────────────────────────────────────────────────
def parse_csv_to_models(csv_file: Union[str, Path, TextIO]) -> List[QARecord]:
    """
    Read a CSV file and return a list of QARecord instances.

    Parameters
    ----------
    csv_file : str | Path | TextIO
        Path to the CSV file **or** an already-opened file/stream.

    Returns
    -------
    List[QARecord]
        A list of validated records.

    Raises
    ------
    ValidationError
        If any row fails model validation.
    """
    # Accept both file paths and file-like objects
    close_after = False
    if isinstance(csv_file, (str, Path)):
        csv_file = open(csv_file, newline="", encoding="utf-8")
        close_after = True

    try:
        reader = csv.DictReader(csv_file)
        records: List[QARecord] = []

        for line_no, row in enumerate(reader, start=2):  # +2: header is line 1
            try:
                record = QARecord(
                    question=row["Question"].strip(),
                    source_docs=row["Source Docs"].strip(),
                    question_type=row["Question Type"].strip(),  # type: ignore
                    source_chunk_type=row["Source Chunk Type"].strip(),  # type: ignore
                    answer=row["Answer"].strip(),
                )
                records.append(record)
            except ValidationError as exc:
                raise ValidationError(exc.errors()) from ValueError(
                    f"CSV validation failed on line {line_no}"
                )

        return records
    finally:
        if close_after:
            csv_file.close()


@task
async def upload_kg_rag(file_name: str):
    qa_rows = parse_csv_to_models(file_name)
    for index, qa in enumerate(qa_rows):
        await upload_question(
            question_id=f"kg_rag_{index}",
            dataset_name="kg_rag",
            expected_answer=qa.answer,
            expected_context=qa.source_docs,
            question=qa.question,
            metadata={
                "question_type_from_dataset": qa.question_type,
            },
        )
