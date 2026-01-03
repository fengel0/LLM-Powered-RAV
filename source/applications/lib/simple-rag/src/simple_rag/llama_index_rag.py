import logging

from core.result import Result
from domain.rag.interface import RAGLLM, Conversation
from domain.rag.model import (
    Message,
    Node,
    RAGResponse,
)
from llama_index.core.base.llms.types import ChatMessage, MessageRole
from llama_index_extension.simple_builder import LlamaIndexSimpleBuilder
from llama_index_extension.sub_question_builder import LlamaIndexSubQuestionBuilder
from opentelemetry import trace

logger = logging.getLogger(__name__)


class LlamaIndexSubRAG(RAGLLM):
    _chat_builder: LlamaIndexSubQuestionBuilder

    def __init__(self, chat_builder: LlamaIndexSubQuestionBuilder):
        self.tracer = trace.get_tracer("LlamaIndexSubRAG")
        self._chat_builder = chat_builder

    def __convert_to_chat_history(self, messages: list[Message]) -> list[ChatMessage]:
        return [
            ChatMessage(role=MessageRole(message.role.value), content=message.message)
            for message in messages
        ]

    async def request(
        self,
        conversation: Conversation,
        metadata_filters: dict[str, list[str] | list[int] | list[float]] | None = None,
        collection: str | None = None,
    ) -> Result[RAGResponse]:
        if metadata_filters is None:
            metadata_filters = {}
        with self.tracer.start_as_current_span("sub-rag-query"):
            chat_engine = self._chat_builder.get_decompose_engine(
                model=conversation.model,
                metadata_filters=metadata_filters,
                collection=collection,
            )
            messages = conversation.messages
            last_message = messages[len(messages) - 1]
            messages.remove(last_message)
            chat_history = self.__convert_to_chat_history(messages)

            try:
                response = chat_engine.stream_chat(
                    last_message.message, chat_history=chat_history
                )

                nodes = [
                    Node(
                        id=node.id_,
                        content=node.text,
                        metadata=node.metadata,
                        similarity=node.get_score(raise_error=False),
                    )
                    for node in response.source_nodes
                ]

                logger.debug(f"found nodes {[node.id for node in nodes]}")

                async def async_wrap_blocking():
                    for item in response.response_gen:
                        yield item

                return Result.Ok(
                    RAGResponse.create_stream_response(
                        generator=async_wrap_blocking(),
                        nodes=nodes,
                    )
                )
            except Exception as e:
                logger.error(e, exc_info=True)
                return Result.Err(Exception(f"failed to retrive answer from llm {e}"))


class LlamaIndexRAG(RAGLLM):
    """
    implementation of the VectorDatabase interface using LlamaIndex."""

    chat_builder: LlamaIndexSimpleBuilder

    def __init__(self, chat_builder: LlamaIndexSimpleBuilder):
        self.tracer = trace.get_tracer("LlamaIndexRAG")
        self.chat_builder = chat_builder

    async def request(
        self,
        conversation: Conversation,
        metadata_filters: dict[str, list[str] | list[int] | list[float]] | None = None,
        collection: str | None = None,
    ) -> Result[RAGResponse]:
        with self.tracer.start_as_current_span("rag-query"):
            chat_engine = self.chat_builder.get_chat_enging(
                model=conversation.model,
                metadata_filters=metadata_filters,
                collection=collection,
            )
            messages = conversation.messages
            last_message = messages[len(messages) - 1]
            messages.remove(last_message)
            chat_history = self.__convert_to_chat_history(messages)

            try:
                response = chat_engine.stream_chat(
                    last_message.message, chat_history=chat_history
                )

                nodes = [
                    Node(
                        id=node.id_,
                        content=node.text,
                        metadata=node.metadata,
                        similarity=node.get_score(raise_error=False),
                    )
                    for node in response.source_nodes
                ]

                logger.debug(f"found nodes {[node.id for node in nodes]}")

                async def async_wrap_blocking():
                    for item in response.response_gen:
                        yield item

                return Result.Ok(
                    RAGResponse.create_stream_response(
                        generator=async_wrap_blocking(),
                        nodes=nodes,
                    )
                )
            except Exception as e:
                logger.error(e, exc_info=True)
                return Result.Err(Exception(f"failed to retrive answer from llm {e}"))

    def __convert_to_chat_history(self, messages: list[Message]) -> list[ChatMessage]:
        return [
            ChatMessage(role=MessageRole(message.role.value), content=message.message)
            for message in messages
        ]
