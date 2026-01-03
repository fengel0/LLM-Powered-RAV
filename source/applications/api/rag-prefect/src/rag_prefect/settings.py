from typing import Any
from core.config_loader import ConfigAttribute, EnvConfigAttribute, FileConfigAttribute

RAG_TYPE = "RAG_TYPE"
RAG_CONFIG = "RAG_CONFIG"
RETRIVAL_CONFIG = "RETRIVAL_CONFIG"
PARALLEL_REQUESTS = "PARALLEL_REQUESTS"
EMBEDD_CONFIG_TO_USE = "EMBEDD_CONFIG_TO_USE"
RAG_CONFIG_NAME = "RAG_CONFIG_NAME"
SUPPORTE_STRUCTURED_OUTPUT = "SUPPORTE_STRUCTURED_OUTPUT"

API_VERSION = "0.2.0"
API_NAME = "rag-prefrect-deployment"


SETTINGS: list[ConfigAttribute[Any]] = [
    EnvConfigAttribute(
        name=PARALLEL_REQUESTS, default_value=1, value_type=int, is_secret=False
    ),
    EnvConfigAttribute(
        name=PARALLEL_REQUESTS, default_value=1, value_type=int, is_secret=False
    ),
    #
    EnvConfigAttribute(
        name=RAG_TYPE, default_value="", value_type=str, is_secret=False
    ),
    EnvConfigAttribute(
        name=RAG_CONFIG_NAME, default_value="", value_type=str, is_secret=False
    ),
    EnvConfigAttribute(
        name=EMBEDD_CONFIG_TO_USE, default_value=None, value_type=str, is_secret=False
    ),
    EnvConfigAttribute(
        name=SUPPORTE_STRUCTURED_OUTPUT,
        default_value=True,
        value_type=bool,
        is_secret=False,
    ),
    #
    FileConfigAttribute(
        name=RETRIVAL_CONFIG,
        default_value="",
        value_type=str,
        is_secret=False,
        file_location="./config/retrival_config.json",
    ),
    FileConfigAttribute(
        name=RAG_CONFIG,
        default_value="",
        value_type=str,
        is_secret=False,
        file_location="./config/rag_config.json",
    ),
]
