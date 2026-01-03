# tests/test_postgres_db_state_store.py
import logging
from core.hash import compute_mdhash_id
from domain.hippo_rag.interfaces import StateStore
from domain.hippo_rag.model import (
    Triple,
    Document,
    DocumentCollection,
)

from domain_test import AsyncTestBase

logger = logging.getLogger(__name__)


class TestDBStateStore(AsyncTestBase):
    state_store: StateStore

    # ------------------------------------------------------------------ fixtures
    def _make_document(
        self,
        idx: str = "doc1",
        passage: str = "Test passage",
        entities: list[str] | None = None,
        triples: list[Triple] | None = None,
        metadata: dict[str, str | int | float] | None = None,
    ) -> Document:
        return Document(
            idx=idx,
            passage=passage,
            extracted_entities=entities or ["entity1", "entity2"],
            extracted_triples=triples or [("entity1", "relates_to", "entity2")],
            metadata=metadata or {"source": "test", "page": 1},
        )

    def _make_document_collection(
        self, documents: list[Document] | None = None
    ) -> DocumentCollection:
        if documents is None:
            documents = [
                self._make_document("doc1", "First document"),
                self._make_document(
                    "doc2",
                    "Second document",
                    entities=["entity3", "entity4"],
                    triples=[("entity3", "connects_to", "entity4")],
                ),
            ]
        return DocumentCollection(docs=documents)

    # ------------------------------------------------------------------ tests

    async def test_store_and_load_openie_info(self):
        docs = self._make_document_collection()
        store = await self.state_store.store_openie_info(docs)
        if store.is_error():
            logger.error(store.get_error())
        assert store.is_ok()

        loaded = await self.state_store.load_openie_info()
        if loaded.is_error():
            logger.error(loaded.get_error())
        assert loaded.is_ok()
        assert {d.idx for d in loaded.get_ok().docs} == {"doc1", "doc2"}

    async def test_load_openie_info_with_metadata_empty(self):
        docs = self._make_document_collection()
        result = await self.state_store.store_openie_info(docs)
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()

        loaded = await self.state_store.load_openie_info_with_metadata({})
        assert loaded.is_ok()
        assert len(loaded.get_ok().docs) == 2

    async def test_load_openie_info_with_metadata_filter(self):
        doc1 = self._make_document("doc1", metadata={"source": "test", "page": 1})
        doc2 = self._make_document("doc2", metadata={"source": "prod", "page": 2})
        doc3 = self._make_document("doc3", metadata={"source": "test", "page": 3})

        result = await self.state_store.store_openie_info(
            DocumentCollection(docs=[doc1, doc2, doc3])
        )
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()

        loaded = await self.state_store.load_openie_info_with_metadata(
            {"source": ["test"]}
        )
        if loaded.is_error():
            logger.error(loaded.get_error())
        assert loaded.is_ok()
        assert {d.metadata["source"] for d in loaded.get_ok().docs} == {"test"}
        assert len(loaded.get_ok().docs) == 2

    async def test_triples_to_docs(self):
        triple1: Triple = ("entity1", "relates_to", "entity2")
        triple2: Triple = ("entity3", "connects_to", "entity4")

        doc1 = self._make_document("doc1", triples=[triple1])
        doc2 = self._make_document("doc2", triples=[triple2, triple1])

        result = await self.state_store.store_openie_info(
            DocumentCollection(docs=[doc1, doc2])
        )
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()

        r1 = await self.state_store.triples_to_docs(triple1)
        if r1.is_error():
            logger.error(r1.get_error())
        assert r1.is_ok()
        assert set(r1.get_ok()) == {"doc1", "doc2"}

        r2 = await self.state_store.triples_to_docs(triple2)
        if r2.is_error():
            logger.error(r2.get_error())
        assert r2.is_ok()
        assert r2.get_ok() == ["doc2"]

        r3 = await self.state_store.triples_to_docs(("x", "y", "z"))
        assert r3.is_ok()
        assert r3.get_ok() == []

    async def test_ent_node_to_chunk(self):
        doc1 = self._make_document("doc1", triples=[("entity1", "v", "entity2")])
        doc2 = self._make_document("doc2", triples=[("entity2", "v", "entity3")])

        result = await self.state_store.store_openie_info(
            DocumentCollection(docs=[doc1, doc2])
        )
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()

        r1 = await self.state_store.ent_node_to_chunk(compute_mdhash_id("entity1"))
        if r1.is_error():
            logger.error(r1.get_error())
        assert r1.is_ok() and r1.get_ok() == ["doc1"]

        r2 = await self.state_store.ent_node_to_chunk(compute_mdhash_id("entity2"))
        if r2.is_error():
            logger.error(r2.get_error())
        assert r2.is_ok()
        assert set(r2.get_ok()) == {"doc1", "doc2"}

        r3 = await self.state_store.ent_node_to_chunk(compute_mdhash_id("missing"))
        if r3.is_error():
            logger.error(r3.get_error())
        assert r3.is_ok()
        assert r3.is_ok() and r3.get_ok() == []

    async def test_ent_node_count(self):
        d1 = self._make_document("d1", triples=[("e1", "v", "e2")])
        d2 = self._make_document("d2", triples=[("e2", "v", "e3")])
        d3 = self._make_document("d3", triples=[("e4", "v", "e1")])

        result = await self.state_store.store_openie_info(
            DocumentCollection(docs=[d1, d2, d3])
        )
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()

        count = await self.state_store.ent_node_count()
        if count.is_error():
            logger.error(count.get_error())
        assert count.is_ok()
        assert count.get_ok() == 4

    async def test_fetch_not_existing_documents(self):
        d1, d2 = self._make_document("d1"), self._make_document("d2")
        await self.state_store.store_openie_info(DocumentCollection(docs=[d1, d2]))

        r = await self.state_store.fetch_not_existing_documents(["d1", "d2", "d3"])
        if r.is_error():
            logger.error(r.get_error())
        assert r.is_ok()
        assert set(r.get_ok()) == {"d3"}

        r_empty = await self.state_store.fetch_not_existing_documents([])
        assert r_empty.is_ok() and r_empty.get_ok() == []

    async def test_fetch_chunks_by_ids(self):
        docs = [self._make_document(f"d{i}") for i in range(1, 4)]
        result = await self.state_store.store_openie_info(DocumentCollection(docs=docs))
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()

        r = await self.state_store.fetch_chunks_by_ids(["d1", "d3"])
        if r.is_error():
            logger.error(r.get_error())
        assert r.is_ok()
        idxs = {d.idx for d in r.get_ok().docs}
        assert idxs == {"d1", "d3"}

        r_empty = await self.state_store.fetch_chunks_by_ids([])
        assert r_empty.is_ok() and r_empty.get_ok().docs == []

    async def test_delete_chunks(self):
        t1: Triple = ("e1", "relates", "e2")
        t2: Triple = ("e3", "connects", "e4")

        d1 = self._make_document("d1", entities=["e1", "e2"], triples=[t1])
        d2 = self._make_document("d2", entities=["e3", "e4"], triples=[t2])

        result = await self.state_store.store_openie_info(
            DocumentCollection(docs=[d1, d2])
        )
        if result.is_error():
            logger.error(result.get_error())

        before = await self.state_store.load_openie_info()
        if before.is_error():
            logger.error(before.get_error())
        assert before.is_ok()
        assert len(before.get_ok().docs) == 2

        delete = await self.state_store.delete_chunks(["d1"])
        if delete.is_error():
            logger.error(delete.get_error())
        assert delete.is_ok()

        after = await self.state_store.load_openie_info()
        if after.is_error():
            logger.error(after.get_error())
        assert after.is_ok()
        assert [d.idx for d in after.get_ok().docs] == ["d2"]

        e1map = await self.state_store.ent_node_to_chunk(compute_mdhash_id("e1"))
        if e1map.is_error():
            logger.error(e1map.get_error())
        assert e1map.is_ok()
        assert e1map.get_ok() == []

        t1map = await self.state_store.triples_to_docs(t1)
        if t1map.is_error():
            logger.error(t1map.get_error())
        assert t1map.is_ok()
        assert t1map.get_ok() == []

    async def test_store_duplicate_documents(self):
        d1 = self._make_document("doc1", "original")
        result = await self.state_store.store_openie_info(DocumentCollection(docs=[d1]))
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()

        d1_updated = self._make_document("doc1", "updated")
        result = await self.state_store.store_openie_info(
            DocumentCollection(docs=[d1_updated])
        )
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()

        loaded = await self.state_store.load_openie_info()
        if loaded.is_error():
            logger.error(loaded.get_error())
        assert loaded.is_ok()
        assert [d.passage for d in loaded.get_ok().docs] == ["updated"]

    async def test_add_chunks_to_node_avoids_duplicates(self):
        d1 = self._make_document("doc1", entities=["e1"], triples=[("e1", "v", "e1")])
        result = await self.state_store.store_openie_info(DocumentCollection(docs=[d1]))
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()

        chunks = await self.state_store.ent_node_to_chunk(compute_mdhash_id("e1"))
        if chunks.is_error():
            logger.error(chunks.get_error())
        assert chunks.is_ok()
        assert chunks.get_ok() == ["doc1"]

    async def test_add_chunks_to_triple_avoids_duplicates(self):
        t1: Triple = ("e1", "r", "e2")
        d1 = self._make_document("doc1", triples=[t1])
        result = await self.state_store.store_openie_info(DocumentCollection(docs=[d1]))
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()

        docs = await self.state_store.triples_to_docs(t1)
        assert docs.is_ok()
        assert docs.get_ok() == ["doc1"]

    async def test_store_empty_document_collection(self):
        r = await self.state_store.store_openie_info(DocumentCollection(docs=[]))
        if r.is_error():
            logger.error(r.get_error())
        assert r.is_ok()

        loaded = await self.state_store.load_openie_info()
        assert loaded.is_ok() and loaded.get_ok().docs == []

    async def test_complex_metadata_filtering(self):
        d1 = self._make_document("d1", metadata={"source": "web", "type": "article"})
        d2 = self._make_document("d2", metadata={"source": "book", "type": "chapter"})
        d3 = self._make_document("d3", metadata={"source": "web", "type": "blog"})
        d4 = self._make_document("d4", metadata={"source": "book", "type": "article"})

        result = await self.state_store.store_openie_info(
            DocumentCollection(docs=[d1, d2, d3, d4])
        )
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()

        r1 = await self.state_store.load_openie_info_with_metadata(
            {"source": ["web"], "type": ["article"]}
        )
        assert r1.is_ok()
        if r1.is_error():
            logger.error(r1.get_error())
        assert [d.idx for d in r1.get_ok().docs] == ["d1"]

        r2 = await self.state_store.load_openie_info_with_metadata(
            {"type": ["article", "blog"]}
        )
        if r2.is_error():
            logger.error(r2.get_error())
        assert r2.is_ok()
        idxs = {d.idx for d in r2.get_ok().docs}
        assert idxs == {"d1", "d3", "d4"}
