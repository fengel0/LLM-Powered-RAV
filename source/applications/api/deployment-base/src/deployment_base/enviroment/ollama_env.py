from typing import Any
from core.config_loader import ConfigAttribute, EnvConfigAttribute

DEFAULT_LLM_MODEL = "DEFAULT_LLM_MODEL"
CONTEXT_WINDOW = "CONTEXT_WINDOW"
REQUEST_TIMEOUT_IN_SECONDS = "REQUEST_TIME_OUT"
OLLAMA_HOST = "OLLAMA_HOST"
TEMPERATURE = "TEMPERATURE"


SETTINGS: list[ConfigAttribute[Any]] = [
    #
    EnvConfigAttribute(
        name=REQUEST_TIMEOUT_IN_SECONDS,
        default_value=6000,
        value_type=int,
        is_secret=False,
    ),
    #
    EnvConfigAttribute(
        name=OLLAMA_HOST,
        default_value=None,
        value_type=str,
        is_secret=False,
    ),
    EnvConfigAttribute(
        name=CONTEXT_WINDOW, default_value=8192, value_type=int, is_secret=False
    ),
]
