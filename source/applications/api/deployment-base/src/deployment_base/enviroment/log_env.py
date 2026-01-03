from typing import Any
from core.config_loader import ConfigAttribute, EnvConfigAttribute

LOG_LEVEL = "LOG_LEVEL"
LOG_SECRETS = "LOG_SECRETS"


OTEL_HOST = "OTEL_HOST"
OTEL_ENABLED = "OTEL_ENABLED"
OTEL_INSECURE = "OTEL_INSECURE"


SETTINGS: list[ConfigAttribute[Any]] = [
    EnvConfigAttribute(
        name=LOG_SECRETS, default_value=False, value_type=bool, is_secret=False
    ),
    EnvConfigAttribute(
        name=LOG_LEVEL, default_value="info", value_type=str, is_secret=False
    ),
    EnvConfigAttribute(
        name=OTEL_ENABLED, default_value=False, value_type=bool, is_secret=False
    ),
    EnvConfigAttribute(
        name=OTEL_HOST, default_value="", value_type=str, is_secret=False
    ),
    EnvConfigAttribute(
        name=OTEL_INSECURE, default_value=True, value_type=bool, is_secret=False
    ),
]
