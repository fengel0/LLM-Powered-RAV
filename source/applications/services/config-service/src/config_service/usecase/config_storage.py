import logging
from typing import Callable
from domain.database.config.interface import ConfigDatabase
from typing import Generic, Type, TypeVar
from core.result import Result
from core.config_loader import (
    ConfigLoader,
    FileConfigAttribute,
    FileConfigObject,
)
from domain.database.config.model import ConfigInterface

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=ConfigInterface)


class ConfigLoaderUsecase(Generic[T]):

    """
    ConfigLoader usecase
    allows to load a json file and update it with new values
    the new config will be stored into the database and writes the new config on to the file system
    """


    _config_loader: ConfigLoader
    _model: Type[T]
    _db: ConfigDatabase[T]

    def __init__(
        self, model: Type[T], db: ConfigDatabase[T], config_loader: ConfigLoader
    ):
        logger.info("created config loader")
        self._config_loader = config_loader
        self._model = model
        self._db = db

    async def load_from_id(self, id: str) -> Result[T | None]:
        return await self._db.get_config_by_id(id=id)

    async def _load_from_id(self, config_holder: FileConfigObject[T]) -> Result[T]:
        assert config_holder.id
        config_db_result = await self._db.get_config_by_id(id=config_holder.id)
        if config_db_result.is_error():
            return config_db_result.propagate_exception()
        config_db = config_db_result.get_ok()
        if config_db is None:
            return Result.Err(
                FileNotFoundError(f"config with id {config_holder.id} not found")
            )
        return Result.Ok(config_db)

    async def write_config_attribut(self, key: str, config: T) -> Result[T]:
        config.compute_config_hash()
        result = await self._db.get_config_by_hash(hash=config.compute_config_hash())
        if result.is_error():
            return result.propagate_exception()
        db_config = result.get_ok()
        if db_config is None:
            logger.error(f"new config {config.compute_config_hash()}")
            result = await self._db.create_config(obj=config)
            if result.is_error():
                raise result.get_error()
            id = result.get_ok().id
            config.id = id
        else:
            config.id = db_config.id

        file_config_attribute: FileConfigAttribute[str] = (
            self._config_loader.get_file_attribute(key=key)
        )

        self._config_loader.write_config(
            attribute=file_config_attribute,
            config=FileConfigObject(id=config.id, stored_config=config),
        )
        return Result.Ok(config)

    async def _load_update_attributes(
        self,
        key: str,
        config_holder: FileConfigObject[T],
        update_lamda: Callable[[T, ConfigLoader], T],
    ) -> Result[T]:
        if config_holder.stored_config is None:
            return Result.Err(Exception("No Valid Configuration given"))

        config_file = config_holder.stored_config

        obj = update_lamda(config_file.model_copy(), self._config_loader)

        result = await self._db.get_config_by_hash(hash=obj.compute_config_hash())
        if result.is_error():
            return result.propagate_exception()
        db_config = result.get_ok()
        if db_config is None:
            logger.error(f"new config {obj.id} - {obj.compute_config_hash()}")
            result = await self._db.create_config(obj=obj)
            if result.is_error():
                raise result.get_error()
            id = result.get_ok().id
            obj.id = id
        else:
            obj.id = db_config.id

        file_config_attribute: FileConfigAttribute[str] = (
            self._config_loader.get_file_attribute(key=key)
        )

        self._config_loader.write_config(
            attribute=file_config_attribute,
            config=FileConfigObject(id=obj.id, stored_config=obj),
        )
        return Result.Ok(obj)

    async def load_config_update_config(
        self,
        key: str,
        update_lamda: Callable[[T, ConfigLoader], T],
    ) -> Result[T]:
        config_holder = self._config_loader.get_model(key=key, model=self._model)
        if config_holder and config_holder.id and config_holder.stored_config is None:
            return await self._load_from_id(config_holder=config_holder)

        if config_holder and config_holder.stored_config:
            return await self._load_update_attributes(
                key=key, config_holder=config_holder, update_lamda=update_lamda
            )

        return Result.Err(Exception(f"no object where found for {key}"))
