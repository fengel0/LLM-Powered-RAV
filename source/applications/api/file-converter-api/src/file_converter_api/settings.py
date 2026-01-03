from core.config_loader import ConfigAttribute, EnvConfigAttribute
from typing import Any

DEVICE = "DEVICE"

API_VERSION = "0.2.0"
API_NAME = "file-converter-api"

SETTINGS: list[ConfigAttribute[Any]] = [
    EnvConfigAttribute(
        name=DEVICE, default_value="cpu", value_type=str, is_secret=False
    ),
]
