from typing import Any
from core.config_loader import ConfigAttribute, EnvConfigAttribute

EMBEDDING_SIZE = "EMBEDDING_SIZE"
EMBEDDING_HOST = "EMBEDDING_HOST"
EMBEDDING_MODEL = "EMBEDDING_MODEL"
IS_EMBEDDING_HOST_SECURE = "IS_EMBEDDING_HOST_SECURE"

EMBEDDING_DOC_PROMPT_NAME = "EMBEDDING_DOC_PROMPT_NAME"
EMBEDDING_QUERY_PROMPT_NAME = "EMBEDDING_QUERY_PROMPT_NAME"
EMEDDING_NORMALIZE = "EMEDDING_NORMALIZE"
TRUNCATE = "TRUNCATE"
TRUNCATE_DIRECTION = "TRUNCATE_DIRECTION"

SETTINGS_HOST: list[ConfigAttribute[Any]] = [
    EnvConfigAttribute(
        name=EMBEDDING_HOST,
        default_value=None,
        value_type=str,
        is_secret=False,
    ),
    EnvConfigAttribute(
        name=IS_EMBEDDING_HOST_SECURE,
        default_value=False,
        value_type=bool,
        is_secret=False,
    ),
]

SETTINGS_MODEL: list[ConfigAttribute[Any]] = [
    EnvConfigAttribute(
        name=EMBEDDING_MODEL,
        default_value=None,
        value_type=str,
        is_secret=False,
    ),
    EnvConfigAttribute(
        name=EMEDDING_NORMALIZE,
        default_value=True,
        value_type=bool,
        is_secret=False,
    ),
    EnvConfigAttribute(
        name=TRUNCATE,
        default_value=True,
        value_type=bool,
        is_secret=False,
    ),
    EnvConfigAttribute(
        name=TRUNCATE_DIRECTION,
        default_value="right",
        value_type=str,
        is_secret=False,
    ),
    #
    EnvConfigAttribute(
        name=EMBEDDING_DOC_PROMPT_NAME,
        default_value="",
        value_type=str,
        is_secret=False,
    ),
    EnvConfigAttribute(
        name=EMBEDDING_QUERY_PROMPT_NAME,
        default_value="",
        value_type=str,
        is_secret=False,
    ),
    EnvConfigAttribute(
        name=EMBEDDING_SIZE,
        default_value=1024,
        value_type=int,
        is_secret=False,
    ),
]

SETTINGS_ALL: list[ConfigAttribute[Any]] = [*SETTINGS_MODEL, *SETTINGS_HOST]
