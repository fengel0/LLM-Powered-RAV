from typing import cast
from tortoise import fields
from domain.hippo_rag.model import Triple, Document
from database.session import DatabaseBaseModel
from tortoise.contrib.postgres.indexes import GinIndex


class TripleToDocDB(DatabaseBaseModel):
    triple = fields.CharField(max_length=1024)  # ["s","p","o"]
    doc_id = fields.CharField(max_length=255)


class EntNodeChunkDB(DatabaseBaseModel):
    ent_node = fields.CharField(max_length=255, db_index=True)
    chunk_id = fields.CharField(max_length=255)


class OpenIEDocumentDB(DatabaseBaseModel):
    idx = fields.CharField(max_length=255, unique=True, db_index=True)
    passage = fields.TextField()
    extracted_entities = fields.JSONField[list[str]]()  # list[str]
    extracted_triples = fields.JSONField[list[list[str]]]()  # list[list[str]]
    metadata = fields.JSONField[dict[str, str | int | float]]()  # list[list[str]]

    class Meta:  # type: ignore
        indexes = [GinIndex(fields=["metadata"])]


def triple_to_json(t: Triple) -> list[str]:
    s, p, o = t
    return [s, p, o]


def json_to_triple(t: list[str]) -> Triple:
    if not isinstance(t, list) or len(t) != 3:  # type: ignore
        raise ValueError("Invalid triple payload; expected list of [s,p,o].")
    return t[0], t[1], t[2]


def db_to_document(row: OpenIEDocumentDB) -> Document:
    triples_json = cast(list[list[str]], row.extracted_triples or [])  # type: ignore
    triples: list[Triple] = [json_to_triple(t) for t in triples_json]
    entities = cast(list[str], row.extracted_entities or [])  # type: ignore
    return Document(
        idx=row.idx,
        passage=row.passage,
        extracted_entities=list(entities),
        extracted_triples=triples,
        metadata=row.metadata,
    )


def document_to_db(doc: Document) -> OpenIEDocumentDB:
    triples_json: list[list[str]] = [triple_to_json(t) for t in doc.extracted_triples]
    return OpenIEDocumentDB(
        idx=doc.idx,
        passage=doc.passage,
        extracted_entities=list(doc.extracted_entities),
        extracted_triples=triples_json,
        metadata=doc.metadata,
    )
