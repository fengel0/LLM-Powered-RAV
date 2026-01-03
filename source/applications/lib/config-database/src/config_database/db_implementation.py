import logging
from uuid import uuid4
from core.model import DublicateException
from typing import Any, Generic, Type, TypeVar
from core.result import Result
from database.session import BaseDatabase
from domain.database.config.interface import (
    RAGConfigDatabase,
    RAGRetrivalConfigDatabase,
    SystemConfigDatabase,
)

from opentelemetry import trace

from pydantic import BaseModel
from config_database.model import BasicConfig
from config_database.model import RagRetrievalConfig as RagRetrievalConfigDB
from config_database.model import RagEmbeddingConfig as RagEmbeddingConfigDB
from config_database.model import RagConfig as RagConfigDB
from domain.database.config.model import (
    Config,
    RAGConfig,
    RagEmbeddingConfig,
    RagRetrievalConfig,
)
from domain.database.config.interface import (
    RAGEmbeddingConfigDatabase,
)

logger = logging.getLogger(__name__)


T = TypeVar("T", bound=BaseModel)


class _InternPostgreDBRetrievalConfig(BaseDatabase[RagRetrievalConfigDB]):
    def __init__(self):
        super().__init__(RagRetrievalConfigDB)


class _InternPostgreDBEmbeddingConfig(BaseDatabase[RagEmbeddingConfigDB]):
    def __init__(self):
        super().__init__(RagEmbeddingConfigDB)


class _InternPostgreDBRagConfig(BaseDatabase[RagConfigDB]):
    def __init__(self):
        super().__init__(RagConfigDB)


class _InternPostgreDBSystemConfig(BaseDatabase[BasicConfig], Generic[T]):
    def __init__(self):
        super().__init__(BasicConfig)


class PostgresRAGEmbeddingConfigDatabase(RAGEmbeddingConfigDatabase):
    def __init__(self) -> None:
        self._db = _InternPostgreDBEmbeddingConfig()
        self.tracer = trace.get_tracer("RAGEmbeddingConfigDatabase")

    # -------------- mapping --------------
    def _to_domain(self, db: RagEmbeddingConfigDB) -> RagEmbeddingConfig:
        return RagEmbeddingConfig(
            id=db.get_id(),
            hash=db.hash,
            chunk_size=db.chunk_size,
            chunk_overlap=db.chunk_overlap,
            models=db.models,
            addition_information=db.addition_information,
        )

    # -------------- protocol --------------
    async def create_config(
        self, obj: RagEmbeddingConfig
    ) -> Result[RagEmbeddingConfig]:
        with self.tracer.start_as_current_span("create-embedding-config"):
            obj.compute_config_hash()
            exists = await self.get_config_by_hash(obj.hash)
            if exists.is_error():
                return exists.propagate_exception()
            if exists.get_ok() is not None:
                return Result.Err(
                    DublicateException("embedding config with same hash exists")
                )

            row = RagEmbeddingConfigDB(
                hash=obj.hash,
                chunk_size=obj.chunk_size,
                chunk_overlap=obj.chunk_overlap,
                models=obj.models,
                addition_information=obj.addition_information,
            )
            result = await self._db.create(row)
            if result.is_error():
                return result.propagate_exception()
            id = result.get_ok()
            return Result.Ok(
                RagEmbeddingConfig(
                    id=id,
                    hash=obj.hash,
                    chunk_size=obj.chunk_size,
                    chunk_overlap=obj.chunk_overlap,
                    models=obj.models,
                    addition_information=obj.addition_information,
                )
            )

    async def get_config_by_id(self, id: str) -> Result[RagEmbeddingConfig | None]:
        with self.tracer.start_as_current_span("get-embedding-config-by-id"):
            res = await self._db.get(id=id)
            if res.is_error():
                return res.propagate_exception()
            row = res.get_ok()
            return Result.Ok(None if row is None else self._to_domain(row))

    async def get_config_by_hash(self, hash: str) -> Result[RagEmbeddingConfig | None]:
        with self.tracer.start_as_current_span("get-embedding-config-by-hash"):
            res = await self._db.run_query_first({"hash": hash})
            if res.is_error():
                return res.propagate_exception()
            row = res.get_ok()
            return Result.Ok(None if row is None else self._to_domain(row))

    async def fetch_all(self) -> Result[list[RagEmbeddingConfig]]:
        result = await self._db.get_all()
        if result.is_error():
            return result.propagate_exception()
        return Result.Ok([self._to_domain(o) for o in result.get_ok()])


