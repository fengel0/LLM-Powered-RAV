from typing import Any
from core.config_loader import ConfigAttribute, EnvConfigAttribute, FileConfigAttribute

ENABLED_IMAGE_DESCRIPTION = "ENABLED_IMAGE_DESCRIPTION"

SYSTEM_PROMPT = "SYSTEM_PROMPT"
PROMPT = "PROMPT"

FILE_CONVERTER_API = "FILE_CONVERTER_API"
REQUEST_TIMEOUT_IN_SECONDS = "REQUEST_TIME_OUT"

API_VERSION = "0.2.0"
API_NAME = "file-converter-prefrect-deployment"


SETTINGS: list[ConfigAttribute[Any]] = [
    EnvConfigAttribute(
        name=FILE_CONVERTER_API, default_value=None, value_type=str, is_secret=False
    ),
    EnvConfigAttribute(
        name=REQUEST_TIMEOUT_IN_SECONDS,
        default_value=6000,
        value_type=int,
        is_secret=False,
    ),
    FileConfigAttribute(
        name=PROMPT,
        default_value=None,
        value_type=str,
        is_secret=False,
        file_location="./prompts/prompt_image_description.txt",
    ),
    FileConfigAttribute(
        name=SYSTEM_PROMPT,
        default_value=None,
        file_location="./prompts/system_prompt_image_description.txt",
        value_type=str,
        is_secret=False,
    ),
    EnvConfigAttribute(
        name=ENABLED_IMAGE_DESCRIPTION,
        default_value=False,
        value_type=bool,
        is_secret=False,
    ),
]
