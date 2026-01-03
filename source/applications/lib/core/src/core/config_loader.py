from abc import ABC, abstractmethod
from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import Any, Generic, Type, TypeAlias, TypeVar, Union, runtime_checkable
from typing_extensions import Protocol

from core.result import Result, str_to_bool
import logging
from pydantic import BaseModel

from core.singelton import BaseSingleton

logger = logging.getLogger(__name__)

ConfigType: TypeAlias = Union[str, int, float, bool]
R = TypeVar("R", str, int, float, bool)
T = TypeVar("T", bound=BaseModel)


class NoKeyException(Exception): ...


class ConfigAttribute(BaseModel, Generic[R], ABC):
    name: str
    default_value: ConfigType | None
    value_type: Type[R]
    is_secret: bool


class EnvConfigAttribute(ConfigAttribute[R]): ...


class FileConfigAttribute(ConfigAttribute[R]):
    file_location: str


class FileConfigObject(BaseModel, Generic[T]):
    id: str | None
    stored_config: T | None


class ConfigLoader:
    """
    Protocol for a configuration loader that reads values from environment
    variables, files, or other sources and makes them available through a
    strongly‑typed API.  All operations that may fail return a :class:`Result`
    object rather than raising exceptions.
    """

    # --------------------------------------------------------------------- #
    # Loading
    # --------------------------------------------------------------------- #
    def load_values(self, attributes: list[ConfigAttribute[Any]]) -> Result[None]:
        """
        Load a collection of configuration attributes.

        * Each attribute is read from its defined source (env var, file, …).
        * The raw string is cast to the attribute’s ``value_type``.
        * Successful casts are stored in the loader’s internal cache.
        * If a value cannot be obtained, the attribute’s ``default_value`` is used
          (when present).  Otherwise a ``Result.Err`` wrapping the first
          exception (e.g. missing key, conversion error) is returned.
        * Returns ``Result.Ok()`` only when **all** attributes have been processed
          without error.
        """
        ...

    # --------------------------------------------------------------------- #
    # Logging
    # --------------------------------------------------------------------- #
    def log_loaded_values(self, log_secrets: bool) -> None:
        """
        Write an INFO‑level log entry for each loaded key/value pair.

        * When ``log_secrets`` is ``False`` any attribute marked as secret is
          omitted from the output.
        * The method never propagates exceptions; failures are handled internally.
        """
        ...

    # --------------------------------------------------------------------- #
    # Typed getters
    # --------------------------------------------------------------------- #
    def get_str(self, key: str) -> str:
        """
        Return the value associated with *key* as a ``str``.

        * Raises ``AssertionError`` if the stored value is not a string.
        * If the key is missing, an empty string is returned before the type
          check (mirroring the reference implementation’s fallback behaviour).
        """
        ...

    def get_int(self, key: str) -> int:
        """
        Return the value associated with *key* as an ``int``.

        * Raises ``AssertionError`` if the stored value is not an integer.
        * Missing keys default to ``""`` which will trigger the assertion, just
          as the reference implementation does.
        """
        ...

    def get_float(self, key: str) -> float:
        """
        Return the value associated with *key* as a ``float``.

        * Raises ``AssertionError`` if the stored value is not a float.
        """
        ...

    def get_bool(self, key: str) -> bool:
        """
        Return the value associated with *key* as a ``bool``.

        * Raises ``AssertionError`` if the stored value is not a boolean.
        """
        ...

    # --------------------------------------------------------------------- #
    # Model handling
    # --------------------------------------------------------------------- #
    def get_model(
        self,
        key: str,
        model: Type[T],
    ) -> FileConfigObject[T] | None:
        """
        Parse the JSON string stored under *key* into a Pydantic model of type
        ``model`` and wrap it in a ``FileConfigObject``.

        * Returns the parsed object when the stored string is non‑empty.
        * Returns ``None`` when the key is missing or the string is empty.
        """
        ...

    # --------------------------------------------------------------------- #
    # File‑backed attribute helpers
    # --------------------------------------------------------------------- #
    def get_file_attribute(self, key: str) -> FileConfigAttribute[R]:
        """
        Retrieve the original ``FileConfigAttribute`` that produced the value for
        *key*.

        * Raises ``AssertionError`` if the key does not correspond to a
          file‑backed attribute.
        """
        ...

    def write_config(
        self,
        attribute: FileConfigAttribute[R],
        config: FileConfigObject[T],
    ) -> Result[None]:
        """
        Serialise ``config`` to pretty‑printed JSON and write it to the location
        defined by ``attribute.file_location``.

        * Returns ``Result.Ok()`` on successful write.
        * Returns ``Result.Err(exc)`` if any I/O or serialisation error occurs,
          and logs the exception.
        """
        ...


