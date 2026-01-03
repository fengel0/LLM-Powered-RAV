import logging
import math
import os

from core.logger import init_logging
from domain.text_embedding.interface import EmbeddClient
from domain.text_embedding.model import (
    EmbeddingRequestDto,
    EmbeddingResponseDto,
)
from domain_test import AsyncTestBase


init_logging("debug")
logger = logging.getLogger(__name__)


EMBED_ADDR = os.getenv("EMBED_ADDR", "")
USE_TLS = os.getenv("TEI_TLS", "false").lower() in ("1", "true", "yes")


class TestClientsIntegration(AsyncTestBase):
    embed_client: EmbeddClient

    # ---------------- EMBED TESTS (extended) ----------------

    def test_embed_right(self):
        request = EmbeddingRequestDto(
            inputs="This is a test",
            normalize=False,
            prompt_name=None,
            truncate=False,
            truncation_direction="right",
        )
        result = self.embed_client.embed(request)
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()
        response = result.get_ok()
        assert isinstance(response, EmbeddingResponseDto)
        assert len(response.root) > 0
        assert isinstance(response.root, list)
        assert isinstance(response.root[0], float)

    def test_embed_left(self):
        request = EmbeddingRequestDto(
            inputs="This is a test",
            normalize=False,
            prompt_name=None,
            truncate=False,
            truncation_direction="left",
        )
        result = self.embed_client.embed(request)
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()
        response = result.get_ok()
        assert isinstance(response, EmbeddingResponseDto)
        assert len(response.root) > 0
        assert isinstance(response.root, list)
        assert isinstance(response.root[0], float)

    def test_embed_left_normalized_l2_norm_close_to_1(self):
        request = EmbeddingRequestDto(
            inputs="This is a test",
            normalize=True,
            prompt_name=None,
            truncate=False,
            truncation_direction="left",
        )
        result = self.embed_client.embed(request)
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()
        response = result.get_ok()
        assert isinstance(response, EmbeddingResponseDto)
        vec = response.root
        assert len(vec) > 0
        # L2 norm ~ 1.0 if the server actually normalizes
        l2 = math.sqrt(sum(float(x) * float(x) for x in vec))
        assert round(l2, 2) == 1.0

    def test_embed_right_normalized(self):
        request = EmbeddingRequestDto(
            inputs="This is a test",
            normalize=True,
            prompt_name=None,
            truncate=False,
            truncation_direction="right",
        )
        result = self.embed_client.embed(request)
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()
        response = result.get_ok()
        assert isinstance(response, EmbeddingResponseDto)
        assert len(response.root) > 0
        assert isinstance(response.root[0], float)

    def test_embed_batch_inputs_returns_list_of_vectors(self):
        texts = ["short one", "this is longer text", "irrelevant geese again"]
        request = EmbeddingRequestDto(
            inputs=texts,  # list[str] triggers the batch branch
            normalize=False,
            prompt_name=None,
            truncate=False,
            truncation_direction="right",
        )
        result = self.embed_client.embed(request)
        if result.is_error():
            logger.error("embed batch error: %s", result.get_error())
        assert result.is_ok()
        # For list inputs your client returns list[list[float]] not DTO
        vectors = result.get_ok()
        assert isinstance(vectors, list)
        assert len(vectors) == len(texts)
        assert all(isinstance(v, list) and len(v) > 0 for v in vectors)
        assert all(isinstance(v[0], float) for v in vectors)

        # Optional: check consistent dimensionality
        dims = {len(v) for v in vectors}
        assert len(dims) == 1

    def test_embed_query_uses_config_prompt(self):
        res = self.embed_client.embed_query(["what is tei?", "semantic stuff"])
        if res.is_error():
            logger.error(res.get_error())
        assert res.is_ok()

    def test_embed_doc_uses_config_prompt(self):
        res = self.embed_client.embed_doc("this should be treated as a document")
        if res.is_error():
            logger.error(res.get_error())
        assert res.is_ok()

    def test_embed_with_truncate_true(self):
        long_text = "word " * 2000
        request = EmbeddingRequestDto(
            inputs=long_text,
            normalize=False,
            prompt_name=None,
            truncate=True,
            truncation_direction="right",
        )
        result = self.embed_client.embed(request)
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()

    def test_embed_invalid_truncation_direction_returns_err(self):
        request = EmbeddingRequestDto(
            inputs="test",
            normalize=False,
            prompt_name=None,
            truncate=False,
            truncation_direction="middle",  # not acceptable
        )
        result = self.embed_client.embed(request)
        assert result.is_error(), "Expected Err() for invalid truncation dir"

    def test_embed_invalid_prompt_direction_returns_err(self):
        request = EmbeddingRequestDto(
            inputs="test",
            normalize=False,
            prompt_name="unknown",
            truncate=False,
            truncation_direction="middle",  # not acceptable
        )
        result = self.embed_client.embed(request)
        assert result.is_error(), "Expected Err() for invalid truncation dir"

    def test_embed_empty_string_direction_returns_err(self):
        request = EmbeddingRequestDto(
            inputs="",
            normalize=False,
            prompt_name="unknown",
            truncate=False,
            truncation_direction="right",  # not acceptable
        )
        result = self.embed_client.embed(request)
        assert result.is_error(), "Expected Err() for invalid truncation dir"

        request = EmbeddingRequestDto(
            inputs=[""],
            normalize=False,
            prompt_name="unknown",
            truncate=False,
            truncation_direction="right",  # not acceptable
        )
        result = self.embed_client.embed(request)
        assert result.is_error(), "Expected Err() for invalid truncation dir"

    def test_embed_multiple_batches_mixed(self):
        texts = ["alpha", "beta", "gamma " * 500]
        request = EmbeddingRequestDto(
            inputs=texts,
            normalize=True,
            prompt_name=None,
            truncate=True,
            truncation_direction="left",
        )
        result = self.embed_client.embed(request)
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()
        vectors = result.get_ok()
        assert isinstance(vectors, list)
        assert len(vectors) == 3
        # light sanity on normalization
        for vec in vectors:
            l2 = math.sqrt(sum(float(x) * float(x) for x in vec))
            assert 0.9 <= l2 <= 1.1

    def test_embed_single_string_returns_dto_not_list(self):
        request = EmbeddingRequestDto(
            inputs="single string only",
            normalize=False,
            prompt_name=None,
            truncate=False,
            truncation_direction="right",
        )
        result = self.embed_client.embed(request)
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()
        payload = result.get_ok()
        assert isinstance(payload, EmbeddingResponseDto)
        assert isinstance(payload.root, list)

