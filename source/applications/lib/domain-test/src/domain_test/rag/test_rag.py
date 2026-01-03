# domain_test/rag/rag_queries.py
import logging
import time

from domain.rag.interface import RAGLLM
from domain_test import AsyncTestBase
from domain.rag.model import Conversation, Message, RoleType

logger = logging.getLogger(__name__)


class TestDBRAGQueries(AsyncTestBase):
    """
    Storage/stack-agnostic RAG flow tests.
    Harness must:
      - initialize LLamaIndexHolder & vector session
      - seed at least 2 nodes (metadata other=lol,count=5 recommended)
      - optionally set `self.model`
    """

    model: str = ""
    rag_llm: RAGLLM

    async def test_run_a_sub_query(self):
        start_time = time.perf_counter()
        response_result = await self.rag_llm.request(
            conversation=Conversation(
                messages=[Message(message="Was mag ich?", role=RoleType.Assistent)],
                model=self.model,
            ),
            # metadata_filters={"other": ["lol"]},
        )
        if response_result.is_error():
            logger.error(response_result.get_error())
        assert response_result.is_ok()

        response = response_result.get_ok()

        generated_tokens = 0
        logger.info("generation start")
        start_time_generation = time.perf_counter()
        async for token in response.generator:
            logger.info(token)
            generated_tokens += 1

        generation_ms = (time.perf_counter() - start_time_generation) * 1_000
        total_ms = (time.perf_counter() - start_time) * 1_000
        logger.info(f"total {total_ms:.2f} ms")
        logger.info(f"generation {generation_ms:.2f} ms")
        logger.info(f"difference {total_ms - generation_ms:.2f} ms")
        logger.info(response.message)
        logger.info(response.nodes)

        assert len(response.nodes) > 0
        assert response.generator is not None

        assert generated_tokens > 0