class ConfigLoaderImplementation(BaseSingleton, ConfigLoader):
    _config: dict[str, ConfigType]
    _attributes: list[ConfigAttribute[Any]]

    def _init_once(self) -> None:
        logger.debug("create ConfigLoaderImplementation")
        self._attributes = []
        self._config = {}

    def load_values(self, attributes: list[ConfigAttribute[Any]]) -> Result[None]:
        return self._load_config(attributes=attributes)

    def _load_value(self, config_attribute: ConfigAttribute[Any]) -> str | None:
        if isinstance(config_attribute, FileConfigAttribute):
            try:
                with open(config_attribute.file_location, "r") as file:
                    return file.read()
            except FileNotFoundError as e:
                logger.warning(e, exc_info=True)
                return None
        if isinstance(config_attribute, EnvConfigAttribute):
            return os.environ.get(config_attribute.name)

    def _load_config(self, attributes: list[ConfigAttribute[Any]]) -> Result[None]:
        for attribute in attributes:
            logger.debug(f"load {attribute}")
            value = self._load_value(attribute)

            if value is not None:
                try:
                    if attribute.value_type is bool:
                        casted_value = str_to_bool(value)
                    else:
                        casted_value = attribute.value_type(value)
                    self._config[attribute.name] = casted_value
                    continue
                except Exception as e:
                    logger.error(
                        f"{e} failed for attribute {attribute}:{value}", exc_info=True
                    )
                    return Result.Err(e)

            if attribute.default_value is not None:
                self._config[attribute.name] = attribute.default_value
                continue

            return Result.Err(NoKeyException(f"No Value for Key {attribute.name} set"))
        self._attributes = [*self._attributes, *attributes]
        return Result.Ok()

    def log_loaded_values(self, log_secrets: bool):
        for attribute in self._attributes:
            if not log_secrets and attribute.is_secret:
                continue
            logger.info(f"Key:{attribute.name} | Value:{self._config[attribute.name]}")

    def get_str(self, key: str) -> str:
        value = self._config.get(key, "")
        assert isinstance(value, str), f"key: {key} value content: |{value}|"
        return value

    def get_int(self, key: str) -> int:
        value = self._config.get(key, "")
        assert isinstance(value, int), f"key: {key} value content: |{value}|"
        return value

    def get_float(self, key: str) -> float:
        value = self._config.get(key, "")
        assert isinstance(value, float), f"key: {key} value content: |{value}|"
        return value

    def get_bool(self, key: str) -> bool:
        value = self._config.get(key, "")
        assert isinstance(value, bool), f"key: {key} value content: |{value}|"
        return value

    def get_model(self, key: str, model: Type[T]) -> FileConfigObject[T] | None:
        data = self.get_str(key=key)
        if data:
            return FileConfigObject[model].model_validate_json(data)
        return None

    def get_file_attribute(self, key: str) -> FileConfigAttribute[R]:
        for attribute in self._attributes:
            if attribute.name == key:
                assert isinstance(attribute, FileConfigAttribute)
                return attribute
        assert False, f"Not file Attribute with key {key} found"

    def write_config(
        self, attribute: FileConfigAttribute[R], config: FileConfigObject[T]
    ) -> Result[None]:
        try:
            with open(attribute.file_location, "w+") as file:
                file.write(config.model_dump_json(indent=2))
            return Result.Ok()
        except Exception as e:
            logger.error(e, exc_info=True)
            return Result.Err(e)


def _serialize_bool(v: Any) -> str:
    # match your str_to_bool expectations
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, str):
        # trust caller; str_to_bool will parse when read
        return v
    return "true" if bool(v) else "false"