# ======================================================================================
# 2) Retrieval config repository
# ======================================================================================


class PostgresRAGRetrievalConfigDatabase(RAGRetrivalConfigDatabase):
    def __init__(self) -> None:
        self._db = _InternPostgreDBRetrievalConfig()
        self.tracer = trace.get_tracer("RAGRetrievalConfigDatabase")

    # -------------- mapping --------------
    def _to_domain(self, db: RagRetrievalConfigDB) -> RagRetrievalConfig:
        return RagRetrievalConfig(
            id=db.get_id(),
            hash=db.hash,
            temp=db.temp,
            generator_model=db.generator_model,
            prompts=db.prompts,
            addition_information=db.addition_information,
        )

    # -------------- protocol --------------
    async def create_config(
        self, obj: RagRetrievalConfig
    ) -> Result[RagRetrievalConfig]:
        with self.tracer.start_as_current_span("create-retrieval-config"):
            obj.compute_config_hash()
            exists = await self.get_config_by_hash(obj.hash)
            if exists.is_error():
                return exists.propagate_exception()
            if exists.get_ok() is not None:
                return Result.Err(
                    DublicateException("retrieval config with same hash exists")
                )

            row = RagRetrievalConfigDB(
                hash=obj.hash,
                generator_model=obj.generator_model,
                temp=obj.temp,
                prompts=obj.prompts,
                addition_information=obj.addition_information,
            )
            result = await self._db.create(row)
            if result.is_error():
                return result.propagate_exception()
            id = result.get_ok()
            return Result.Ok(
                RagRetrievalConfig(
                    id=id,
                    hash=obj.hash,
                    temp=obj.temp,
                    generator_model=obj.generator_model,
                    prompts=obj.prompts,
                    addition_information=obj.addition_information,
                )
            )

    async def get_config_by_id(self, id: str) -> Result[RagRetrievalConfig | None]:
        with self.tracer.start_as_current_span("get-retrieval-config-by-id"):
            res = await self._db.get(id=id)
            if res.is_error():
                return res.propagate_exception()
            row = res.get_ok()
            return Result.Ok(None if row is None else self._to_domain(row))

    async def get_config_by_hash(self, hash: str) -> Result[RagRetrievalConfig | None]:
        with self.tracer.start_as_current_span("get-retrieval-config-by-hash"):
            res = await self._db.run_query_first({"hash": hash})
            if res.is_error():
                return res.propagate_exception()
            row = res.get_ok()
            return Result.Ok(None if row is None else self._to_domain(row))

    # -------------- extras --------------
    async def fetch_all(self) -> Result[list[RagRetrievalConfig]]:
        result = await self._db.get_all()
        if result.is_error():
            return result.propagate_exception()
        return Result.Ok([self._to_domain(o) for o in result.get_ok()])


# ======================================================================================
# 3) Top-level RAG config repository (orchestrates embedding + retrieval)
# ======================================================================================


