from enum import Enum


class EventName(Enum):

    """
    Enum of all event names used throughout the processing pipeline.

    The events are emitted by various Prefect tasks (e.g. file upload,
    conversion, embedding, RAG query, evaluation) and are consumed by
    automations or downstream services.  Keeping the names in a single
    Enum makes it easy to reference them consistently and avoids typo‑related
    bugs.

    """

    # Emitted when a file has been created or updated and is ready for
    FILE_CREATED_UPDATES = "file-created-updated"
    # Emitted after a file has been successfully converted to the target format.
    FILE_CONVERTED = "file-converted"
    # Emitted when a file's content has been embedded and stored in the vector
    # database, making it searchable for RAG.
    FILE_EMBEDDED = "file-embedded"
    # Emitted when a dataset archive has been uploaded and is ready for
    # ingestion into the system.
    DATASET_UPLOADED = "dataset-uploaded"
    # Emitted to trigger a RAG (Retrieval‑Augmented Generation) query.
    ASK_RAG_SYSTEM = "ask-rag-system"
    # Emitted after a RAG response has been created and needs to be evaluated (e.g., correctness,
    # relevance) by the grading service.
    EVALUATE_RAG_SYSTEM = "evaluate-rag-system"
