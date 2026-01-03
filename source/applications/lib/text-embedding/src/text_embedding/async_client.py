from __future__ import annotations
import json

import asyncio
from urllib.parse import urljoin
import logging
from typing import Any, List
from domain.http_client.async_client import AsyncHttpClient

from core.result import Result
from opentelemetry import trace
from pydantic import BaseModel, Field

# your app types
from domain.text_embedding.interface import (
    AsyncRerankerClient,
)

from domain.text_embedding.model import (
    RerankRequestDto,
    RerankResponseDto,
    RerankResponseElement,
)

logger = logging.getLogger(__name__)


class CohereRerankerConfig(BaseModel):
    model: str = Field(default="BAAI/bge-reranker-base")
    retries: int = 3


def _auth_headers(api_key: str, extra: dict[str, str] | None = None) -> dict[str, str]:
    base = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if extra:
        base.update(extra)
    return base


def _ensure_json(body: Any) -> dict[str, Any]:
    if isinstance(body, (dict, list)):
        return body  # type: ignore[return-value]
    if isinstance(body, str) and body:
        try:
            return json.loads(body)
        except Exception:
            return {"raw": body}
    return {"raw": body}


class CohereHttpRerankerClient(AsyncRerankerClient):
    """
    Async reranker via vLLM's Cohere-compatible API using your AsyncHttpClient.
    Endpoint: POST {base_url}/v1/rerank
    """

    tracer: trace.Tracer

    def __init__(
        self,
        http: AsyncHttpClient,
        config: CohereRerankerConfig,
        base_url: str = "http://localhost:8000",  # NOTE: Cohere base has no /v1; we append it
        api_key: str = "sk-fake-key",
    ):
        self.http = http
        self._config = config
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.tracer = trace.get_tracer("CohereHttpRerankerClient")

    async def _rerank_once(
        self, query: str, docs: List[str], return_documents: bool
    ) -> Result[RerankResponseDto]:
        url = urljoin(self.base_url + "/", "v1/rerank")
        headers = _auth_headers(self.api_key)
        payload = {
            "model": self._config.model,
            "query": query,
            "documents": docs,  # vLLM accepts list[str] (Cohere compatibility)
            "top_n": len(docs),
            "return_documents": return_documents,
        }

        res = await self.http.post(url, header=headers, json=payload)
        if res.is_error():
            return res.propagate_exception()

        resp = res.get_ok()
        if resp.status_code < 200 or resp.status_code >= 300:
            body = _ensure_json(resp.body)
            return Result.Err(RuntimeError(f"Rerank HTTP {resp.status_code}: {body}"))

        body = _ensure_json(resp.body)

        try:
            results = body.get("results", [])
            elements: List[RerankResponseElement] = []
            for item in results:
                idx = item.get("index")
                score = float(item.get("relevance_score"))
                text = None
                if return_documents:
                    # item["document"] may be dict or string depending on server; handle both
                    doc_obj = item.get("document")
                    text = doc_obj.get("text")  # type: ignore

                elements.append(
                    RerankResponseElement(index=idx, score=score, text=str(text))
                )
            # To mirror your previous behavior: sort by original index
            elements.sort(key=lambda x: x.score, reverse=True)
            return Result.Ok(RerankResponseDto(root=elements))
        except Exception as e:
            logger.error("Failed to parse rerank response: %s", body, exc_info=True)
            return Result.Err(e)

    async def rerank(self, request: RerankRequestDto) -> Result[RerankResponseDto]:
        with self.tracer.start_as_current_span("rerank-inputs"):
            if not request.texts:
                return Result.Ok(RerankResponseDto(root=[]))

            return_docs = request.return_text

            backoff = 1.0
            last_err: Exception | None = None
            for attempt in range(1, self._config.retries + 1):
                logger.info(f"elements to rerank {len(request.texts)}")
                rv = await self._rerank_once(
                    request.query, list(request.texts), return_docs
                )
                if rv.is_ok():
                    return rv
                last_err = rv.get_error()
                assert last_err
                logger.warning(
                    "[rerank] error on attempt %d/%d: %s",
                    attempt,
                    self._config.retries,
                    last_err,
                    exc_info=True,
                )
                if attempt < self._config.retries:
                    await asyncio.sleep(backoff)
                    backoff *= 2.0

            assert isinstance(last_err, Exception)
            return Result.Err(last_err)
