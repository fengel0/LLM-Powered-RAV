import os

EMBEDDING_HOST = os.getenv("EMBEDDING_HOST", "")
EMBEDDING_MODEL = os.getenv("EMBEDDING_HOST", "dummy")
EMBEDDING_SIZE = int(os.getenv("EMBEDDING_SIZE", "0"))
