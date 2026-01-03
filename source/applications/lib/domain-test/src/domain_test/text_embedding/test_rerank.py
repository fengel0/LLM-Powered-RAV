import logging
from domain.text_embedding.interface import AsyncRerankerClient
from domain.text_embedding.model import (
    RerankRequestDto,
    RerankResponseDto,
)
from domain_test import AsyncTestBase

logger = logging.getLogger(__name__)


class TestRerankClientsIntegration(AsyncTestBase):
    rerank_client: AsyncRerankerClient

    async def test_rerank(self):
        request = RerankRequestDto(
            query="What is AI?",
            texts=["Cats are animals", "AI is intelligence", "AI cats"],
            raw_scores=False,
            return_text=True,
            truncate=False,
            truncation_direction="right",
        )
        result = await self.rerank_client.rerank(request)
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()
        response: RerankResponseDto = result.get_ok()
        for node in response:
            logger.error(node)
        assert len(response.root) > 0
        assert isinstance(response.root[0].score, float)
        for index, _ in enumerate(response.root):
            if index == len(response.root) - 1:
                continue
            assert response.root[index].score > response.root[index + 1].score

    async def test_rerank_left(self):
        request = RerankRequestDto(
            query="What is AI?",
            texts=["AI is intelligence", "Cats are animals"],
            raw_scores=False,
            return_text=True,
            truncate=False,
            truncation_direction="left",
        )
        result = await self.rerank_client.rerank(request)
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()
        response: RerankResponseDto = result.get_ok()
        assert len(response.root) > 0
        assert isinstance(response.root[0].score, float)

    async def test_rerank_raw_scores(self):
        request = RerankRequestDto(
            query="What is AI?",
            texts=["AI is intelligence", "Cats are animals"],
            raw_scores=True,
            return_text=True,
            truncate=False,
            truncation_direction="right",
        )
        result = await self.rerank_client.rerank(request)
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()
        response: RerankResponseDto = result.get_ok()
        assert len(response.root) > 0
        assert isinstance(response.root[0].score, float)

    async def test_rerank_no_text_return(self):
        request = RerankRequestDto(
            query="What is AI?",
            texts=["AI is intelligence", "Cats are animals"],
            raw_scores=True,
            return_text=False,
            truncate=False,
            truncation_direction="right",
        )
        result = await self.rerank_client.rerank(request)
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()
        response: RerankResponseDto = result.get_ok()
        assert len(response.root) > 0
        assert isinstance(response.root[0].score, float)

    async def test_rerank_truncate_true(self):
        request = RerankRequestDto(
            query="Define transformers in ML.",
            texts=[
                "Transformers are attention-based models...",
                "Please enjoy this unrelated poem about geese.",
            ],
            raw_scores=False,
            return_text=True,
            truncate=True,
            truncation_direction="right",
        )
        result = await self.rerank_client.rerank(request)
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()
        response: RerankResponseDto = result.get_ok()
        assert len(response.root) > 0
