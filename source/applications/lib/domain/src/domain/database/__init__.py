from typing import Generic, Protocol, TypeVar, runtime_checkable

from core.result import Result
from pydantic import BaseModel


T = TypeVar("T", bound=BaseModel)


@runtime_checkable
class BaseDatabase(Protocol, Generic[T]):

    """
    Base Database interface.
    defines CRUD Operation for all Database Models
    """

    async def create(self, obj: T) -> Result[str]: ...

    async def update(self, obj: T) -> Result[None]: ...

    async def delete(self, id: str) -> Result[None]: ...

    async def get(self, id: str) -> Result[T | None]: ...

    async def get_all(self) -> Result[list[T]]: ...
