from core.result import Result
import logging
from domain.rag.model import Conversation, RAGResponse
from domain.rag.interface import RAGLLM
from opentelemetry import trace


logger = logging.getLogger(__name__)


class SimpleRAGUsecase:
    """
    Simple usecase to run rag-systems in prod
    """
    tracer: trace.Tracer
    rag_llm: RAGLLM

    def __init__(self, rag_llm: RAGLLM):
        logger.info("created SimpleRAG Usecase")
        self.tracer = trace.get_tracer("SimpleRAG Usecase")
        self.rag_llm = rag_llm

    async def request(
        self,
        conversation: Conversation,
        metadata_filters: dict[str, list[str] | list[int] | list[float]] | None = None,
        collection: str | None = None,
    ) -> Result[RAGResponse]:
        with self.tracer.start_as_current_span("simple-rag-request"):
            return await self.rag_llm.request(
                conversation=conversation,
                metadata_filters=metadata_filters,
                collection=collection,
            )
