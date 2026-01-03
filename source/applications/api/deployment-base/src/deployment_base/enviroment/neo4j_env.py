from typing import Any
from core.config_loader import ConfigAttribute, EnvConfigAttribute


NEO4J_HOST = "NEO4J_HOST"
NEO4J_USER = "NEO4J_USER"
NEO4J_PASSWORD = "NEO4J_PASSWORD"


SETTINGS: list[ConfigAttribute[Any]] = [
    EnvConfigAttribute(
        name=NEO4J_HOST,
        default_value="",
        value_type=str,
        is_secret=False,
    ),
    EnvConfigAttribute(
        name=NEO4J_USER,
        default_value="",
        value_type=str,
        is_secret=False,
    ),
    EnvConfigAttribute(
        name=NEO4J_PASSWORD,
        default_value="",
        value_type=str,
        is_secret=False,
    ),
]
