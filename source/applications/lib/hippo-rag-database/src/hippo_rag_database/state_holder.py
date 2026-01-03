from __future__ import annotations
from core.hash import compute_mdhash_id
from copy import deepcopy
import asyncio
import operator
from functools import reduce
from tortoise.expressions import Q

import logging

from opentelemetry import trace

from core.result import Result
from database.session import BaseDatabase

from domain.hippo_rag.interfaces import StateStore
from domain.hippo_rag.model import Triple, DocumentCollection
from hippo_rag_database.model import (
    TripleToDocDB,
    EntNodeChunkDB,
    OpenIEDocumentDB,
    db_to_document,
    document_to_db,
)

logger = logging.getLogger(__name__)


class _InternPostgresDBTripleToDoc(BaseDatabase[TripleToDocDB]):
    def __init__(self):
        super().__init__(TripleToDocDB)


class _InternPostgresDBEntNodeChunk(BaseDatabase[EntNodeChunkDB]):
    def __init__(self):
        super().__init__(EntNodeChunkDB)


class _InternPostgresDBOpenIE(BaseDatabase[OpenIEDocumentDB]):
    def __init__(self):
        super().__init__(OpenIEDocumentDB)


class PostgresDBStateStore(StateStore):
    _db_triple_to_doc: _InternPostgresDBTripleToDoc
    _db_ent_node_chunk: _InternPostgresDBEntNodeChunk
    _db_openie: _InternPostgresDBOpenIE
    tracer: trace.Tracer

    def __init__(self) -> None:
        self._db_triple_to_doc = _InternPostgresDBTripleToDoc()
        self._db_ent_node_chunk = _InternPostgresDBEntNodeChunk()
        self._db_openie = _InternPostgresDBOpenIE()
        self.tracer = trace.get_tracer("StateStore")

    async def triples_to_docs(self, triples: Triple) -> Result[list[str]]:
        # Note: DB stores triple as JSON list ["s","p","o"], so query accordingly.
        with self.tracer.start_as_current_span("triples-to-docs"):
            try:
                q = {"triple": compute_mdhash_id(str(triples))}
                result = await self._db_triple_to_doc.run_query(query=q)
                if result.is_error():
                    return result.propagate_exception()
                rows = result.get_ok()
                return Result.Ok([r.doc_id for r in rows])
            except Exception as e:
                logger.error(e, exc_info=True)
                return Result.Err(e)

    async def ent_node_to_chunk(self, ent_node: str) -> Result[list[str]]:
        with self.tracer.start_as_current_span("ent-node-to-chunk"):
            try:
                result = await self._db_ent_node_chunk.run_query(
                    query={"ent_node": ent_node}
                )
                if result.is_error():
                    return result.propagate_exception()
                rows = result.get_ok()
                return Result.Ok([r.chunk_id for r in rows])
            except Exception as e:
                logger.error(e, exc_info=True)
                return Result.Err(e)

    async def _delete_entity_in_chunk(
        self, ent_node: str, chunk_id: str
    ) -> Result[None]:
        with self.tracer.start_as_current_span("ent-node-to-chunk"):
            try:
                result = await self._db_ent_node_chunk.run_query(
                    query={
                        "ent_node": compute_mdhash_id(ent_node),
                        "chunk_id": chunk_id,
                    }
                )
                if result.is_error():
                    return result.propagate_exception()
                rows = result.get_ok()
                if len(rows) > 0:
                    return await self._db_ent_node_chunk.delete(str(rows[0].id))
                return Result.Ok(None)
            except Exception as e:
                logger.error(e, exc_info=True)
                return Result.Err(e)

    async def _delete_triple_in_chunk(
        self, triple: Triple, chunk_id: str
    ) -> Result[None]:
        with self.tracer.start_as_current_span("ent-node-to-chunk"):
            try:
                result = await self._db_triple_to_doc.run_query(
                    query={"triple": compute_mdhash_id(str(triple)), "doc_id": chunk_id}
                )
                if result.is_error():
                    return result.propagate_exception()
                rows = result.get_ok()
                if len(rows) > 0:
                    return await self._db_triple_to_doc.delete(str(rows[0].id))
                return Result.Ok(None)
            except Exception as e:
                logger.error(e, exc_info=True)
                return Result.Err(e)

    async def ent_node_count(self) -> Result[int]:
        with self.tracer.start_as_current_span("ent-node-count"):
            try:
                result = (
                    await EntNodeChunkDB.all()
                    .distinct()
                    .values_list("ent_node", flat=True)
                )
                # count distinct entity nodes
                return Result.Ok(len(result))
            except Exception as e:
                logger.error(e, exc_info=True)
                return Result.Err(e)

    async def _add_chunks_to_triple(
        self, triple: Triple, chunk_ids: list[str]
    ) -> Result[None]:
        with self.tracer.start_as_current_span("add-chunks-to-node"):
            try:
                # Avoid duplicates: fetch existing mappings
                existing_result = await self.triples_to_docs(triple)
                if existing_result.is_error():
                    return existing_result.propagate_exception()
                existing_chunks = set(existing_result.get_ok() or [])
                new_chunks = [cid for cid in chunk_ids if cid not in existing_chunks]

                if not new_chunks:
                    return Result.Ok(None)

                # Optional: swap for bulk_create if your BaseDatabase exposes it
                for cid in new_chunks:
                    await self._db_triple_to_doc.create(
                        TripleToDocDB(triple=compute_mdhash_id(str(triple)), doc_id=cid)
                    )
                return Result.Ok(None)
            except Exception as e:
                logger.error(e, exc_info=True)
                return Result.Err(e)

    async def _add_chunks_to_node(
        self, ent_node: str, chunk_ids: list[str]
    ) -> Result[None]:
        with self.tracer.start_as_current_span("add-chunks-to-node"):
            try:
                # Avoid duplicates: fetch existing mappings
                hash = compute_mdhash_id(ent_node)
                existing_result = await self.ent_node_to_chunk(hash)
                if existing_result.is_error():
                    return existing_result.propagate_exception()
                existing_chunks = set(existing_result.get_ok() or [])
                new_chunks = [cid for cid in chunk_ids if cid not in existing_chunks]

                if not new_chunks:
                    return Result.Ok(None)

                # Optional: swap for bulk_create if your BaseDatabase exposes it
                for cid in new_chunks:
                    result = await self._db_ent_node_chunk.create(
                        EntNodeChunkDB(ent_node=hash, chunk_id=cid)
                    )
                    if result.is_error():
                        return result.propagate_exception()
                return Result.Ok(None)
            except Exception as e:
                logger.error(e, exc_info=True)
                return Result.Err(e)

    async def load_openie_info_with_metadata(
        self, metadata: dict[str, list[str] | list[float] | list[int]]
    ) -> Result[DocumentCollection]:
        with self.tracer.start_as_current_span("load-openie-info-with-metadata"):
            try:
                if not metadata:
                    qs = OpenIEDocumentDB.all().order_by("-created_at")
                    docs_db = await qs
                    return Result.Ok(
                        DocumentCollection(docs=[db_to_document(d) for d in docs_db])
                    )

                q_total: Q | None = None
                for key, values in metadata.items():
                    if not values:
                        continue

                    per_value_qs = (
                        Q(**{"metadata__contains": {key: v}})  # type: ignore
                        for v in values
                    )
                    key_q = reduce(operator.or_, per_value_qs)
                    q_total = key_q if q_total is None else (q_total & key_q)

                qs = (
                    OpenIEDocumentDB.filter(q_total)
                    if q_total is not None
                    else OpenIEDocumentDB.all()
                )
                qs = qs.order_by("-created_at")
                docs_db = await qs
                docs_domain = [db_to_document(doc) for doc in docs_db]
                return Result.Ok(DocumentCollection(docs=docs_domain))
            except Exception as e:
                logger.error(e, exc_info=True)
                return Result.Err(e)

    async def load_openie_info(
        self, offset: int = 0, chunk_size: int = 1024
    ) -> Result[DocumentCollection]:
        with self.tracer.start_as_current_span("load-openie-info"):
            try:
                result = await self._db_openie.get_all_with_offset(
                    offset=offset, chunk_size=chunk_size
                )

                if result.is_error():
                    return result.propagate_exception()
                docs_db = result.get_ok()
                docs_domain = [db_to_document(doc) for doc in docs_db]
                return Result.Ok(DocumentCollection(docs=docs_domain))
            except Exception as e:
                logger.error(e, exc_info=True)
                return Result.Err(e)

    async def fetch_not_existing_documents(
        self, hash_ids: list[str]
    ) -> Result[list[str]]:
        with self.tracer.start_as_current_span("fetch-not-existing-ids"):
            try:
                if not hash_ids:
                    return Result.Ok(([]))

                missing = deepcopy(hash_ids)

                # Chunk the IN clause for very large inputs
                for ids in _chunked(hash_ids, 10):
                    results = await asyncio.gather(
                        *[self._db_openie.run_query_first({"idx": id}) for id in ids]
                    )
                    for result in results:
                        if result.is_error():
                            return result.propagate_exception()
                        document = result.get_ok()
                        if document:
                            missing.remove(document.idx)

                return Result.Ok(missing)
            except Exception as e:
                logger.error(e, exc_info=True)
                return Result.Err(e)

    async def store_openie_info(self, documents: DocumentCollection) -> Result[None]:
        with self.tracer.start_as_current_span("store-openie-info"):
            try:
                result = await self._fetch_chunks_by_ids(
                    [doc.idx for doc in documents.docs]
                )
                if result.is_error():
                    return result.propagate_exception()
                found_doc = result.get_ok()
                map_hash_id_to_db = {doc.idx: doc.id for doc in found_doc}

                for doc in documents.docs:
                    db_obj = document_to_db(doc)
                    if db_obj.idx in map_hash_id_to_db.keys():
                        db_obj.id = map_hash_id_to_db[db_obj.idx]
                        result = await self._db_openie.update(db_obj)
                    else:
                        result = await self._db_openie.create(db_obj)

                    if result.is_error():
                        return result.propagate_exception()

                    for triple in doc.extracted_triples:
                        result_triple = self._add_chunks_to_triple(
                            triple=triple, chunk_ids=[doc.idx]
                        )
                        if result.is_error():
                            return result.propagate_exception()
                        entities = [triple[0], triple[2]]
                        results = await asyncio.gather(
                            *[
                                self._add_chunks_to_node(ent, [doc.idx])
                                for ent in entities
                            ],
                            result_triple,
                        )
                        for result in results:
                            if result.is_error():
                                return result.propagate_exception()

                return Result.Ok(None)
            except Exception as e:
                logger.error(e, exc_info=True)
                return Result.Err(e)

    async def delete_chunks(self, hash_ids: list[str]) -> Result[None]:
        with self.tracer.start_as_current_span("delete-chunks"):
            try:
                result = await self._fetch_chunks_by_ids(hash_ids=hash_ids)
                if result.is_error():
                    return result.propagate_exception()
                found_chunks = result.get_ok()
                for doc in found_chunks:
                    result = await self._db_openie.delete(str(doc.id))
                    if result.is_error():
                        return result.propagate_exception()

                    for triple in doc.extracted_triples:
                        assert len(triple) == 3
                        result_triple = self._delete_triple_in_chunk(
                            triple=(triple[0], triple[1], triple[2]),
                            chunk_id=doc.idx,
                        )
                        if result.is_error():
                            return result.propagate_exception()
                        entities = [triple[0], triple[2]]
                        results = await asyncio.gather(
                            *[
                                self._delete_entity_in_chunk(ent, doc.idx)
                                for ent in entities
                            ],
                            result_triple,
                        )
                        for result in results:
                            if result.is_error():
                                return result.propagate_exception()

                return Result.Ok(None)
            except Exception as e:
                logger.error(e, exc_info=True)
                return Result.Err(e)

    async def fetch_chunks_by_ids(
        self, hash_ids: list[str]
    ) -> Result[DocumentCollection]:
        with self.tracer.start_as_current_span("fetch-by-chunks-id"):
            try:
                result = await self._fetch_chunks_by_ids(hash_ids=hash_ids)
                if result.is_error():
                    return result.propagate_exception()
                docs_db = result.get_ok()
                docs_domain = [db_to_document(doc) for doc in docs_db]
                return Result.Ok(DocumentCollection(docs=docs_domain))
            except Exception as e:
                logger.error(e, exc_info=True)
                return Result.Err(e)

    async def _fetch_chunks_by_ids(
        self, hash_ids: list[str]
    ) -> Result[list[OpenIEDocumentDB]]:
        with self.tracer.start_as_current_span("fetch-by-chunks-id"):
            try:
                if not hash_ids:
                    return Result.Ok([])
                result = await self._db_openie.run_query(query={"idx__in": hash_ids})
                if result.is_error():
                    return result.propagate_exception()
                docs_db = result.get_ok()

                return Result.Ok(docs_db)
            except Exception as e:
                logger.error(e, exc_info=True)
                return Result.Err(e)


def _chunked(seq: list[str], size: int):
    for i in range(0, len(seq), size):
        yield seq[i : i + size]