def _to_serialized_text(value: Any, value_type: type) -> str:
    """
    Convert a provided python value to the text we will write into enviroment/file
    so that your existing loaders can read & cast it back.
    """
    if value_type is bool:
        return _serialize_bool(value)
    if isinstance(value, (dict, list)):
        # if someone passes a structure, write JSON
        return json.dumps(value)
    if isinstance(value, BaseModel):
        return value.model_dump_json()
    if isinstance(value, FileConfigObject):
        return value.model_dump_json()
    return str(value)


@dataclass
class _FileSnapshot:
    path: Path
    existed: bool
    content: bytes | None


class ConfigProvisioner:
    def __init__(
        self,
        attributes: list[ConfigAttribute[Any]],
        values: Union[dict[str, Any], list[tuple[str, Any]]],
        create_missing_dirs: bool = True,
    ) -> None:
        self.attributes = attributes
        self.values = dict(values) if isinstance(values, list) else values
        self.create_missing_dirs = create_missing_dirs

        # restore state
        self._prev_env: dict[str, str | None] = {}
        self._file_snaps: list[_FileSnapshot] = []
        self._applied = False

        # validate up front, so failures happen early and loudly
        self._validated_map = self._validate_and_prepare()

    def _validate_and_prepare(
        self,
    ) -> dict[str, tuple[ConfigAttribute[Any], str | None]]:
        """
        Returns map name -> (attribute, serialized_value or None if default->None)
        """
        name_to_tuple: dict[str, tuple[ConfigAttribute[Any], str | None]] = {}

        for attr in self.attributes:
            name = attr.name

            if name in self.values:
                raw = self.values[name]
                try:
                    serialized = _to_serialized_text(raw, attr.value_type)
                except Exception as e:
                    raise ValueError(
                        f"Cannot serialize value for {name}: {raw!r}"
                    ) from e
                name_to_tuple[name] = (attr, serialized)
                continue

            # not provided: use default if present
            if attr.default_value is not None:
                serialized = _to_serialized_text(attr.default_value, attr.value_type)
                name_to_tuple[name] = (attr, serialized)
                continue

            raise NoKeyException(f"No Value for Key {name} set and no default provided")

        return name_to_tuple

    def apply(self) -> None:
        if self._applied:
            return

        for name, (attr, serialized) in self._validated_map.items():
            if isinstance(attr, EnvConfigAttribute):
                # snapshot previous
                self._prev_env[name] = os.environ.get(name)
                # set
                if serialized is None:
                    # unset if explicitly None (rare)
                    if name in os.environ:
                        del os.environ[name]
                else:
                    os.environ[name] = serialized

            elif isinstance(attr, FileConfigAttribute):
                path = Path(attr.file_location)
                if self.create_missing_dirs:
                    path.parent.mkdir(parents=True, exist_ok=True)

                existed = path.exists()
                previous = path.read_bytes() if existed else None
                self._file_snaps.append(
                    _FileSnapshot(path=path, existed=existed, content=previous)
                )

                to_write = (serialized or "").encode("utf-8")
                path.write_bytes(to_write)
            else:
                # in case new attribute types are added in the future
                raise TypeError(f"Unsupported attribute type for {name}: {type(attr)}")

        self._applied = True

    def restore(self) -> None:
        if not self._applied:
            return

        # restore enviroment
        for key, prev in self._prev_env.items():
            if prev is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = prev

        # restore files
        for snap in reversed(self._file_snaps):
            if snap.existed:
                # put original content back
                if snap.content is not None:
                    snap.path.write_bytes(snap.content)
                else:
                    # existed but unreadable before? highly unlikely
                    pass
            else:
                # we created it → delete
                try:
                    snap.path.unlink(missing_ok=True)
                except Exception as e:
                    logger.warning("Failed to remove test file %s: %s", snap.path, e)

        self._prev_env.clear()
        self._file_snaps.clear()
        self._applied = False

    # context-manager sugar, because tests deserve nice things
    def __enter__(self) -> "ConfigProvisioner":
        self.apply()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore
        self.restore()
