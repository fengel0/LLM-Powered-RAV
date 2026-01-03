from __future__ import annotations
from core.singelton import BaseSingleton
from domain.text_embedding.model import EmbeddingResponseDto
from qdrant_client.conversions.common_types import PointId
import logging
from domain.text_embedding.interface import EmbeddClient
from opentelemetry import trace

import uuid
from typing import List, Literal

from core.result import Result
from qdrant_client import AsyncQdrantClient, models
from qdrant_client.models import HasIdCondition, RecommendInput, RecommendQuery

# from qdrant_client.grpc import HasIdCondition
from qdrant_client.models import (
    Distance,
    Filter,
    PointStruct,
    VectorParams,
)
from pydantic import BaseModel

# Your domain model
from domain.hippo_rag.model import (
    Row,
    SimilarNodes,
)  # expects: Row(hash_id: str, content: str, ...)
from domain.hippo_rag.interfaces import EmbeddingStoreInterface

from core.hash import compute_mdhash_id

logger = logging.getLogger(__name__)

Namespace = Literal["entity", "facts", "chunk"]

TEXT_PAYLOAD_KEY: str = "text"
HASH_PAYLOAD_KEY: str = "hash_id"


class QdrantConfig(BaseModel):
    url: str | None = None
    host: str | None = None
    port: int | None = None
    api_key: str | None = None
    timeout: int | None = 30
    default_top_k: int = 10
    prefere_grpc: bool = False
    grpc_port: int = 6334
    https: bool = False


class QdrantEmbeddingStoreConfig(BaseModel):
    collection: str
    namespace: Namespace
    dim: int
    distance: Distance = Distance.COSINE
    default_top_k: int = 10


class HippoRAGVectorStoreSession(BaseSingleton):
    """
    LlamaIndexVectorStoreSession is a singleton class that holds the database instance.
    Allows to reuse the same database instance across the application.
    """

    _aclient: AsyncQdrantClient | None = None

    def _init_once(self, config: QdrantConfig):
        self._aclient = AsyncQdrantClient(
            url=config.url,
            host=config.host,
            port=config.port,
            prefer_grpc=config.prefere_grpc,
            grpc_port=config.grpc_port,
            api_key=config.api_key,
            https=config.https,
            timeout=config.timeout,
        )
        self._config = config

    def get_qdrant_client(self) -> AsyncQdrantClient:
        assert self._aclient is not None, "Database is not initialized."
        return self._aclient

    async def close(self) -> None:
        if self._aclient:
            await self._aclient.close()


