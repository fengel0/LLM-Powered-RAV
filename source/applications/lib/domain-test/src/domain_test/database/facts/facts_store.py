import logging
from core.logger import init_logging
from domain.database.facts.interface import FactStore
from domain_test import AsyncTestBase

init_logging("info")
logger = logging.getLogger(__name__)


class TestDBFactsStore(AsyncTestBase):
    state_store: FactStore

    # ------------------------------------------------------------------ tests
    async def test_get_facts_to_hash_returns_empty_when_missing(self):
        result = await self.state_store.get_facts_to_hash("missing-hash")
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()
        assert result.get_ok() is None

    async def test_store_and_get_facts_roundtrip(self):
        h = "doc-hash-1"
        facts = ["a -> b", "b -> c", "c -> d"]

        store = await self.state_store.store_facts(h, facts)
        if store.is_error():
            logger.error(store.get_error())
        assert store.is_ok()

        fetched = await self.state_store.get_facts_to_hash(h)
        if fetched.is_error():
            logger.error(fetched.get_error())
        assert fetched.is_ok()
        assert fetched.get_ok() == facts

    async def test_store_empty_facts_list(self):
        h = "empty-facts-hash"

        store = await self.state_store.store_facts(h, [])
        if store.is_error():
            logger.error(store.get_error())
        assert store.is_ok()

        fetched = await self.state_store.get_facts_to_hash(h)
        if fetched.is_error():
            logger.error(fetched.get_error())
        assert fetched.is_ok()
        assert fetched.get_ok() == []

    async def test_multiple_hashes_are_isolated(self):
        h1 = "hash-1"
        h2 = "hash-2"
        facts1 = ["x -> y", "y -> z"]
        facts2 = ["p -> q"]

        r1 = await self.state_store.store_facts(h1, facts1)
        if r1.is_error():
            logger.error(r1.get_error())
        assert r1.is_ok()

        r2 = await self.state_store.store_facts(h2, facts2)
        if r2.is_error():
            logger.error(r2.get_error())
        assert r2.is_ok()

        f1 = await self.state_store.get_facts_to_hash(h1)
        if f1.is_error():
            logger.error(f1.get_error())
        assert f1.is_ok()
        assert f1.get_ok() == facts1

        f2 = await self.state_store.get_facts_to_hash(h2)
        if f2.is_error():
            logger.error(f2.get_error())
        assert f2.is_ok()
        assert f2.get_ok() == facts2

        f3 = await self.state_store.get_facts_to_hash("unknown-hash")
        if f3.is_error():
            logger.error(f3.get_error())
        assert f3.is_ok()
        assert f3.get_ok() is None

    async def test_store_then_overwrite_behavior_documented(self):
        h = "dup-hash"

        first = await self.state_store.store_facts(h, ["a"])
        if first.is_error():
            logger.error(first.get_error())
        assert first.is_ok()

        second = await self.state_store.store_facts(h, ["b"])
        if second.is_error():
            logger.error(second.get_error())

        if second.is_ok():
            # Upsert semantics: verify latest value is visible.
            fetched = await self.state_store.get_facts_to_hash(h)
            if fetched.is_error():
                logger.error(fetched.get_error())
            assert fetched.is_ok()
            assert fetched.get_ok() == ["b"]
        else:
            # Insert-only semantics: verify original value remains.
            fetched = await self.state_store.get_facts_to_hash(h)
            if fetched.is_error():
                logger.error(fetched.get_error())
            assert fetched.is_ok()
            assert fetched.get_ok() == ["a"]
