from typing import Any
from core.config_loader import ConfigAttribute, EnvConfigAttribute

S3_HOST = "S3_HOST"
S3_ACCESS_KEY = "S3_ACCESS_KEY"
S3_SECRET_KEY = "S3_SECRET_KEY"
S3_SESSION_KEY = "S3_SESSION_KEY"
S3_IS_SECURE = "S3_IS_SECURE"


SETTINGS: list[ConfigAttribute[Any]] = [
    EnvConfigAttribute(
        name=S3_HOST, default_value=None, value_type=str, is_secret=False
    ),
    EnvConfigAttribute(
        name=S3_ACCESS_KEY, default_value=None, value_type=str, is_secret=True
    ),
    EnvConfigAttribute(
        name=S3_SECRET_KEY, default_value=None, value_type=str, is_secret=True
    ),
    EnvConfigAttribute(
        name=S3_SESSION_KEY, default_value="", value_type=str, is_secret=True
    ),
    EnvConfigAttribute(
        name=S3_IS_SECURE, default_value=False, value_type=bool, is_secret=False
    ),
]
