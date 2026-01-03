from typing import Any
from core.config_loader import ConfigAttribute, EnvConfigAttribute, FileConfigAttribute

EMBEDDING_IMPLEMENTATION = "EMBEDDING_IMPLEMENTATION"
PARALLEL_REQUESTS = "PARALLEL_REQUESTS"
QUED_TASKS = "QUED_TASKS"
PRE_ALLOCATED_TASK = "PRE_ALLOCATED_TASK"
DOCUMENT_LANGUAGE = "DOCUMENT_LANGUAGE"
CONSIDER_IMAGES = "CONSIDER_IMAGES"
# EMBEDDING_TYPE = "EMBEDDING_TYPE"
EMBEDDING_CONFIG = "EMBEDDING_CONFIG"


API_VERSION = "0.2.0"
API_NAME = "file-embedding-prefect"


SETTINGS: list[ConfigAttribute[Any]] = [
    EnvConfigAttribute(
        name=EMBEDDING_IMPLEMENTATION,
        default_value="vector",
        value_type=str,
        is_secret=False,
    ),
    EnvConfigAttribute(
        name=DOCUMENT_LANGUAGE,
        default_value="en",
        value_type=str,
        is_secret=False,
    ),
    #
    EnvConfigAttribute(
        name=PARALLEL_REQUESTS, default_value=1, value_type=int, is_secret=False
    ),
    EnvConfigAttribute(
        name=QUED_TASKS, default_value=5, value_type=int, is_secret=False
    ),
    EnvConfigAttribute(
        name=PRE_ALLOCATED_TASK, default_value=10, value_type=int, is_secret=False
    ),
    EnvConfigAttribute(
        name=CONSIDER_IMAGES, default_value=False, value_type=bool, is_secret=False
    ),
    FileConfigAttribute(
        name=EMBEDDING_CONFIG,
        default_value="",
        value_type=str,
        is_secret=False,
        file_location="./config/embedding_config.json",
    ),
]
