from typing import Protocol, runtime_checkable
from core.result import Result


@runtime_checkable
class FactStore(Protocol):
    """
    Fact Store Interface.
    Should be used to chash fact extraction of chunks
    """
    async def get_facts_to_hash(self, hash: str) -> Result[list[str] | None]: ...
    async def store_facts(self, hash: str, facts: list[str]) -> Result[None]: ...
