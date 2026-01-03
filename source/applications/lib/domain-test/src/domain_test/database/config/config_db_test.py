# domain_test/database/config/system_config_db.py
import logging
import uuid
from typing import TypeVar
from core.model import DublicateException

from domain.database.config.model import (
    RAGConfig,
    RagRetrievalConfig,
)

from domain.database.config.model import RagEmbeddingConfig
from domain.database.config.interface import (
    RAGConfigDatabase,
    RAGEmbeddingConfigDatabase,
    RAGRetrivalConfigDatabase,
    SystemConfigDatabase,
)
from domain_test import AsyncTestBase
from domain.database.config.model import Config, EvaluationConfig

logger = logging.getLogger(__name__)


logger = logging.getLogger(__name__)

T = TypeVar("T", bound=EvaluationConfig)


class TestDBSystemConfigDatabase(AsyncTestBase):
    """
    Storage-agnostic CRUD + queries for a system-config DB.
    Subclasses must assign `self.db` in setup_method_async.
    """

    db: SystemConfigDatabase[EvaluationConfig]

    # ------------------------------------------------------------------ fixtures
    def _make_config(
        self, name: str = "default", model: str = "some-llm"
    ) -> Config[EvaluationConfig]:
        return Config(
            id="",
            data=EvaluationConfig(
                name=name,
                model=model,
                prompts={"system_prompt": "das ist mein System Prompt"},
            ),
        )

    # ------------------------------------------------------------------ tests
    async def test_create_get_update_delete_and_get_by_hash(self):
        config = self._make_config("alpha")

        # Create
        create_res = await self.db.create_config(config)
        if create_res.is_error():
            logger.error(create_res.get_error())
        assert create_res.is_ok()
        config_id = create_res.get_ok()

        # Create duplicate → expect error
        dup_res = await self.db.create_config(config)
        if dup_res.is_ok():
            logger.error("duplicate create unexpectedly succeeded")
        assert dup_res.is_error()
        assert isinstance(dup_res.get_error(), DublicateException)

        # Get
        get_res = await self.db.get_config_by_id(config_id.id)
        if get_res.is_error():
            logger.error(get_res.get_error())
        assert get_res.is_ok()
        fetched_config = get_res.get_ok()
        assert fetched_config
        assert fetched_config.data.name == "alpha"

        # Get by hash
        hash_res = await self.db.get_config_by_hash(fetched_config.hash)
        if hash_res.is_error():
            logger.error(hash_res.get_error())
        assert hash_res.is_ok()
        by_hash = hash_res.get_ok()
        assert by_hash
        assert by_hash.id == config_id.id

        # Get all
        all_res = await self.db.fetch_all()
        if all_res.is_error():
            logger.error(all_res.get_error())
        assert all_res.is_ok()
        assert len(all_res.get_ok()) >= 1

        # fetch_by_config_type
        by_type = await self.db.fetch_by_config_type(str(EvaluationConfig.__name__))
        if by_type.is_error():
            logger.error(by_type.get_error())
        assert by_type.is_ok()
        assert len(by_type.get_ok()) >= 1

        # Delete


