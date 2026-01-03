from typing import Any
from core.config_loader import ConfigAttribute, EnvConfigAttribute

UPDATE_MESSAGE = "UPDATE_MESSAGE"


SETTINGS: list[ConfigAttribute[Any]] = [
    EnvConfigAttribute(
        name=UPDATE_MESSAGE, default_value=None, value_type=str, is_secret=False
    ),
]
