import logging
from domain.text_embedding.interface import EmbeddClient
from llama_index.core.base.embeddings.base import BaseEmbedding, Embedding

from llama_index.core.callbacks import CBEventType, EventPayload
from pydantic import PrivateAttr

logger = logging.getLogger(__name__)


class CustomEmbedding(BaseEmbedding):
    _client: EmbeddClient = PrivateAttr()

    def __init__(self, client: EmbeddClient):
        super().__init__()
        self._client = client

    def _get_query_embedding(self, query: str) -> Embedding:
        """
        Embed the input query synchronously.

        Subclasses should implement this method. Reference get_query_embedding's
        docstring for more information.
        """
        result = self._client.embed_query(query)

        if result.is_error():
            logger.error(result.get_error(), exc_info=True)
            raise result.get_error()
        return result.get_ok().root

    async def _aget_query_embedding(self, query: str) -> Embedding:
        return self._get_query_embedding(query=query)

    async def _aget_text_embedding(self, text: str) -> Embedding:
        return self._get_text_embedding(text)

    def _get_text_embedding(self, text: str) -> Embedding:
        """
        Embed the input text synchronously.

        Subclasses should implement this method. Reference get_text_embedding's
        docstring for more information.
        """
        result = self._client.embed_doc(text)

        self.callback_manager.event(
            CBEventType.EMBEDDING,
            payload={
                EventPayload.QUERY_STR: text,
            },
        )

        if result.is_error():
            logger.error(result.get_error(), exc_info=True)
            raise result.get_error()
        return result.get_ok().root
