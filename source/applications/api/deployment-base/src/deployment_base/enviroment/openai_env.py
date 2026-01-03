from core.config_loader import ConfigAttribute, EnvConfigAttribute
from typing import Any


OPENAI_MODEL = "OPENAI_MODEL"
OPENAI_KEY = "OPENAI_KEY"
TEMPERATUR = "TEMPERATUR"
MAX_TOKENS = "MAX_TOKENS"
OPENAI_HOST = "OPENAI_HOST"
LLM_REQUEST_TIMEOUT = "LLM_REQUEST_TIMEOUT"
DOES_SUPPORT_STRUCTURED_OUTPUT = "DOES_SUPPORT_STRUCTURED_OUTPUT"


SETTINGS_HOST: list[ConfigAttribute[Any]] = [
    EnvConfigAttribute(
        name=OPENAI_HOST, default_value="", value_type=str, is_secret=False
    ),
    EnvConfigAttribute(
        name=OPENAI_KEY, default_value="", value_type=str, is_secret=False
    ),
    EnvConfigAttribute(
        name=LLM_REQUEST_TIMEOUT, default_value=60, value_type=int, is_secret=False
    ),
]

SETTINGS_MODEL: list[ConfigAttribute[Any]] = [
    EnvConfigAttribute(
        name=MAX_TOKENS,
        default_value=8192,
        value_type=int,
        is_secret=False,
    ),
    #
    EnvConfigAttribute(
        name=OPENAI_MODEL, default_value="", value_type=str, is_secret=False
    ),
    EnvConfigAttribute(
        name=OPENAI_KEY, default_value="", value_type=str, is_secret=True
    ),
    EnvConfigAttribute(
        name=TEMPERATUR, default_value=0.5, value_type=float, is_secret=False
    ),
    EnvConfigAttribute(
        name=DOES_SUPPORT_STRUCTURED_OUTPUT,
        default_value=True,
        value_type=bool,
        is_secret=False,
    ),
]

SETTINGS: list[ConfigAttribute[Any]] = [*SETTINGS_HOST, *SETTINGS_MODEL]
