from typing import Any
from core.config_loader import ConfigAttribute, EnvConfigAttribute


# --- Vector DB Config Constants ---
QDRANT_HOST = "QDRANT_HOST"
QDRANT_PORT = "QDRANT_PORT"
QDRANT_API_KEY = "QDRANT_API_KEY"
QDRANT_GRPC_PORT = "QDRANT_GRPC_PORT"
QDRANT_PREFER_GRPC = "QDRANT_PREFER_GRPC"
VECTOR_COLLECTION = "VECTOR_COLLECTION"
SPARSE_MODEL = "SPARSE_MODEL"
VECTOR_BATCH_SIZE = "VECTOR_BATCH_SIZE"


SETTINGS: list[ConfigAttribute[Any]] = [
    #
    EnvConfigAttribute(
        name=QDRANT_HOST, default_value=None, value_type=str, is_secret=False
    ),
    EnvConfigAttribute(
        name=QDRANT_PORT, default_value=6333, value_type=int, is_secret=False
    ),
    EnvConfigAttribute(
        name=QDRANT_API_KEY, default_value="", value_type=str, is_secret=True
    ),
    EnvConfigAttribute(
        name=QDRANT_GRPC_PORT, default_value=6333, value_type=int, is_secret=False
    ),
    EnvConfigAttribute(
        name=QDRANT_PREFER_GRPC, default_value=True, value_type=bool, is_secret=False
    ),
    EnvConfigAttribute(
        name=VECTOR_BATCH_SIZE, default_value=20, value_type=int, is_secret=False
    ),
    EnvConfigAttribute(
        name=SPARSE_MODEL, default_value="Qdrant/bm25", value_type=str, is_secret=False
    ),
    EnvConfigAttribute(
        name=VECTOR_COLLECTION,
        default_value="default_collection",
        value_type=str,
        is_secret=False,
    ),
]
