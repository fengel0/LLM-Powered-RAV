from __future__ import annotations

import logging

from opentelemetry import trace

from core.result import Result
from database.session import BaseDatabase


from domain.database.facts.interface import FactStore
from fact_store_database.model import Facts

logger = logging.getLogger(__name__)


class _InternPostgresDBFacts(BaseDatabase[Facts]):
    def __init__(self):
        super().__init__(Facts)


class PostgresDBFactStore(FactStore):
    tracer: trace.Tracer
    _db_facts: _InternPostgresDBFacts

    def __init__(self) -> None:
        self._db_facts = _InternPostgresDBFacts()
        self.tracer = trace.get_tracer("StateStore")

    async def get_facts_to_hash(self, hash: str) -> Result[list[str] | None]:
        with self.tracer.start_as_current_span("fetch-facts"):
            try:
                q = {"hash": hash}
                result = await self._db_facts.run_query_first(query=q)
                if result.is_error():
                    return result.propagate_exception()
                facts_optional = result.get_ok()
                if facts_optional is None:
                    return Result.Ok(None)
                return Result.Ok(facts_optional.facts)
            except Exception as e:
                logger.error(e, exc_info=True)
                return Result.Err(e)

    async def store_facts(self, hash: str, facts: list[str]) -> Result[None]:
        with self.tracer.start_as_current_span("store-facts"):
            try:
                result = await self._db_facts.create(Facts(hash=hash, facts=facts))
                if result.is_error():
                    return result.propagate_exception()
                return Result.Ok()
            except Exception as e:
                logger.error(e, exc_info=True)
                return Result.Err(e)
