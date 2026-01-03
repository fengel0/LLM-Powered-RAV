from typing import Any
from core.config_loader import ConfigAttribute, EnvConfigAttribute

API_VERSION = "0.2.0"
API_NAME = "simple-rag-api"

CONTEXT_MAX_ITEMS = "CONTEXT_MAX_ITEMS"
CONTEXT_TTL_SECONDS = "CONTEXT_TTL_SECONDS"

DEFAULT_PROJECT = "DEFAULT_PROJECT"

LLMS_AVAILABALE = "LLMS_AVAILABALE"

RUNNING_HOST = "RUNNING_HOST"

DEFAULT_SIMPLE_CONFIG = "DEFAULT_SIMPLE_CONFIG"
DEFAULT_SUB_CONFIG = "DEFAULT_SUB_CONFIG"
DEFAULT_HIP_CONFIG = "DEFAULT_HIP_CONFIG"
DEFAULT_CONFIG = "DEFAULT_CONFIG"

SETTINGS: list[ConfigAttribute[Any]] = [
    EnvConfigAttribute(
        name=LLMS_AVAILABALE, default_value=None, value_type=str, is_secret=False
    ),
    EnvConfigAttribute(
        name=CONTEXT_TTL_SECONDS,
        default_value=(24 * 3600),
        value_type=int,
        is_secret=False,
    ),
    EnvConfigAttribute(
        name=CONTEXT_MAX_ITEMS, default_value=1000, value_type=int, is_secret=False
    ),
    EnvConfigAttribute(
        name=DEFAULT_SIMPLE_CONFIG, default_value="", value_type=str, is_secret=False
    ),
    EnvConfigAttribute(
        name=DEFAULT_SUB_CONFIG, default_value="", value_type=str, is_secret=False
    ),
    EnvConfigAttribute(
        name=DEFAULT_HIP_CONFIG, default_value="", value_type=str, is_secret=False
    ),
    EnvConfigAttribute(
        name=DEFAULT_CONFIG, default_value=None, value_type=str, is_secret=False
    ),
    EnvConfigAttribute(
        name=RUNNING_HOST, default_value="", value_type=str, is_secret=False
    ),
]