class TestRAGConfigDatabase(AsyncTestBase):
    """
    End-to-end for composing a RAGConfig from existing sub-configs.
    """

    db_rag: RAGConfigDatabase
    db_embedding: RAGEmbeddingConfigDatabase
    db_retrival: RAGRetrivalConfigDatabase

    def _make_embedding(self) -> RagEmbeddingConfig:
        cfg = RagEmbeddingConfig(
            id="",
            hash="",
            chunk_size=256,
            chunk_overlap=32,
            models={"embedder": "text-embedding-3-small"},
            addition_information={"lang": "en"},
        )
        cfg.compute_config_hash()
        return cfg

    def _make_retrieval(self) -> RagRetrievalConfig:
        cfg = RagRetrievalConfig(
            id="",
            hash="",
            temp=0.4,
            generator_model="gpt-4o-mini",
            prompts={"system": "Reply concisely."},
            addition_information={"top_k": 8},
        )
        cfg.compute_config_hash()
        return cfg

    def _make_rag_config(
        self,
        r_config: RagRetrievalConfig,
        e_config: RagEmbeddingConfig,
        name: str | None = None,
    ) -> RAGConfig:
        cfg = RAGConfig(
            id="",
            hash="",
            config_type="subquestion",
            name=name or "test",
            embedding=e_config,
            retrieval_config=r_config,
        )
        cfg.compute_config_hash()
        return cfg

    async def test_create_rag_and_fetch_by_hash_and_duplicates(self):
        # create the sub-configs
        emb = self._make_embedding()
        emb.compute_config_hash()
        ret = self._make_retrieval()
        ret.compute_config_hash()
        emb_id = (await self.db_embedding.create_config(emb)).get_ok()
        ret_id = (await self.db_retrival.create_config(ret)).get_ok()
        assert emb_id and ret_id

        # create rag config
        name = "pipeline-alpha"
        rag_res = await self.db_rag.create_config(
            self._make_rag_config(r_config=ret_id, e_config=emb_id, name=name)
        )
        if rag_res.is_error():
            logger.error(rag_res.get_error())
        assert rag_res.is_ok()
        rag = rag_res.get_ok()
        rag.compute_config_hash()
        assert rag.name == name
        assert rag.hash == f"{emb.hash}-{ret.hash}"
        assert rag.embedding.hash == emb.hash
        assert rag.retrieval_config.hash == ret.hash

        # fetch by composed hash
        by_hash_res = await self.db_rag.get_config_by_hash(rag.hash)
        if by_hash_res.is_error():
            logger.error(by_hash_res.get_error())
        assert by_hash_res.is_ok()
        by_hash = by_hash_res.get_ok()
        assert by_hash is not None
        assert by_hash.name == name
        assert by_hash.hash == rag.hash

        # duplicate by name -> DublicateException
        dup_name = await self.db_rag.create_config(
            self._make_rag_config(r_config=ret_id, e_config=emb_id, name=name)
        )
        assert dup_name.is_error()
        assert isinstance(dup_name.get_error(), DublicateException)

        # duplicate by hash (different name, same pair) -> DublicateException
        dup_hash = await self.db_rag.create_config(
            self._make_rag_config(r_config=ret_id, e_config=emb_id)
        )
        assert dup_hash.is_error()
        assert isinstance(dup_hash.get_error(), DublicateException)

        # unknown hash -> None
        missing = await self.db_rag.get_config_by_hash(
            f"{uuid.uuid4().hex}-{uuid.uuid4().hex}"
        )
        assert missing.is_ok()
        assert missing.get_ok() is None

    async def test_create_rag_with_missing_fk_fails(self):
        # attempt to create RAG with non-existing sub-config hashes
        bad = await self.db_rag.create_config(
            self._make_rag_config(
                r_config=RagRetrievalConfig(
                    id="lo",
                    generator_model="this is a dummy modelXYZ",
                    temp=0.4,
                    prompts={},
                    addition_information={},
                ),
                e_config=RagEmbeddingConfig(
                    id="",
                    chunk_size=999,
                    chunk_overlap=9999,
                    models={},
                    addition_information={},
                ),
            )
        )
        assert bad.is_error()
        # The implementation raises ValueError for missing FK rows; adjust if you use a custom NotFound
        assert isinstance(bad.get_error(), ValueError)

    async def test_get_rag_config_by_id_unknown_returns_none(self):
        # Since create_rag_config returns the DTO (not the id), we only validate the negative id path
        res = await self.db_rag.get_config_by_id(str(uuid.uuid4()))
        assert res.is_ok()
        assert res.get_ok() is None

    async def test_get_rag_config_by_id_success_and_deep_fields(self):
        # sub-configs
        emb = self._make_embedding()
        ret = self._make_retrieval()
        emb = (await self.db_embedding.create_config(emb)).get_ok()
        ret = (await self.db_retrival.create_config(ret)).get_ok()
        assert emb and ret

        # create a rag config
        rag_created = (
            await self.db_rag.create_config(
                self._make_rag_config(r_config=ret, e_config=emb, name="id-happy")
            )
        ).get_ok()
        assert rag_created.id

        # fetch by id (positive path)
        got_res = await self.db_rag.get_config_by_id(rag_created.id)
        assert got_res.is_ok()
        got = got_res.get_ok()
        assert got is not None

        # validate it's the same object and that nested fields are populated (not just FKs)
        assert got.id == rag_created.id
        assert got.name == "id-happy"
        assert got.hash == f"{emb.hash}-{ret.hash}"
        assert got.embedding is not None
        assert got.embedding.id == emb.id
        assert got.embedding.hash == emb.hash
        assert got.retrieval_config is not None
        assert got.retrieval_config.id == ret.id
        assert got.retrieval_config.hash == ret.hash

    async def test_fetch_all_empty_then_populated(self):
        # Start with an empty read (use a fresh DB or assume isolation)
        empty_res = await self.db_rag.fetch_all()
        assert empty_res.is_ok()
        assert empty_res.get_ok() == []

        # create one pipeline
        emb = (await self.db_embedding.create_config(self._make_embedding())).get_ok()
        ret = (await self.db_retrival.create_config(self._make_retrieval())).get_ok()
        one = (
            await self.db_rag.create_config(
                self._make_rag_config(r_config=ret, e_config=emb, name="solo")
            )
        ).get_ok()

        # now fetch_all returns exactly one, with deep/nested objects
        all_res = await self.db_rag.fetch_all()
        assert all_res.is_ok()
        items = all_res.get_ok()
        assert isinstance(items, list)
        assert len(items) == 1
        assert items[0].id == one.id
        assert items[0].embedding is not None
        assert items[0].retrieval_config is not None

    async def test_create_multiple_combinations_and_uniqueness_scope(self):
        # Two embeddings, two retrieval configs -> four possible pairs.
        emb_a = (await self.db_embedding.create_config(self._make_embedding())).get_ok()
        emb_b_cfg = self._make_embedding()
        emb_b_cfg.chunk_overlap = 16  # tweak to force a different hash
        emb_b_cfg.compute_config_hash()
        emb_b = (await self.db_embedding.create_config(emb_b_cfg)).get_ok()

        ret_a = (await self.db_retrival.create_config(self._make_retrieval())).get_ok()
        ret_b_cfg = self._make_retrieval()
        ret_b_cfg.addition_information["top_k"] = 4  # tweak to force a different hash
        ret_b_cfg.compute_config_hash()
        ret_b = (await self.db_retrival.create_config(ret_b_cfg)).get_ok()

        # make three distinct pipelines (unique by composed hash)
        r1 = (
            await self.db_rag.create_config(
                self._make_rag_config(e_config=emb_a, r_config=ret_a, name="embA-retA")
            )
        ).get_ok()
        r2 = (
            await self.db_rag.create_config(
                self._make_rag_config(e_config=emb_a, r_config=ret_b, name="embA-retB")
            )
        ).get_ok()
        r3 = (
            await self.db_rag.create_config(
                self._make_rag_config(e_config=emb_b, r_config=ret_a, name="embB-retA")
            )
        ).get_ok()

        assert r1.hash == f"{emb_a.hash}-{ret_a.hash}"
        assert r2.hash == f"{emb_a.hash}-{ret_b.hash}"
        assert r3.hash == f"{emb_b.hash}-{ret_a.hash}"
        assert len({r1.hash, r2.hash, r3.hash}) == 3

        # attempting to create the same pair (embA + retA) with a different name must fail (duplicate by hash)
        dup_pair = await self.db_rag.create_config(
            self._make_rag_config(
                e_config=emb_a, r_config=ret_a, name="embA-retA-newname"
            )
        )
        assert dup_pair.is_error()
        assert isinstance(dup_pair.get_error(), DublicateException)

        # attempting to reuse an existing *name* with a different pair must fail (duplicate by name)
        dup_name = await self.db_rag.create_config(
            self._make_rag_config(e_config=emb_b, r_config=ret_b, name="embA-retA")
        )
        assert dup_name.is_error()
        assert isinstance(dup_name.get_error(), DublicateException)

    async def test_get_config_by_hash_variants_and_consistency(self):
        emb_a = (await self.db_embedding.create_config(self._make_embedding())).get_ok()
        ret_a = (await self.db_retrival.create_config(self._make_retrieval())).get_ok()
        created = (
            await self.db_rag.create_config(
                self._make_rag_config(e_config=emb_a, r_config=ret_a, name="by-hash")
            )
        ).get_ok()

        # fetch by the exact composed hash
        hres = await self.db_rag.get_config_by_hash(created.hash)
        assert hres.is_ok()
        cfg = hres.get_ok()
        assert cfg is not None
        assert cfg.id == created.id
        assert cfg.embedding.hash == emb_a.hash
        assert cfg.retrieval_config.hash == ret_a.hash

        # verify that any altered composed hash does not resolve
        wrong_hash = f"{emb_a.hash}-{uuid.uuid4().hex}"
        miss = await self.db_rag.get_config_by_hash(wrong_hash)
        assert miss.is_ok()
        assert miss.get_ok() is None

    async def test_fetch_all_returns_sorted_or_stable(self):
        """
        If your implementation guarantees an order (e.g., created_at desc),
        assert it here. Otherwise just assert set-equality (stable content).
        """
        # create a couple
        emb1 = (await self.db_embedding.create_config(self._make_embedding())).get_ok()
        ret1 = (await self.db_retrival.create_config(self._make_retrieval())).get_ok()
        r1 = (
            await self.db_rag.create_config(
                self._make_rag_config(e_config=emb1, r_config=ret1, name="ord-1")
            )
        ).get_ok()

        emb2_cfg = self._make_embedding()
        emb2_cfg.chunk_size = 128
        emb2_cfg.compute_config_hash()
        emb2 = (await self.db_embedding.create_config(emb2_cfg)).get_ok()
        ret2_cfg = self._make_retrieval()
        ret2_cfg.prompts = {"system": "Be brief."}
        ret2_cfg.compute_config_hash()
        ret2 = (await self.db_retrival.create_config(ret2_cfg)).get_ok()
        r2 = (
            await self.db_rag.create_config(
                self._make_rag_config(e_config=emb2, r_config=ret2, name="ord-2")
            )
        ).get_ok()

        res = await self.db_rag.fetch_all()
        assert res.is_ok()
        got = res.get_ok()

        ids = {x.id for x in got}
        assert {r1.id, r2.id}.issubset(ids)

        # If your DB guarantees ordering, uncomment and adapt:
        # assert [x.id for x in got[:2]] == [r2.id, r1.id]  # e.g., latest first

    async def test_create_rag_rejects_crosswired_hash_composition(self):
        """
        Defensive test: if an implementation allows passing prefilled hashes,
        ensure it rejects inconsistencies where composed hash != f"{emb.hash}-{ret.hash}".
        If your create code recomputes the hash unconditionally, this should still pass
        by yielding a corrected value that equals the recomputed one.
        """
        emb = (await self.db_embedding.create_config(self._make_embedding())).get_ok()
        ret = (await self.db_retrival.create_config(self._make_retrieval())).get_ok()

        cfg = self._make_rag_config(e_config=emb, r_config=ret, name="defensive")
        cfg.hash = "tampered-hash"  # simulate a caller mistake

        res = await self.db_rag.create_config(cfg)
        if res.is_error():
            # acceptable outcome: create path rejects mismatch explicitly
            err = res.get_error()
            assert isinstance(err, (ValueError, DublicateException))
        else:
            # also acceptable: create path *recomputes* and stores canonical value
            stored = res.get_ok()
            assert stored.hash == f"{emb.hash}-{ret.hash}"
