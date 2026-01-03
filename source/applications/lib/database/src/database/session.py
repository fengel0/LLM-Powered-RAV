from types import ModuleType
from aerich import Command, Migrate
from aerich.models import fields
from tortoise import Model, Tortoise
from typing import Any
from core.singelton import BaseSingleton
from opentelemetry import trace
from pydantic import BaseModel, Field
from typing import Generic, List, TypeVar, Type
from core.result import Result
import logging
from core.model import NotFoundException
import aerich.models as aerich_models


logger = logging.getLogger(__name__)


class DatabaseConfig(BaseModel):
    host: str
    port: str
    database_name: str
    username: str
    password: str
    migration_location: str = Field(default="./migrations")


class PostgresSession(BaseSingleton):
    _config: DatabaseConfig
    _models: list[ModuleType]

    def _init_once(self, config: DatabaseConfig, models: list[ModuleType]):
        logger.info("created PostgresSession")

        self._config = config
        self.tracer = trace.get_tracer("DatabaseSession")
        self._models = models
        self._models.append(aerich_models)

    async def start(self):
        await Tortoise.init(
            db_url=f"postgres://{self._config.username}:{self._config.password}@{self._config.host}:{self._config.port}/{self._config.database_name}",
            modules={"models": self._models},
        )
        conn = Tortoise.get_connection("default")
        await conn.execute_query("SELECT 1;")  # type: ignore

    async def migrations(self, update_message: str = "update"):
        TORTOISE_ORM = {
            "connections": {
                "default": f"postgres://{self._config.username}:{self._config.password}@{self._config.host}:{self._config.port}/{self._config.database_name}"
            },
            "apps": {
                "models": {
                    "models": self._models,
                    "default_connection": "default",
                },
            },
        }

        command = Command(
            tortoise_config=TORTOISE_ORM,
            app="models",
            location=self._config.migration_location,
        )

        # Initialise Aerich’s internal metadata table if it doesn’t exist yet

        await Migrate.init(  # type: ignore
            config=TORTOISE_ORM,
            app="models",
            location=self._config.migration_location,
        )
        try:
            await command.init_db(safe=True)  # no-op when aleady initialised
        except FileExistsError as e:
            logger.warning(
                f"init db file already exists this is fine if it is not the first startup {e}"
            )

        try:
            output = await command.upgrade()
            logger.error(output)
        except Exception as e:
            logger.error(f"upgraded failed {e}")

        try:
            output = await command.migrate(name=update_message)

            logger.error(output)
        except Exception as e:
            logger.error(f"migration failed {e}")

        try:
            output = await command.upgrade()
            logger.error(output)
        except Exception as e:
            logger.error(f"upgraded failed {e}")

    async def shutdown(self) -> None:
        await Tortoise.close_connections()


