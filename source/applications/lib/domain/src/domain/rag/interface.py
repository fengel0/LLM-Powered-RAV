from typing import Protocol, runtime_checkable

from core.result import Result

from domain.rag.model import Conversation, RAGResponse


@runtime_checkable
class RAGLLM(Protocol):
    """
    Asynchronous protocol representing a Large Language Model (LLM) used for Retrieval‑Augmented
    Generation (RAG).

    Implementations expose a single asynchronous ``request`` method that accepts a
    :class:`~domain.rag.model.Conversation` and optional metadata filters or a collection
    identifier.  The method returns a :class:`core.result.Result` wrapping a
    :class:`~domain.rag.model.RAGResponse`.  The protocol deliberately stays
    implementation‑agnostic – it does not prescribe a particular LLM vendor, model, or
    service (e.g., OpenAI, Cohere, custom hosted model).  Instead, it defines the *behaviour* required
    by the rest of the system:

    * ``request`` – given a conversation history, optionally filter the context with
      ``metadata_filters`` and/or ``collection``, perform a generation step and return the
      structured RAG response.
    """
    async def request(
        self,
        conversation: Conversation,
        metadata_filters: dict[str, list[str] | list[int] | list[float]] | None = None,
        collection: str | None = None,
    ) -> Result[RAGResponse]: ...
