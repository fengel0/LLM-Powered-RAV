from typing import Any
from core.config_loader import ConfigAttribute, EnvConfigAttribute

WORKERS = "WORKERS"
PORT = "PORT"
PATH_PREFIX = "PATH_PREFIX"


SETTINGS: list[ConfigAttribute[Any]] = [
    EnvConfigAttribute(name=WORKERS, default_value=1, value_type=int, is_secret=False),
    EnvConfigAttribute(name=PORT, default_value=8000, value_type=int, is_secret=False),
    EnvConfigAttribute(
        name=PATH_PREFIX, default_value="", value_type=str, is_secret=False
    ),
]
