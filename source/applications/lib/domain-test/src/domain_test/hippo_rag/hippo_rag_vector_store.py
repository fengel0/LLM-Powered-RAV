# tests/test_qdrant_embedding_store.py
from __future__ import annotations

import logging
import os


from domain.hippo_rag.interfaces import EmbeddingStoreInterface
from core.hash import compute_mdhash_id
from core.logger import init_logging


from domain_test import AsyncTestBase

init_logging("debug")
logger = logging.getLogger(__name__)

QDRANT_HTTP_PORT = 6333
QDRANT_GRPC_PORT = 6334
QDRANT_IMAGE = os.environ.get("QDRANT_IMAGE", "qdrant/qdrant:v1.12.6")
EMBED_ADDR = os.getenv("EMBED_ADDR", "")
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "768"))  # sensible default


# --------------------------- lowest base with tests ---------------------------


class TestQdrantEmbeddingStoreBase(AsyncTestBase):
    __test__ = False
    store: EmbeddingStoreInterface

    async def _hash(self, text: str) -> str:
        return compute_mdhash_id(text)

    # --------------------------- tests ---------------------------

    async def test_insert_and_get_row_and_idempotency(self):
        texts = ["apple", "banana"]
        r = await self.store.is_doc_already_inserted(texts)
        if r.is_error():
            logger.error(r.get_error())
        assert r.is_ok()
        assert len(r.get_ok()) == 2

        r = await self.store.insert_strings(texts)
        if r.is_error():
            logger.error(r.get_error())
        assert r.is_ok()

        r = await self.store.is_doc_already_inserted(texts)
        if r.is_error():
            logger.error(r.get_error())
        assert r.is_ok()
        assert len(r.get_ok()) == 0

        # check if double texts are not created
        r = await self.store.insert_strings(texts)
        if r.is_error():
            logger.error(r.get_error())
        assert r.is_ok()

        ids_res = await self.store.get_all_ids()
        if ids_res.is_error():
            logger.error(ids_res.get_error())
        assert ids_res.is_ok()
        ids = ids_res.get_ok()
        assert len(ids) == 2

        # get_row
        hid_apple = await self._hash("apple")
        row_res = await self.store.get_row(hid_apple)
        if row_res.is_error():
            logger.error(row_res.get_error())
        assert row_res.is_ok()
        assert row_res.get_ok().content == "apple"

        # Reinsert same texts must be idempotent
        r2 = await self.store.insert_strings(texts)
        if r2.is_error():
            logger.error(r2.get_error())
        assert r2.is_ok()

        ids_res2 = await self.store.get_all_ids()
        assert ids_res2.is_ok()
        assert len(ids_res2.get_ok()) == 2

    async def test_migration(self):
        texts = ["apple", "banana"]
        r = await self.store.insert_strings(texts)
        if r.is_error():
            logger.error(r.get_error())
        assert r.is_ok()

        apple_hash = compute_mdhash_id("apple")
        r = await self.store.move_all_ids_to_new_collection(
            hash_ids=[apple_hash], collection="tmp"
        )
        if r.is_error():
            logger.error(r.get_error())
        assert r.is_ok()

        ids_res = await self.store.get_all_id_to_rows("tmp")
        if ids_res.is_error():
            logger.error(ids_res.get_error())
        assert ids_res.is_ok()
        ids = ids_res.get_ok()
        assert len(ids) == 1

        r = await self.store.delete_store(self.store._config.collection)  # type: ignore
        assert r.is_error()
        r = await self.store.delete_store("tmp")
        if r.is_error():
            logger.error(r.get_error())
        assert r.is_ok()

    async def test_missing_and_delete(self):
        texts = ["alpha", "beta"]
        assert (await self.store.insert_strings(texts)).is_ok()

        miss = await self.store.get_missing_string_hash_ids(["alpha", "gamma"])
        if miss.is_error():
            logger.error(miss.get_error())
        assert miss.is_ok()
        missing = miss.get_ok()
        assert len(missing) == 1
        assert next(iter(missing.values())).content == "gamma"

        # delete one
        hid_alpha = await self._hash("alpha")
        del_res = await self.store.delete([hid_alpha])
        if del_res.is_error():
            logger.error(del_res.get_error())
        assert del_res.is_ok()

        ids_res = await self.store.get_all_ids()
        assert ids_res.is_ok()
        assert len(ids_res.get_ok()) == 1

        names_res = await self.store.get_all_texts()
        assert names_res.is_ok()
        assert names_res.get_ok() == {"beta"}

    async def test_get_rows_and_all_id_to_rows(self):
        texts = ["cat", "cater", "dog"]
        assert (await self.store.insert_strings(texts)).is_ok()

        hid_cat = await self._hash("cat")
        hid_dog = await self._hash("dog")
        rows = await self.store.get_rows([hid_cat, hid_dog])
        if rows.is_error():
            logger.error(rows.get_error())
        assert rows.is_ok()
        d = rows.get_ok()
        assert d[hid_cat].content == "cat"
        assert d[hid_dog].content == "dog"

        all_map_res = await self.store.get_all_id_to_rows()
        assert all_map_res.is_ok()
        all_map = all_map_res.get_ok()
        assert {r.content for r in all_map.values()} == set(texts)

    async def test_query(self):
        texts = ["aaaa", "aaab", "xxxxxxxx"]
        assert (await self.store.insert_strings(texts)).is_ok()

        qres = await self.store.query("aaaa")
        if qres.is_error():
            logger.error(qres.get_error())
        assert qres.is_ok()
        hits = qres.get_ok()
        assert len(hits) >= 1

        top_id = hits[0].id
        hid = await self._hash("aaaa")
        assert top_id == hid

    async def test_query_test(self):
        texts = [
            "Jörg Sahm teaches at fachhochschule",
            "Jörg Sahm Unterrichtet an der Fachhochschule",
            "Jörg Sahm Dozent an der Fachhochschule",
        ]
        assert (await self.store.insert_strings(texts)).is_ok()

        qres = await self.store.query("Dozent")
        if qres.is_error():
            logger.error(qres.get_error())
        assert qres.is_ok()
        hits = qres.get_ok()
        logger.error("Dozent")
        for hit in hits:
            logger.error(f"{hit.payload} : {hit.score}")

        qres = await self.store.query("Unterrichtet")
        if qres.is_error():
            logger.error(qres.get_error())
        assert qres.is_ok()
        hits = qres.get_ok()
        logger.error("Unterrichtet")
        for hit in hits:
            logger.error(f"{hit.payload} : {hit.score}")

        qres = await self.store.query("teaches")
        if qres.is_error():
            logger.error(qres.get_error())
        assert qres.is_ok()
        hits = qres.get_ok()
        logger.error("teaches")
        for hit in hits:
            logger.error(f"{hit.payload} : {hit.score}")

    async def test_knn_by_ids(self):
        texts = ["aaaa", "aaab", "bbb", "xxxxxxxx"]
        assert (await self.store.insert_strings(texts)).is_ok()

        qid = await self._hash("aaaa")
        knn = await self.store.knn_by_ids(
            [qid],
            top_k=3,
            min_similarity=0.0,
        )
        if knn.is_error():
            logger.error(knn.get_error())
        assert knn.is_ok()
        res = knn.get_ok()
        assert qid in res

        nodes = res[qid]
        # Should not include itself
        assert qid not in [node.id for node in nodes]
        # Should return up to 3 neighbors
        assert len(nodes) <= 3

        # Sanity-check presence of expected neighbors via reverse lookup
        ids_text: set[str] = set()
        for node in nodes:
            r = await self.store.get_row(node.id)
            assert r.is_ok()
            ids_text.add(r.get_ok().content)
        logger.error(ids_text)
        assert {"aaab", "bbb"}.issubset(ids_text)

        qid = await self._hash("aaaa")
        knn = await self.store.knn_by_ids(
            [qid],
            allowd__point_ids=[compute_mdhash_id("aaab"), compute_mdhash_id("bbb")],
            top_k=3,
            min_similarity=0.0,
        )
        if knn.is_error():
            logger.error(knn.get_error())
        assert knn.is_ok()
        res = knn.get_ok()
        assert qid in res

        nodes = res[qid]
        assert qid not in [node.id for node in nodes]
        assert len(nodes) <= 2
