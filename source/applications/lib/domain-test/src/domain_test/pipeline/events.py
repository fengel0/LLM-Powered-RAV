from enum import Enum


class EventName(Enum):
    FILE_CREATED_UPDATES = "file-created-updated"
    FILE_CONVERTED = "file-converted"
    FILE_EMBEDDED = "file-embedded"
    DATASET_UPLOADED = "dataset-uploaded"
    ASK_RAG_SYSTEM = "ask-rag-system"
    EVALUATE_RAG_SYSTEM = "evaluate-rag-system"
