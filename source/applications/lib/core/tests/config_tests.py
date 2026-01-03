from __future__ import annotations

import logging
import os
from typing import Any
from unittest.mock import mock_open, patch

import pytest
from pydantic import BaseModel

from core.config_loader import (
    ConfigAttribute,  # abstract; imported for typing only
    ConfigLoaderImplementation,
    EnvConfigAttribute,
    FileConfigAttribute,
    FileConfigObject,
    NoKeyException,
)
from core.logger import init_logging
from core.singelton import SingletonMeta


class ExampleSettings(BaseModel):
    foo: str
    bar: int


# --- Constants for Environment Variable Keys ---
ENV_MY_STRING = "MY_STRING"
ENV_MY_INT = "MY_INT"
ENV_MY_BOOL = "MY_BOOL"
ENV_MY_FLOAT = "MY_FLOAT"
ENV_DEFAULTED_STRING = "DEFAULTED_STRING"
ENV_MISSING_VAR = "MISSING_VAR"
ENV_TEST_KEY = "TEST_KEY"
ENV_BAD_INT = "BAD_INT"
ENV_BOOL_KEY = "BOOL_KEY"

init_logging("debug")
logger = logging.getLogger(__name__)


class TestConfigLoaderPytest:
    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        # ensure each test starts with a fresh singleton registry
        SingletonMeta.clear_all()

    def test_successful_config_load_from_file(self):
        file_content = "file_value"
        m = mock_open(read_data=file_content)

        with patch("builtins.open", m):
            attributes: list[ConfigAttribute[Any]] = [
                FileConfigAttribute(
                    name=ENV_MY_STRING,
                    default_value=None,
                    value_type=str,
                    is_secret=False,
                    file_location="/fake/path/to/file.txt",
                )
            ]

            loader = ConfigLoaderImplementation.create()
            result = loader.load_values(attributes)
            if result.is_error():
                logger.error(result.get_error())
            assert result.is_ok()

            assert loader.get_str(ENV_MY_STRING) == file_content
            m.assert_called_once_with("/fake/path/to/file.txt", "r")

    def test_fail_config_load_from_file(self):
        attributes: list[ConfigAttribute[Any]] = [
            FileConfigAttribute(
                name=ENV_MY_STRING,
                default_value=None,
                value_type=str,
                is_secret=False,
                file_location="/fake/path/to/file.txt",
            )
        ]

        loader = ConfigLoaderImplementation.create()
        result = loader.load_values(attributes)
        assert result.is_error()

    def test_successful_config_load_with_env(self):
        with patch.dict(
            os.environ,
            {
                ENV_MY_STRING: "hello",
                ENV_MY_INT: "42",
                ENV_MY_BOOL: "true",
                ENV_MY_FLOAT: "3.14",
            },
        ):
            attributes: list[ConfigAttribute[Any]] = [
                EnvConfigAttribute(
                    name=ENV_MY_STRING,
                    default_value=None,
                    value_type=str,
                    is_secret=False,
                ),
                EnvConfigAttribute(
                    name=ENV_MY_INT, default_value=None, value_type=int, is_secret=False
                ),
                EnvConfigAttribute(
                    name=ENV_MY_BOOL,
                    default_value=None,
                    value_type=bool,
                    is_secret=False,
                ),
                EnvConfigAttribute(
                    name=ENV_MY_FLOAT,
                    default_value=None,
                    value_type=float,
                    is_secret=False,
                ),
            ]
            loader = ConfigLoaderImplementation.create()
            result = loader.load_values(attributes)
            if result.is_error():
                logger.error(result.get_error())
            assert result.is_ok()

            assert loader.get_str(ENV_MY_STRING) == "hello"
            assert loader.get_int(ENV_MY_INT) == 42
            assert loader.get_bool(ENV_MY_BOOL) is True
            assert abs(loader.get_float(ENV_MY_FLOAT) - 3.14) < 1e-9

    def test_secret_logging(self):
        with patch.dict(
            os.environ,
            {
                ENV_MY_STRING: "hello",
                ENV_MY_INT: "42",
            },
        ):
            attributes: list[ConfigAttribute[Any]] = [
                EnvConfigAttribute(
                    name=ENV_MY_STRING,
                    default_value=None,
                    value_type=str,
                    is_secret=False,
                ),
                EnvConfigAttribute(
                    name=ENV_MY_INT, default_value=None, value_type=int, is_secret=True
                ),
            ]
            loader = ConfigLoaderImplementation.create()
            result = loader.load_values(attributes)
            if result.is_error():
                logger.error(result.get_error())
            assert result.is_ok()

            # should not raise when toggling secret logging
            loader.log_loaded_values(log_secrets=False)
            loader.log_loaded_values(log_secrets=True)

            assert loader.get_str(ENV_MY_STRING) == "hello"
            assert loader.get_int(ENV_MY_INT) == 42

    def test_config_load_uses_default_if_env_missing(self):
        attributes: list[ConfigAttribute[Any]] = [
            EnvConfigAttribute(
                name=ENV_DEFAULTED_STRING,
                default_value="default",
                value_type=str,
                is_secret=False,
            ),
        ]
        loader = ConfigLoaderImplementation.create()
        result = loader.load_values(attributes)
        if result.is_error():
            logger.error(result.get_error())

        assert loader.get_str(ENV_DEFAULTED_STRING) == "default"

    def test_config_load_fails_if_no_env_and_no_default(self):
        attributes: list[ConfigAttribute[Any]] = [
            EnvConfigAttribute(
                name=ENV_MISSING_VAR,
                default_value=None,
                value_type=str,
                is_secret=False,
            ),
        ]
        loader = ConfigLoaderImplementation.create()
        result = loader.load_values(attributes)
        assert result.is_error()
        error = result.get_error()
        assert isinstance(error, NoKeyException)

    def test_get_instance_returns_same_loader(self):
        with patch.dict(os.environ, {ENV_TEST_KEY: "true"}):
            attributes: list[ConfigAttribute[Any]] = [
                EnvConfigAttribute(
                    name=ENV_TEST_KEY,
                    default_value=None,
                    value_type=bool,
                    is_secret=False,
                )
            ]
            loader = ConfigLoaderImplementation.create()
            result = loader.load_values(attributes)
            if result.is_error():
                logger.error(result.get_error())
            assert result.is_ok()

            instance1 = ConfigLoaderImplementation.Instance()
            instance2 = ConfigLoaderImplementation.Instance()
            assert instance1 is instance2
            assert instance1.get_bool(ENV_TEST_KEY) is True

    def test_invalid_cast_returns_error(self):
        # Casting "not_a_number" to int should produce a ValueError (or similar)
        with patch.dict(os.environ, {ENV_BAD_INT: "not_a_number"}):
            attributes: list[ConfigAttribute[Any]] = [
                EnvConfigAttribute(
                    name=ENV_BAD_INT,
                    default_value=None,
                    value_type=int,
                    is_secret=False,
                )
            ]
            loader = ConfigLoaderImplementation.create()
            result = loader.load_values(attributes)
            assert result.is_error()
            error = result.get_error()
            assert isinstance(error, Exception)  # usually ValueError

    def test_str_to_bool_with_invalid_string_fails(self):
        # str_to_bool("maybe") should raise -> loader returns Err(ValueError)
        with patch.dict(os.environ, {ENV_BOOL_KEY: "maybe"}):
            attributes: list[ConfigAttribute[Any]] = [
                EnvConfigAttribute(
                    name=ENV_BOOL_KEY,
                    default_value=None,
                    value_type=bool,
                    is_secret=False,
                )
            ]
            loader = ConfigLoaderImplementation.create()
            result = loader.load_values(attributes)
            assert result.is_error()
            error = result.get_error()
            assert isinstance(error, Exception)  # usually ValueError

    def test_get_model_parses_json_correctly(self):
        """get_model should round-trip a FileConfigObject that was stored as JSON."""
        obj = FileConfigObject[ExampleSettings](
            id="abc123",
            stored_config=ExampleSettings(foo="spam", bar=42),
        )
        json_str = obj.model_dump_json()

        with patch.dict(os.environ, {ENV_MY_STRING: json_str}):
            attributes = [
                EnvConfigAttribute(
                    name=ENV_MY_STRING,
                    default_value=None,
                    value_type=str,
                    is_secret=False,
                )
            ]
            loader = ConfigLoaderImplementation.create()
            assert loader.load_values(attributes).is_ok()
            loaded_obj = loader.get_model(ENV_MY_STRING, ExampleSettings)

        assert loaded_obj == obj

    def test_write_config_writes_expected_json(self):
        """write_config should dump the model to the target file path."""
        obj = FileConfigObject[ExampleSettings](
            id="abc123",
            stored_config=ExampleSettings(foo="eggs", bar=7),
        )
        attr = FileConfigAttribute(
            name="EXAMPLE_FILE",
            default_value=None,
            value_type=str,
            is_secret=False,
            file_location="/fake/path/config.json",
        )

        m = mock_open()
        # ensure Instance exists and initialized
        ConfigLoaderImplementation.create()

        with patch("builtins.open", m):
            res = ConfigLoaderImplementation.Instance().write_config(attr, obj)

        assert res.is_ok()
        m.assert_called_once_with("/fake/path/config.json", "w+")
        m().write.assert_called_once_with(obj.model_dump_json(indent=2))

    def test_write_config_returns_error_on_failure(self):
        """If the file cannot be opened, write_config should surface the error."""
        obj = FileConfigObject[ExampleSettings](
            id="abc123",
            stored_config=ExampleSettings(foo="toast", bar=3),
        )
        attr = FileConfigAttribute(
            name="EXAMPLE_FILE",
            default_value=None,
            value_type=str,
            is_secret=False,
            file_location="/fake/path/config.json",
        )

        # ensure Instance exists and initialized
        ConfigLoaderImplementation.create()

        with patch("builtins.open", side_effect=IOError("disk full")):
            res = ConfigLoaderImplementation.Instance().write_config(attr, obj)

        assert res.is_error()
        assert isinstance(res.get_error(), IOError)
