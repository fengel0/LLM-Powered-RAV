from typing import Protocol, runtime_checkable
from core.result import Result

from domain.rag.indexer.model import Document, SplitNode
from domain.rag.model import Node


@runtime_checkable
class DocumentSplitter(Protocol):
    def split_documents(self, doc: Document) -> list[SplitNode]: ...


@runtime_checkable
class AsyncDocumentIndexer(Protocol):
    """
    Asynchronous protocol defining the required behaviour of a document indexer.

    Implementations provide a storage‑agnostic interface for indexing and
    retrieving documents for RAG Application.  The protocol is deliberately
    generic –

    * ``create_document`` – add a new :class:`~domain.rag.indexer.model.Document`
      to a collection.
    * ``update_document`` – modify an existing document.
    * ``delete_document`` – remove a document by its identifier.
    * ``find_similar_nodes`` – perform a similarity search based on a query
      string and optional metadata, returning a list of :class:`~domain.rag.indexer.model.Node`.
    * ``does_object_with_metadata_exist`` – check whether an object matching the
      given metadata exists in the store.

    All methods are asynchronous and return a :class:`core.result.Result`
    wrapper, allowing callers to handle success or failure uniformly without
    raising exceptions.
    """

    async def create_document(
        self, doc: Document, collection: str | None = None
    ) -> Result[None]: ...

    async def update_document(
        self, doc: Document, collection: str | None = None
    ) -> Result[None]: ...

    async def delete_document(
        self, doc_id: str, collection: str | None = None
    ) -> Result[None]: ...

    async def find_similar_nodes(
        self,
        query: str,
        metadata: dict[str, list[str] | list[int] | list[float]] | None = None,
        collection: str | None = None,
    ) -> Result[list[Node]]: ...

    async def does_object_with_metadata_exist(
        self, metadata: dict[str, str | int | float], collection: str | None = None
    ) -> Result[bool]: ...
