from typing import Any
from core.config_loader import ConfigAttribute, EnvConfigAttribute

OBSERVE_DIR = "OBSERVE_DIR"
FILE_TYPES_TO_OBSERVE = "FILE_TYPES_TO_OBSERVE"

API_VERSION = "0.2.0"
API_NAME = "file-uploader-prefrect-deployment"


SETTINGS: list[ConfigAttribute[Any]] = [
    EnvConfigAttribute(
        name=OBSERVE_DIR, default_value="./files", value_type=str, is_secret=False
    ),
    EnvConfigAttribute(
        name=FILE_TYPES_TO_OBSERVE,
        default_value="pdf",
        value_type=str,
        is_secret=False,
    ),
]