class PostgresRAGConfigDatabase(RAGConfigDatabase):
    def __init__(
        self,
        *,
        embedding_repo: PostgresRAGEmbeddingConfigDatabase | None = None,
        retrieval_repo: PostgresRAGRetrievalConfigDatabase | None = None,
    ) -> None:
        self._db_rag = _InternPostgreDBRagConfig()
        self.embedding_repo = embedding_repo or PostgresRAGEmbeddingConfigDatabase()
        self.retrieval_repo = retrieval_repo or PostgresRAGRetrievalConfigDatabase()
        self.tracer = trace.get_tracer("RAGConfigDatabase")

    # -------------- mapping helpers --------------
    def _to_domain_embedding(self, db: RagEmbeddingConfigDB) -> RagEmbeddingConfig:
        return self.embedding_repo._to_domain(db)  # type: ignore

    def _to_domain_retrieval(self, db: RagRetrievalConfigDB) -> RagRetrievalConfig:
        return self.retrieval_repo._to_domain(db)  # type: ignore

    # -------------- protocol: create/get by id/hash --------------
    async def create_config(self, obj: RAGConfig) -> Result[RAGConfig]:
        """
        Creates a RAGConfig row given a fully-formed domain RAGConfig (with embedding/retrieval already chosen).
        If you prefer name+hashes flow, use create_rag_config() below.
        """
        with self.tracer.start_as_current_span("create-rag-config-from-domain"):
            obj.embedding.compute_config_hash()
            obj.retrieval_config.compute_config_hash()
            # resolve FK rows by hash
            emb_q = await self.embedding_repo.get_config_by_hash(
                hash=obj.embedding.hash
            )
            if emb_q.is_error():
                return emb_q.propagate_exception()
            emb_db = emb_q.get_ok()
            if emb_db is None:
                return Result.Err(
                    ValueError(f"embedding config not found {obj.embedding.hash}")
                )

            ret_q = await self.retrieval_repo.get_config_by_hash(
                hash=obj.retrieval_config.hash
            )
            if ret_q.is_error():
                return ret_q.propagate_exception()
            ret_db = ret_q.get_ok()
            if ret_db is None:
                return Result.Err(
                    ValueError(
                        f"retrieval config not found {obj.retrieval_config.hash}"
                    )
                )

            # uniqueness by name
            by_name = await self._db_rag.run_query_first({"name": obj.name})
            if by_name.is_error():
                return by_name.propagate_exception()
            if by_name.get_ok() is not None:
                return Result.Err(
                    DublicateException("RAG config with same name exists")
                )

            # ensure hash
            rag_hash = obj.compute_config_hash()
            by_hash = await self._db_rag.run_query_first({"hash": rag_hash})
            if by_hash.is_error():
                return by_hash.propagate_exception()
            if by_hash.get_ok() is not None:
                return Result.Err(
                    DublicateException("RAG config with same hash exists")
                )

            row = RagConfigDB(
                name=obj.name,
                hash=rag_hash,
                config_type=obj.config_type,
                embedding_id=emb_db.id,
                retrieval_id=ret_db.id,
            )
            result = await self._db_rag.create(row)
            if result.is_error():
                return result.propagate_exception()
            id = result.get_ok()
            return Result.Ok(
                RAGConfig(
                    id=id,
                    name=obj.name,
                    hash=rag_hash,
                    config_type=obj.config_type,
                    embedding=emb_db,
                    retrieval_config=ret_db,
                )
            )

    async def get_config_by_id(self, id: str) -> Result[RAGConfig | None]:
        with self.tracer.start_as_current_span("get-rag-config-by-id"):
            res = await self._db_rag.run_query_first(
                query={"id": id}, relation=["embedding", "retrieval"]
            )
            if res.is_error():
                return res.propagate_exception()
            row = res.get_ok()
            if row is None:
                return Result.Ok(None)
            # if relations are present on row, use them directly; otherwise hydrate via FKs
            return Result.Ok(
                RAGConfig(
                    id=row.get_id(),
                    name=row.name,
                    hash=row.hash,
                    config_type=row.config_type,
                    embedding=self._to_domain_embedding(row.embedding),
                    retrieval_config=self._to_domain_retrieval(row.retrieval),
                )
            )

    async def get_config_by_hash(self, hash: str) -> Result[RAGConfig | None]:
        with self.tracer.start_as_current_span("get-rag-config-by-hash"):
            res = await self._db_rag.run_query_first(
                {"hash": hash}, relation=["embedding", "retrieval"]
            )
            if res.is_error():
                return res.propagate_exception()
            row = res.get_ok()
            if row is None:
                return Result.Ok(None)

            return Result.Ok(
                RAGConfig(
                    id=row.get_id(),
                    name=row.name,
                    hash=row.hash,
                    config_type=row.config_type,
                    embedding=self._to_domain_embedding(row.embedding),
                    retrieval_config=self._to_domain_retrieval(row.retrieval),
                )
            )

    async def fetch_all(self) -> Result[list[RAGConfig]]:
        try:
            result = await RagConfigDB.all().prefetch_related("embedding", "retrieval")
            return Result.Ok(
                [
                    RAGConfig(
                        id=o.get_id(),
                        name=o.name,
                        hash=o.hash,
                        config_type=o.config_type,
                        embedding=self._to_domain_embedding(o.embedding),
                        retrieval_config=self._to_domain_retrieval(o.retrieval),
                    )
                    for o in result
                ]
            )
        except Exception as e:
            logger.error(e, exc_info=True)
            return Result.Err(e)


