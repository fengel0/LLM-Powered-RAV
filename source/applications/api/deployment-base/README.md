
# README  

## Overview  
**deployment‑base** is a modular framework that orchestrates the startup, configuration, and shutdown of all services required for applications. 
It brings together LLM providers, embedding models, vector stores, graph databases, relational databases, object storage, and logging/observability into a single, extensible pipeline. 
The project is packaged as a Python library (see `pyproject.toml` for metadata) and is intended to be used as the foundation for building production‑grade RAG services [1].

## Key Features  

| Feature | Description |
|---------|-------------|
| **Unified Application Lifecycle** | An abstract `Application` class defines a singleton‑based lifecycle with synchronous and asynchronous components, handling start‑up and graceful shutdown for each service [2]. |
| **Pluggable Startup Sequences** | Separate startup classes implement `SyncLifetimeReg` or `AsyncLifetimeReg` for each dependency (e.g., logger, vector store, LLM client, embedding service, database, MinIO, Neo4j). This makes it easy to add or replace components. |
| **Environment‑Driven Configuration** | All configurable values are declared as `EnvConfigAttribute` objects in dedicated modules (e.g., `qdrant_env`, `postgres_env`, `minio_env`, `log_env`). The framework loads them via a `ConfigLoader`, providing type‑safe access to strings, ints, booleans, etc.|
| **Observability Integration** | Optional OpenTelemetry support can be enabled through environment variables, automatically configuring tracing, metrics, and logging for the whole stack. |
| **Support for Multiple RAG Strategies** | Includes ready‑to‑use startup sequences for HippoRAG, LlamaIndex, simple RAG, and sub‑question RAG pipelines, each wiring the appropriate embedding, vector store, reranker, and LLM components. |
| **Extensible Dependency Management** | Uses `hatchling`/`uv` for building and workspace‑linked dependencies, allowing local development of core libraries such as `core`, `hippo‑rag‑graph`, `hippo‑rag‑vectore‑store`, etc. |

## Architecture  

1. **Core Application Engine** – `Application` (abstract) provides the singleton pattern, component registration (`_with_component`, `_with_acomponent`), and methods to start synchronous and asynchronous components [2].  
2. **Configuration Loader** – Reads environment variables and optional files, validates types, and makes them available to startup sequences.  
3. **Startup Sequences** – Each external service has a dedicated class:  
   * `LoggerStartupSequence` configures logging and OpenTelemetry.  
   * `HippoRAGQdrantStartupSequence` sets up a Qdrant vector store for HippoRAG.  
   * `LlamaIndexQdrantStartupSequence` and `LlamaIndexStartupSequence` configure LlamaIndex with Qdrant and OpenAI.  
   * `PostgresStartupSequence`, `Neo4jStartupSequence`, `MinioStartupSequence` initialize relational DB, graph DB, and S3‑compatible object storage.  
   * Embedding and reranker services are started in the respective RAG pipelines (e.g., `GrpcEmbeddClient`, `CohereHttpRerankerClient`).  
4. **RAG Pipelines** – High‑level builder configurations (`LlamaIndexSimpleBuilderConfig`, `LlamaIndexSubQuestionBuilderConfig`) combine the previously initialized components into ready‑to‑use RAG systems, handling prompt templates, top‑N retrieval settings, and model parameters.

## Configuration  

All settings are declared as environment variables. Example groups include:

* **Logging & Observability** – `LOG_LEVEL`, `OTEL_ENABLED`, `OTEL_HOST`, `OTEL_INSECURE`.  
* **Vector Store (Qdrant)** – `QDRANT_HOST`, `QDRANT_PORT`, `QDRANT_API_KEY`, `VECTOR_COLLECTION`.  
* **Database** – `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD`.  
* **Graph DB (Neo4j)** – `NEO4J_HOST`, `NEO4J_USER`, `NEO4J_PASSWORD`.  
* **Object Storage (MinIO/S3)** – `S3_HOST`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_IS_SECURE`.  
* **LLM Providers** – `OPENAI_HOST`, `OPENAI_KEY`, `OPENAI_MODEL`, `OLLAMA_HOST`.  
* **Embedding Service** – `EMBEDDING_HOST`, `EMBEDDING_MODEL`, `EMBEDDING_SIZE`, `EMBEDDING_DOC_PROMPT_NAME`, `EMBEDDING_QUERY_PROMPT_NAME` .  
* **Reranker** – `RERANK_HOST`, `RERANK_API_KEY`, `RERANK_MODEL`.

The `ConfigLoader` validates each variable against the declared type and default value, raising errors early if required settings are missing.

## Use Cases  

The framework is designed for any application that needs to combine large language models with external knowledge sources. Typical scenarios include:

* **Enterprise Knowledge Bases** – Connect a Neo4j graph of internal documents with a Qdrant vector store and an OpenAI LLM to answer employee queries.  
* **Customer Support Chatbots** – Use MinIO for storing attachments, PostgreSQL for user data, and HippoRAG for multi‑modal retrieval and generation.  
* **Research Assistants** – Leverage sub‑question RAG to decompose complex queries, retrieve dense and sparse results, and rerank them before presenting concise answers.  

Because each component is isolated behind a well‑defined interface, teams can swap the vector store (e.g., Qdrant → Pinecone), the LLM provider (OpenAI → Ollama), or the embedding model without changing the surrounding application logic.

