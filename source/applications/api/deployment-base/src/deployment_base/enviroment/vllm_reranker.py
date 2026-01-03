from typing import Any
from core.config_loader import ConfigAttribute, EnvConfigAttribute

RERANK_MODEL = "RERANK_MODEL"
RERANK_API_KEY = "RERANK_API_KEY"
RERANK_HOST = "RERANK_HOST"


SETTINGS: list[ConfigAttribute[Any]] = [
    EnvConfigAttribute(
        name=RERANK_MODEL, default_value="", value_type=str, is_secret=False
    ),
    EnvConfigAttribute(
        name=RERANK_HOST,
        default_value=None,
        value_type=str,
        is_secret=False,
    ),
    EnvConfigAttribute(
        name=RERANK_API_KEY, default_value="", value_type=str, is_secret=False
    ),
]