class PostgresSystemConfigDatabase(SystemConfigDatabase[T]):
    _db_config: _InternPostgreDBSystemConfig[T]
    _model: Type[T]

    def __init__(self, model: Type[T]) -> None:
        super().__init__()
        self._db_config = _InternPostgreDBSystemConfig()
        self._model = model
        self.tracer = trace.get_tracer("SystemConfigDatabase")

    def _convert_to_domain(self, obj: BasicConfig) -> Config[T]:
        return Config(id=obj.get_id(), hash=obj.hash, data=self._model(**obj.data))

    def _convert_to_db(self, obj: Config[T]) -> BasicConfig:
        dump = obj.model_dump()
        dump["config_type"] = str(self._model.__name__)
        try:
            return BasicConfig(**dump)
        except Exception:
            dump.pop("id")
            return BasicConfig(**dump)

    async def create_config(self, obj: Config[T]) -> Result[Config[T]]:
        result = await self.get_config_by_hash(obj.compute_config_hash())
        if result.is_error():
            return result.propagate_exception()
        if result.get_ok() is not None:
            return Result.Err(
                DublicateException(
                    "config with the same hash and another id already exists"
                )
            )
        db_obj = self._convert_to_db(obj)
        db_obj.id = uuid4()
        result = await self._db_config.create(db_obj)
        if result.is_error():
            return result.propagate_exception()

        created_obj = self._convert_to_domain(db_obj)
        created_obj.id = result.get_ok()

        return Result.Ok(created_obj)

    async def fetch_all(self) -> Result[list[Config[T]]]:
        result = await self._db_config.get_all()
        if result.is_error():
            return result.propagate_exception()
        objs = result.get_ok()
        return Result.Ok([self._convert_to_domain(obj) for obj in objs])

    async def fetch_by_config_type(self, config_type: str) -> Result[dict[str, Any]]:
        result = await self._db_config.run_query(query={"config_type": config_type})
        if result.is_error():
            return result.propagate_exception()
        objs = result.get_ok()
        configs: dict[str, Any] = {}
        for obj in objs:
            configs[str(obj.id)] = obj.data
        return Result.Ok(configs)

    async def get_config_by_id(self, id: str) -> Result[Config[T] | None]:
        with self.tracer.start_as_current_span("get-config-by-d"):
            result = await self._db_config.get(id)
            if result.is_error():
                return result.propagate_exception()
            obj = result.get_ok()
            if obj is None:
                return Result.Ok(None)
            return Result.Ok(self._convert_to_domain(obj=obj))

    async def get_config_by_hash(self, hash: str) -> Result[Config[T] | None]:
        with self.tracer.start_as_current_span("get-config-by-hash"):
            query = {"hash": hash}
            result = await self._db_config.run_query(query)
            if result.is_error():
                return result.propagate_exception()
            objs = result.get_ok()
            if len(objs) == 0:
                return Result.Ok(None)
            obj = objs[0]
            return Result.Ok(self._convert_to_domain(obj=obj))
