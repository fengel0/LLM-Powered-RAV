import logging
import time
from opentelemetry import trace
from typing import Any
from core.result import Result
from domain.text_embedding.interface import EmbeddClient, RerankerClient
import grpc
from pydantic import BaseModel

from text_embedding.proto.tei_pb2 import (
    RerankRequest,  # type: ignore
    EmbedRequest,  # type: ignore
    TRUNCATION_DIRECTION_RIGHT,  # type: ignore
    TRUNCATION_DIRECTION_LEFT,  # type: ignore
)
from text_embedding.proto.tei_pb2_grpc import RerankStub, EmbedStub

from domain.text_embedding.model import (
    RerankRequestDto,
    RerankResponseDto,
    RerankResponseElement,
    EmbeddingRequestDto,
    EmbeddingResponseDto,
)

logger = logging.getLogger(__name__)


def map_truncation_direction(direction: str) -> Any:
    if direction == "right":
        return TRUNCATION_DIRECTION_RIGHT  # type: ignore
    elif direction == "left":
        return TRUNCATION_DIRECTION_LEFT  # type: ignore
    else:
        raise ValueError(f"Unknown truncation direction: {direction}")


class EmbeddingClientConfig(BaseModel):
    normalize: bool
    prompt_name_query: str | None
    prompt_name_doc: str | None
    truncate: bool
    truncate_direction: str
    reties: int = 3


class GrpcEmbeddClient(EmbeddClient):
    tracer: trace.Tracer

    def __init__(
        self,
        config: EmbeddingClientConfig,
        address: str = "localhost:50051",
        is_secure: bool = False,
    ):
        if is_secure:
            self.channel = grpc.secure_channel(address)  # type: ignore
        else:
            self.channel = grpc.insecure_channel(address)  # type: ignore
        self.stub = EmbedStub(self.channel)  # type: ignore
        self.tracer = trace.get_tracer("GrpcEmbeddClient")
        self._config = config

    def _embed(self, input: EmbeddingRequestDto) -> Result[EmbeddingResponseDto]:
        with self.tracer.start_as_current_span("embed-input"):
            backoff = 1
            try:
                grpc_request = EmbedRequest(  # type: ignore
                    inputs=input.inputs,
                    normalize=input.normalize,
                    truncate=input.truncate,
                    truncation_direction=map_truncation_direction(
                        input.truncation_direction
                    ),
                )
            except Exception as exc:
                logger.error(exc, exc_info=True)
                return Result.Err(exc)

            last_err: Exception | None = None
            for attempt in range(1, self._config.reties + 1):
                try:
                    if input.prompt_name:
                        grpc_request.prompt_name = input.prompt_name

                    grpc_response = self.stub.Embed(grpc_request)  # type: ignore
                    return Result.Ok(
                        EmbeddingResponseDto(root=grpc_response.embeddings)  # type: ignore
                    )  # type: ignore
                except Exception as exc:
                    logger.warning(
                        "[embedding] error on attempt %d/%d: %s",
                        attempt,
                        self._config.reties,
                        exc,
                        exc_info=True,
                    )
                    last_err = exc
                if attempt < self._config.reties:
                    time.sleep(backoff)
                    backoff *= 2

            assert last_err, "This should never happen"

            return Result.Err(last_err)  # type: ignore[arg-type]

    def embed(
        self, request: EmbeddingRequestDto
    ) -> Result[EmbeddingResponseDto | list[list[float]]]:
        with self.tracer.start_as_current_span("embed-inputs"):
            if isinstance(request.inputs, str):
                return self._embed(request)
            else:
                copy_request = request.model_copy()
                repsonses: list[list[float]] = []
                for input in request.inputs:
                    copy_request.inputs = input
                    embedding = self._embed(copy_request)
                    if embedding.is_error():
                        return embedding.propagate_exception()

                    repsonses.append(embedding.get_ok().root)
                return Result.Ok(repsonses)

    def embed_doc(
        self, text: str | list[str]
    ) -> Result[EmbeddingResponseDto | list[list[float]]]:
        with self.tracer.start_as_current_span("embed-doc"):
            if len(text) == 0:
                logger.error("text is empty")
                logger.error(text)
            return self.embed(
                EmbeddingRequestDto(
                    inputs=text,
                    normalize=self._config.normalize,
                    prompt_name=self._config.prompt_name_doc,
                    truncate=self._config.truncate,
                    truncation_direction=self._config.truncate_direction,
                )
            )

    def embed_query(
        self, text: str | list[str]
    ) -> Result[EmbeddingResponseDto | list[list[float]]]:
        with self.tracer.start_as_current_span("embed-query"):
            if len(text) == 0:
                logger.error("error while embedd query")
                logger.error(text)
            return self.embed(
                EmbeddingRequestDto(
                    inputs=text,
                    normalize=self._config.normalize,
                    prompt_name=self._config.prompt_name_query,
                    truncate=self._config.truncate,
                    truncation_direction=self._config.truncate_direction,
                )
            )

    def __del__(self):
        self.channel.close()


class GrpcRerankerClient(RerankerClient):
    def __init__(self, address: str = "localhost:50051", is_secure: bool = False):
        if is_secure:
            self.channel = grpc.secure_channel(address)  # type: ignore
        else:
            self.channel = grpc.insecure_channel(address)  # type: ignore
        self.stub = RerankStub(self.channel)
        self.tracer = trace.get_tracer("GrpcRerankerClient")

    def rerank(self, request: RerankRequestDto) -> Result[RerankResponseDto]:
        with self.tracer.start_as_current_span("rerank-inputs"):
            try:
                grpc_request = RerankRequest(  # type: ignore
                    query=request.query,
                    texts=request.texts,
                    raw_scores=request.raw_scores,
                    return_text=request.return_text,
                    truncate=request.truncate,
                    truncation_direction=map_truncation_direction(
                        request.truncation_direction
                    ),
                )
                grpc_response = self.stub.Rerank(grpc_request)  # type: ignore
                response = RerankResponseDto(
                    root=[
                        RerankResponseElement(
                            index=rank.index,  # type: ignore
                            score=rank.score,  # type: ignore
                            text=rank.text,  # type: ignore
                        )
                        for rank in grpc_response.ranks  # type: ignore
                    ]
                )
                response.root.sort(key=lambda x: x.score, reverse=True)
                return Result.Ok(response)
            except Exception as e:
                logger.error(e, exc_info=True)
                return Result.Err(e)

    def __del__(self):
        self.channel.close()
