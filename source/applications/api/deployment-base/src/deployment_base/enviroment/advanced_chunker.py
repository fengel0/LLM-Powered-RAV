from typing import Any
from core.config_loader import ConfigAttribute, EnvConfigAttribute

CHUNK_SIZE = "CHUNK_SIZE"
CHUNK_OVERLAB = "CHUNK_OVERLAB"


SETTINGS: list[ConfigAttribute[Any]] = [
    EnvConfigAttribute(
        name=CHUNK_SIZE, default_value=512, value_type=int, is_secret=False
    ),
    EnvConfigAttribute(
        name=CHUNK_OVERLAB, default_value=128, value_type=int, is_secret=False
    ),
]
