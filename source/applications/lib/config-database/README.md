# Config Database

A subproject providing persistent configuration storage for RAG (Retrieval-Augmented Generation) pipelines.  
Implements PostgreSQL-based repositories for embedding, retrieval, and system configurations following the domain-driven design used across the monorepo.

##  Overview

The **Config Database** defines and manages several key data models and repositories:

- **`RagEmbeddingConfig`** — defines how document embeddings are generated (e.g., chunk sizes, embedding models).  
- **`RagRetrievalConfig`** — defines retrieval model parameters and prompt configurations.  
- **`RagConfig`** — combines embedding + retrieval configs into a complete RAG setup.  
- **`SystemConfig`** — stores arbitrary typed configurations for other system components.

All models inherit from a shared async database abstraction layer (`BaseDatabase`) and return strongly typed `Result` objects to standardize success/error handling.

## Features

- Asynchronous PostgreSQL access  
- Hash-based deduplication of configs  
- Typed repositories for embedding, retrieval, RAG, and system-level configs  
- Integration with OpenTelemetry tracing  
- Clean DDD-inspired interface contracts (`domain.database.config.*`)  
- Full compatibility with internal `core`, `domain`, and `database` packages  

