import asyncio
import logging
from typing import List, Optional

from llama_index.core.instrumentation import get_dispatcher
from llama_index.core.callbacks import CBEventType, EventPayload
from domain.text_embedding.interface import AsyncRerankerClient, RerankerClient
from domain.text_embedding.model import RerankRequestDto, RerankResponseElement
from llama_index.core import QueryBundle
from llama_index.core.postprocessor.types import BaseNodePostprocessor
from llama_index.core.schema import MetadataMode, NodeWithScore
from pydantic import Field, PrivateAttr
from llama_index.core.instrumentation.events.rerank import (
    ReRankEndEvent,
    ReRankStartEvent,
)


logger = logging.getLogger(__name__)

dispatcher = get_dispatcher(__name__)


class CustomRerankerClient(BaseNodePostprocessor):
    """Custom reranker client for reranking nodes."""

    top_n: int = Field(description="Number of nodes to return sorted by score.")
    _client: Optional[RerankerClient] = PrivateAttr()
    _aclient: Optional[AsyncRerankerClient] = PrivateAttr()

    def __init__(
        self,
        client: RerankerClient | None = None,
        async_client: AsyncRerankerClient | None = None,
        top_n: int = 5,
    ):
        assert client or async_client, "Provide either client or async_client"
        super().__init__(top_n=top_n)
        self._client = client
        self._aclient = async_client

    @classmethod
    def class_name(cls) -> str:
        return "CustomRerankerClient"

    # ---------- utilities ----------

    @staticmethod
    def _run_coro_sync(coro):
        """Run an async coroutine from a sync context safely."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # Running inside an event loop (rare for sync path); create a new loop in a thread
            import threading

            result_container = {}

            def _runner():
                new_loop = asyncio.new_event_loop()
                try:
                    asyncio.set_event_loop(new_loop)
                    result_container["value"] = new_loop.run_until_complete(coro)
                finally:
                    new_loop.close()

            t = threading.Thread(target=_runner, daemon=True)
            t.start()
            t.join()
            return result_container["value"]
        else:
            # No loop running: safe to create/run one here
            return asyncio.run(coro)

    @staticmethod
    def _extract_texts(nodes: list[NodeWithScore]) -> list[str]:
        return [
            str(node.node.get_content(metadata_mode=MetadataMode.EMBED))
            for node in nodes
        ]

    @staticmethod
    def _apply_rerank_result(
        nodes: List[NodeWithScore], reranks: list[RerankResponseElement]
    ):
        for rank in reranks:
            nodes[rank.index].metadata["retrieval_score"] = nodes[rank.index].score
            nodes[rank.index].score = rank.score
        nodes.sort(key=lambda x: float(x.score or 0), reverse=True)
        return nodes

    # ---------- core calls ----------

    async def _acalculate_sim(
        self, query: str, nodes: List[NodeWithScore]
    ) -> List[NodeWithScore]:
        if not self._aclient:
            raise Exception("No Async implementation")
        result = await self._aclient.rerank(
            request=RerankRequestDto(
                query=query,
                texts=self._extract_texts(nodes),
                raw_scores=True,
                return_text=False,
                truncate=True,
                truncation_direction="right",
            )
        )
        if result.is_error():
            logger.error(result.get_error(), exc_info=True)
            raise result.get_error()
        reranks = result.get_ok().root
        return self._apply_rerank_result(nodes, reranks)

    def _calculate_sim(
        self, query: str, nodes: List[NodeWithScore]
    ) -> List[NodeWithScore]:
        if self._client:
            result = self._client.rerank(
                request=RerankRequestDto(
                    query=query,
                    texts=self._extract_texts(nodes),
                    raw_scores=True,
                    return_text=False,
                    truncate=True,
                    truncation_direction="right",
                )
            )
            if result.is_error():
                logger.error(result.get_error(), exc_info=True)
                raise result.get_error()
            reranks = result.get_ok().root
            return self._apply_rerank_result(nodes, reranks)

        # Fallback: no sync client but async client is available
        if self._aclient:
            return self._run_coro_sync(self._acalculate_sim(query, nodes))

        raise Exception("No available reranker client (sync or async).")

    # ---------- postprocessing (sync/async) ----------

    def _postprocess_nodes(
        self,
        nodes: List[NodeWithScore],
        query_bundle: QueryBundle | None = None,
    ) -> List[NodeWithScore]:
        dispatcher.event(
            ReRankStartEvent(
                query=query_bundle,
                nodes=nodes,
                top_n=self.top_n,
                model_name="custom_reranker",
            )
        )

        if query_bundle is None:
            raise ValueError("Missing query bundle in extra info.")
        if len(nodes) == 0:
            return []

        with self.callback_manager.event(
            CBEventType.RERANKING,
            payload={
                EventPayload.NODES: nodes,
                EventPayload.QUERY_STR: query_bundle.query_str,
                EventPayload.TOP_K: self.top_n,
            },
        ) as event:
            # Prefer sync client; fallback to async client run from sync
            nodes = self._calculate_sim(query_bundle.query_str, nodes)
            reranked_nodes = nodes[: self.top_n]
            event.on_end(payload={EventPayload.NODES: reranked_nodes})

        dispatcher.event(ReRankEndEvent(nodes=reranked_nodes))
        return reranked_nodes

    async def _apostprocess_nodes(
        self,
        nodes: List[NodeWithScore],
        query_bundle: QueryBundle | None = None,
    ) -> List[NodeWithScore]:
        """Postprocess nodes (async)."""
        dispatcher.event(
            ReRankStartEvent(
                query=query_bundle,
                nodes=nodes,
                top_n=self.top_n,
                model_name="custom_reranker",
            )
        )

        if query_bundle is None:
            raise ValueError("Missing query bundle in extra info.")
        if len(nodes) == 0:
            return []

        with self.callback_manager.event(
            CBEventType.RERANKING,
            payload={
                EventPayload.NODES: nodes,
                EventPayload.QUERY_STR: query_bundle.query_str,
                EventPayload.TOP_K: self.top_n,
            },
        ) as event:
            if self._aclient:
                nodes = await self._acalculate_sim(query_bundle.query_str, nodes)
            elif self._client:
                # Fallback: run the sync implementation in a thread so we don't block the loop
                nodes = await asyncio.to_thread(
                    self._calculate_sim, query_bundle.query_str, nodes
                )
            else:
                raise Exception("No available reranker client (sync or async).")

            reranked_nodes = nodes[: self.top_n]
            event.on_end(payload={EventPayload.NODES: reranked_nodes})

        dispatcher.event(ReRankEndEvent(nodes=reranked_nodes))
        return reranked_nodes