class QdrantEmbeddingStore(EmbeddingStoreInterface):
    def __init__(
        self,
        config: QdrantEmbeddingStoreConfig,
        embedder: EmbeddClient,
    ):
        self.tracer = trace.get_tracer("QdrantEmbeddingStore")
        self._config = config
        self.embedder = embedder
        self.client = HippoRAGVectorStoreSession.Instance().get_qdrant_client()

    def _collection_name(self, collection: str | None = None) -> str:
        return f"{self._config.namespace}-{collection or self._config.collection}"

    # ---------- lifecycle ----------
    async def ensure_collection(self, collection: str) -> Result[None]:
        try:
            await self.client.get_collection(collection)
        except Exception:
            try:
                await self.client.create_collection(
                    collection_name=collection,
                    vectors_config=VectorParams(
                        size=self._config.dim, distance=self._config.distance
                    ),
                )
            except Exception as e:
                logger.error(e, exc_info=True)
                return Result.Err(e)
        return Result.Ok()

    @staticmethod
    def _normalize_id(val: str) -> str:
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, val))

    # ---------- interface: write / update ----------
    async def is_doc_already_inserted(self, texts: list[str]) -> Result[dict[str, str]]:
        with self.tracer.start_as_current_span("is-doc-already-inserted"):
            try:
                collection_name = self._collection_name()
                await self.ensure_collection(collection_name)
                if not texts:
                    return Result.Ok({})

                # Dedup by text and compute ids
                unique_texts = list(dict.fromkeys(texts))
                ids = [compute_mdhash_id(t) for t in texts]
                ids_db = [self._normalize_id(id) for id in ids]

                # Find which are missing
                existing = await self.client.retrieve(
                    collection_name=collection_name,
                    ids=ids_db,
                    with_payload=True,
                    with_vectors=False,
                )
                existing_ids = {
                    p.payload.get(HASH_PAYLOAD_KEY, "") for p in existing if p.payload
                }

                to_add: dict[str, str] = {
                    id: text
                    for id, text in zip(ids, unique_texts)
                    if id not in existing_ids
                }
                return Result.Ok(to_add)
            except Exception as e:
                logger.error(e, exc_info=True)
                return Result.Err(e)

    async def insert_strings(
        self,
        texts: list[str],
    ) -> Result[None]:
        with self.tracer.start_as_current_span("insert-strings"):
            try:
                collection_name = self._collection_name()
                await self.ensure_collection(collection_name)
                if not texts:
                    return Result.Ok()

                result = await self.is_doc_already_inserted(texts)
                if result.is_error():
                    return result.propagate_exception()
                to_add = result.get_ok()
                new_ids = [i for i in to_add.keys()]
                new_texts = [t for t in to_add.values()]
                if len(new_texts) == 0:
                    return Result.Ok()
                res = self.embedder.embed_doc(new_texts)
                if res.is_error():
                    return res.propagate_exception()
                vectores = res.get_ok()
                assert isinstance(vectores, list)

                points = [
                    PointStruct(
                        id=self._normalize_id(pid),
                        vector=vec,
                        payload={
                            TEXT_PAYLOAD_KEY: txt,
                            HASH_PAYLOAD_KEY: pid,
                        },
                    )
                    for pid, txt, vec in zip(new_ids, new_texts, vectores)
                ]

                await self.client.upsert(collection_name=collection_name, points=points)
                return Result.Ok()
            except Exception as e:
                logger.error(e, exc_info=True)
                return Result.Err(e)

    async def delete(self, hash_ids: list[str]) -> Result[None]:
        with self.tracer.start_as_current_span("delete-hash-id"):
            try:
                if not hash_ids:
                    return Result.Ok()
                await self.client.delete(
                    collection_name=self._collection_name(),
                    points_selector=models.PointIdsList(
                        points=[self._normalize_id(id) for id in hash_ids]
                    ),  # type: ignore
                )
                return Result.Ok()
            except Exception as e:
                logger.error(e, exc_info=True)
                return Result.Err(e)

    async def delete_store(self, collection: str) -> Result[None]:
        with self.tracer.start_as_current_span("delete-indexer-db"):
            try:
                if self._collection_name(collection) == self._collection_name():
                    return Result.Err(Exception("Tried to delete Source VectorDB"))
                await self.client.delete_collection(
                    collection_name=self._collection_name(collection)
                )
                return Result.Ok()
            except Exception as e:
                logger.error(e, exc_info=True)
                return Result.Err(e)

    # ---------- interface: helpers used by callers ----------
    async def get_missing_string_hash_ids(
        self, texts: list[str]
    ) -> Result[dict[str, Row]]:
        with self.tracer.start_as_current_span("get-missing-string-hash-ids"):
            try:
                if not texts:
                    return Result.Ok({})
                ids = [compute_mdhash_id(t) for t in texts]
                ids_db = [self._normalize_id(id) for id in ids]
                got = await self.client.retrieve(
                    collection_name=self._collection_name(),
                    ids=ids_db,
                    with_payload=True,
                    with_vectors=False,
                )
                existing = {
                    p.payload.get(HASH_PAYLOAD_KEY, "") for p in got if p.payload
                }
                return Result.Ok(
                    {
                        hid: Row(hash_id=hid, content=txt)
                        for hid, txt in zip(ids, texts)
                        if hid not in existing
                    }
                )
            except Exception as e:
                logger.error(e, exc_info=e)
                return Result.Err(e)

    async def get_row(self, hash_id: str) -> Result[Row]:
        with self.tracer.start_as_current_span("get-row"):
            try:
                pts = await self.client.retrieve(
                    collection_name=self._collection_name(),
                    ids=[self._normalize_id(hash_id)],
                    with_payload=True,
                    with_vectors=False,
                )
                if not pts:
                    raise KeyError(hash_id)
                p = pts[0]
                assert p.payload
                content = p.payload.get(TEXT_PAYLOAD_KEY, "")
                return Result.Ok(
                    Row(hash_id=p.payload.get(HASH_PAYLOAD_KEY, ""), content=content)
                )
            except Exception as e:
                logger.error(e, exc_info=True)
                return Result.Err(e)

    async def get_rows(self, hash_ids: list[str]) -> Result[dict[str, Row]]:
        with self.tracer.start_as_current_span("get-rows"):
            try:
                out: dict[str, Row] = {}
                if not hash_ids:
                    return Result.Ok(out)
                pts = await self.client.retrieve(
                    collection_name=self._collection_name(),
                    ids=[self._normalize_id(id) for id in hash_ids],
                    with_payload=True,
                    with_vectors=False,
                )
                for p in pts:
                    assert p.payload
                    content = p.payload.get(TEXT_PAYLOAD_KEY, "")
                    nid = p.payload[HASH_PAYLOAD_KEY]
                    out[nid] = Row(hash_id=nid, content=content)
                return Result.Ok(out)
            except Exception as e:
                logger.error(e, exc_info=True)
                return Result.Err(e)

    async def get_all_ids(self) -> Result[list[str]]:
        with self.tracer.start_as_current_span("get-all-ids"):
            try:
                out: List[str] = []
                next_page = None
                while True:
                    res = await self.client.scroll(
                        collection_name=self._collection_name(),
                        with_payload=True,
                        with_vectors=False,
                        limit=1024,
                        offset=next_page,
                    )
                    points, next_page = res
                    out.extend(p.payload[HASH_PAYLOAD_KEY] for p in points if p.payload)
                    if next_page is None or not points:
                        break
                return Result.Ok(out)
            except Exception as e:
                logger.error(e, exc_info=True)
                return Result.Err(e)

    async def get_all_id_to_rows(
        self, collection: str | None = None
    ) -> Result[dict[str, Row]]:
        with self.tracer.start_as_current_span("get-all-ids-to-row"):
            try:
                collection_name = self._collection_name(collection)
                out: dict[str, Row] = {}
                next_page = None
                while True:
                    points, next_page = await self.client.scroll(
                        collection_name=collection_name,
                        with_payload=True,
                        with_vectors=False,
                        limit=1024,
                        offset=next_page,
                    )
                    for p in points:
                        assert p.payload
                        content = p.payload.get(TEXT_PAYLOAD_KEY, "")
                        id = p.payload.get(HASH_PAYLOAD_KEY, "")

                        out[id] = Row(hash_id=id, content=content)
                    if next_page is None or not points:
                        break
                return Result.Ok(out)
            except Exception as e:
                logger.error(e, exc_info=True)
                return Result.Err(e)

    async def get_all_texts(self) -> Result[set[str]]:
        with self.tracer.start_as_current_span("get-all-texts"):
            try:
                texts: set[str] = set()
                next_page = None
                while True:
                    points, next_page = await self.client.scroll(
                        collection_name=self._collection_name(),
                        with_payload=True,
                        with_vectors=False,
                        limit=1024,
                        offset=next_page,
                    )
                    for p in points:
                        payload = p.payload or {}
                        val = payload.get(TEXT_PAYLOAD_KEY)
                        if isinstance(val, str):
                            texts.add(val)
                    if next_page is None or not points:
                        break
                return Result.Ok(texts)
            except Exception as e:
                logger.error(e, exc_info=True)
                return Result.Err(e)

    async def get_embedding(self, hash_id: str) -> Result[list[float]]:
        with self.tracer.start_as_current_span("get-embedding"):
            try:
                pts = await self.client.retrieve(
                    collection_name=self._collection_name(),
                    ids=[self._normalize_id(hash_id)],
                    with_payload=False,
                    with_vectors=True,
                )
                if not pts:
                    raise KeyError(hash_id)
                vec = pts[0].vector
                if isinstance(vec, dict):
                    # named vectors: choose default
                    vec = next(iter(vec.values()))
                return Result.Ok(list(vec or []))  # type: ignore
            except Exception as e:
                logger.error(e, exc_info=True)
                return Result.Err(e)

    async def get_embeddings(self, hash_ids: list[str]) -> Result[list[float]]:
        with self.tracer.start_as_current_span("get-embeddings"):
            try:
                if not hash_ids:
                    return Result.Ok([])
                pts = await self.client.retrieve(
                    collection_name=self._collection_name(),
                    ids=[self._normalize_id(id) for id in hash_ids],
                    with_payload=False,
                    with_vectors=True,
                )
                out: list[float] = []
                # Return flattened list to match your signature
                for p in pts:
                    vec = p.vector
                    if isinstance(vec, dict):
                        vec = next(iter(vec.values()))
                    out.extend(list(vec or []))  # type: ignore
                return Result.Ok(out)
            except Exception as e:
                logger.error(e, exc_info=True)
                return Result.Err(e)

    async def query(
        self,
        query: str,
        top_k: int | None = None,
        collection: str | None = None,
        allowd__point_ids: list[str] | None = None,
    ) -> Result[list[SimilarNodes]]:
        with self.tracer.start_as_current_span("query"):
            try:
                """
                Vector search by raw query string. Uses the configured embedder.
                Returns list of dicts with id, score, and payload.
                """
                flt: Filter | None = None
                if allowd__point_ids:
                    # ids = [GRPCPointID(id) for id in allowd__point_ids]
                    flt = Filter(
                        must=[
                            HasIdCondition(
                                has_id=[
                                    self._normalize_id(id) for id in allowd__point_ids
                                ]
                            )
                        ]
                    )  # type: ignore
                result = self.embedder.embed_query(query)
                if result.is_error():
                    return result.propagate_exception()
                qvec = result.get_ok()
                assert isinstance(qvec, EmbeddingResponseDto)

                hits = await self.client.query_points(
                    query_filter=flt,
                    collection_name=self._collection_name(collection),
                    query=qvec.root,
                    limit=top_k or self._config.default_top_k,
                    with_payload=True,
                    with_vectors=False,
                )
                return Result.Ok(
                    [
                        SimilarNodes(
                            id=h.payload["hash_id"],
                            score=h.score,
                            payload=h.payload["text"],
                        )
                        for h in hits.points
                        if h.payload
                    ]
                )
            except Exception as e:
                logger.error(e, exc_info=True)
                return Result.Err(e)

    async def move_all_ids_to_new_collection(
        self, hash_ids: list[str], collection: str
    ) -> Result[None]:
        with self.tracer.start_as_current_span("move_hash_ids_to_new_collection"):
            try:
                new_collection_name = self._collection_name(collection)
                result = await self.ensure_collection(new_collection_name)
                if result.is_error():
                    return result.propagate_exception()
                if not hash_ids:
                    return Result.Ok()

                point_id: PointId | None = None

                while True:
                    self.client.search
                    pts, point_id = await self.client.scroll(
                        collection_name=self._collection_name(),
                        scroll_filter=models.Filter(
                            must=[
                                models.HasIdCondition(
                                    has_id=[self._normalize_id(id) for id in hash_ids]
                                )
                            ]  # type: ignore
                        ),
                        limit=1000,
                        offset=point_id,
                        with_payload=True,
                        with_vectors=True,
                    )
                    batch = [
                        models.PointStruct(
                            id=r.id,
                            vector=r.vector,  # type: ignore
                            payload=r.payload or {},
                        )
                        for r in pts
                        if r.vector
                    ]

                    await self.client.upsert(
                        collection_name=new_collection_name, points=batch
                    )
                    if point_id is None:
                        break
            except Exception as e:
                logger.error(e, exc_info=True)
                return Result.Err(e)
            return Result.Ok()

    async def knn_by_ids(
        self,
        query_ids: List[str],
        top_k: int,
        min_similarity: float = 0.0,
        allowd__point_ids: list[str] | None = None,
        collection: str | None = None,
    ) -> Result[dict[str, list[SimilarNodes]]]:
        with self.tracer.start_as_current_span("knn-by-id"):
            try:
                out: dict[str, list[SimilarNodes]] = {}
                if not query_ids:
                    return Result.Ok({})
                flt: Filter | None = None
                if allowd__point_ids:
                    flt = Filter(
                        must=[
                            HasIdCondition(
                                has_id=[
                                    self._normalize_id(id) for id in allowd__point_ids
                                ]
                            )
                        ]
                    )  # type: ignore

                for qid in query_ids:
                    hits = await self.client.query_points(
                        query_filter=flt,
                        collection_name=self._collection_name(collection=collection),
                        query=RecommendQuery(
                            recommend=RecommendInput(
                                positive=[
                                    self._normalize_id(qid)
                                ],  # IDs or vectors both fine
                                negative=[],  # keep parity with old call
                                # strategy=qm.RecommendStrategy.AVERAGE,  # optional; AVERAGE is default
                            )
                        ),
                        limit=top_k,
                        with_payload=True,
                        with_vectors=False,
                        score_threshold=min_similarity if min_similarity > 0 else None,
                    )

                    nodes_to_appnd = [
                        SimilarNodes(
                            id=h.payload[HASH_PAYLOAD_KEY],
                            score=h.score,
                            payload=h.payload[TEXT_PAYLOAD_KEY],
                        )
                        for h in hits.points
                        if h.payload
                    ]
                    out[qid] = nodes_to_appnd

                return Result.Ok(out)
            except Exception as e:
                logger.error(e, exc_info=True)
                return Result.Err(e)