class DatabaseBaseModel(Model):
    id = fields.UUIDField(primary_key=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    def get_id(self) -> str:
        return str(self.id)


T = TypeVar("T", bound=DatabaseBaseModel)
ID_ATTRIBUTE_STR = "_id"


class BaseDatabase(Generic[T]):
    _model: Type[T]
    tracer: trace.Tracer

    def __init__(self, model: Type[T]):
        """
        Initialize the ProjectDatabase with a specific Pydantic model and MongoDB collection.
        """
        self._model = model
        self.tracer = trace.get_tracer(f"MongoDatabase-{model.__class__}")

    async def create(self, obj: T) -> Result[str]:
        """
        Insert a Pydantic model instance into the collection.
        Returns the inserted document's ID.
        """
        with self.tracer.start_as_current_span("create-object"):
            try:
                await obj.save(force_create=True)
                return Result.Ok(str(obj.id))
            except Exception as e:
                logger.error(e, exc_info=True)
                return Result.Err(e)

    async def create_update(self, obj: T) -> Result[str]:
        with self.tracer.start_as_current_span("create-update-object"):
            try:
                await obj.save()
                return Result.Ok(str(obj.id))
            except Exception as e:
                logger.error(e, exc_info=True)
                return Result.Err(e)

    async def create_list(self, objs: list[T]) -> Result[list[str]]:
        """
        Insert a Pydantic model instance into the collection.
        Returns the inserted document's ID.
        """
        with self.tracer.start_as_current_span("create-object"):
            try:
                await self._model.bulk_create(objs)
                return Result.Ok([str(obj.id) for obj in objs])
            except Exception as e:
                logger.error(e, exc_info=True)
                return Result.Err(e)

    async def get(self, id: str) -> Result[T | None]:
        """
        Retrieve documents matching the query.
        Returns a list of Pydantic model instances.
        """
        with self.tracer.start_as_current_span("find-object-by-id"):
            try:
                return Result.Ok(await self._model.get_or_none(id=id))
            except Exception as e:
                logger.error(e, exc_info=True)
                return Result.Err(e)

    async def get_all(self) -> Result[List[T]]:
        """
        Retrieve documents matching the query.
        Returns a list of Pydantic model instances.
        """
        with self.tracer.start_as_current_span("fetch-all-objects"):
            try:
                models = await self._model.filter()
                return Result.Ok(models)
            except Exception as e:
                logger.error(e, exc_info=True)
                return Result.Err(e)

    async def get_all_with_offset(
        self, offset: int, chunk_size: int
    ) -> Result[List[T]]:
        """
        Retrieve documents matching the query.
        Returns a list of Pydantic model instances.
        """
        with self.tracer.start_as_current_span("fetch-all-objects"):
            try:
                models = await self._model.all().offset(offset).limit(chunk_size)

                return Result.Ok(models)
            except Exception as e:
                logger.error(e, exc_info=True)
                return Result.Err(e)

    async def update(self, obj: T) -> Result[None]:
        with self.tracer.start_as_current_span("update-object"):
            try:
                result_object = await self.get(str(obj.id))
                if result_object.is_error():
                    return result_object.propagate_exception()
                optionl_object = result_object.get_ok()
                if optionl_object is None:
                    return Result.Err(
                        NotFoundException(f"not object with the id:{id} exists")
                    )
                await obj.save(force_update=True)  # type: ignore

                return Result.Ok()
            except Exception as e:
                logger.error(e, exc_info=True)
                return Result.Err(e)

    async def delete(self, id: str) -> Result[None]:
        """
        Delete documents matching the query.
        Returns the number of documents deleted.
        """
        with self.tracer.start_as_current_span("delete-object"):
            try:
                result_object = await self.get(id)
                if result_object.is_error():
                    return result_object.propagate_exception()
                optionl_object = result_object.get_ok()
                if optionl_object is None:
                    return Result.Err(
                        NotFoundException(f"not object with the id:{id} exists")
                    )
                await optionl_object.delete()
                return Result.Ok()
            except Exception as e:
                logger.error(e, exc_info=True)
                return Result.Err(e)

    async def run_query_first(
        self,
        query: dict[str, Any],
        relation: list[str] | None = None,
    ) -> Result[T | None]:
        """Return the newest object that matches *query*."""
        with self.tracer.start_as_current_span("run-custom-query-first"):
            try:
                qs = self._model.filter(**query)
                if relation:
                    qs = qs.prefetch_related(*relation)
                result = await qs.order_by("-created_at").first()
                return Result.Ok(result)
            except Exception as e:
                logger.error(f"run_query_first failed {query}", exc_info=True)
                return Result.Err(e)

    async def run_query(
        self,
        query: dict[str, Any],
        skip: int = 0,
        limit: int | None = None,
        relation: list[str] | None = None,
    ) -> Result[List[T]]:
        """Return all objects that match *query*, newest first, with optional paging."""
        with self.tracer.start_as_current_span("run-custom-query"):
            try:
                qs = self._model.filter(**query)
                if relation:
                    qs = qs.prefetch_related(*relation)

                # Always sort by newest-first creation date
                qs = qs.order_by("-created_at")

                # Apply pagination after ordering
                if skip > 0:
                    qs = qs.offset(skip)
                if limit is not None:
                    qs = qs.limit(limit)

                results = await qs
                return Result.Ok(list(results))
            except Exception as e:
                logger.error(f"run_query failed {query}", exc_info=True)
                return Result.Err(e)
