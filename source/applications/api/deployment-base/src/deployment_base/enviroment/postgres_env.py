from typing import Any
from core.config_loader import ConfigAttribute, EnvConfigAttribute

POSTGRES_HOST = "POSTGRES_HOST"
POSTGRES_PORT = "POSTGRES_PORT"
POSTGRES_DATABASE = "POSTGRES_DATABASE"
POSTGRES_USER = "POSTGRES_USER"
POSTGRES_PASSWORD = "POSTGRES_PASSWORD"


SETTINGS: list[ConfigAttribute[Any]] = [
    EnvConfigAttribute(
        name=POSTGRES_HOST, default_value=None, value_type=str, is_secret=False
    ),
    EnvConfigAttribute(
        name=POSTGRES_PORT, default_value=5432, value_type=int, is_secret=False
    ),
    EnvConfigAttribute(
        name=POSTGRES_DATABASE,
        default_value="pipline-db",
        value_type=str,
        is_secret=False,
    ),
    EnvConfigAttribute(
        name=POSTGRES_USER,
        default_value=None,
        value_type=str,
        is_secret=True,
    ),
    EnvConfigAttribute(
        name=POSTGRES_PASSWORD,
        default_value=None,
        value_type=str,
        is_secret=True,
    ),
    #
]
