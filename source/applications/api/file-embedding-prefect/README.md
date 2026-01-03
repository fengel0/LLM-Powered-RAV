# File-Embedding Prefect – RAG-Ready Embedding Service

---

### Overview  
The project provides a **Prefect-based orchestration layer** that loads embedding-related configuration, starts the appropriate RAG (Retrieval-Augmented Generation) pipelines, and executes file-embedding tasks on demand. Two embedding back-ends are supported:

* **Vector-only embedding** – simple dense/sparse vector embeddings  
* **Hippo-RAG graph embedding** – synonym/edge-aware graph-enhanced embeddings

The service is fully environment-driven and integrates smoothly with S3, PostgreSQL, Qdrant, Neo4j, and OpenTelemetry.

---

### Key Features  

| Feature | Description |
|---------|-------------|
| **Config-driven startup** | All settings (model names, chunk sizes, API hosts, etc.) are read from environment variables or optional JSON configuration files. |
| **Dual embedding modes** | Selectable via `EMBEDDING_IMPLEMENTATION` (`vector` or `hippo_rag`). |
| **Prefect task orchestration** | Embedding tasks (`embedd_file`, `embedd_file_`) are wrapped in Prefect with retries and controlled shutdown/startup. |
| **Scalable concurrency** | `PARALLEL_REQUESTS` drives Prefect’s `ConcurrencyLimitConfig`. |
| **Observability** | Optional OpenTelemetry tracing. |
| **Highly extensible** | Supports advanced flags (`TEMPERATUR`, `SYNONYME_EDEGE_TOP_N`, etc.). |
| **End-to-end tests** | Validating both simple and Hippo-RAG startup paths. |

---

### Use Cases  

* Bulk embedding of document collections  
* Knowledge-graph enriched RAG pipelines  
* Multi-model embedding orchestration  
* Enterprise-grade embedding workflows with PostgreSQL + S3 + Qdrant + Neo4j  

---

## Environment File (`.env`)

The file-embedding-prefect service is entirely configured through environment variables.  
The following `.env` template captures the settings required for both **vector embedding** and **Hippo-RAG graph embedding** modes.

### Logging

```
LOG_LEVEL=info
LOG_SECRETS=true
```

### Prefect

```
PREFECT_API_URL=http://0.0.0.0:4200/api
```

### Embedding Mode

```
# vector  OR  hippo_rag
EMBEDDING_IMPLEMENTATION=vector
```

### Parallelism

```
PARALLEL_REQUESTS=4
```

### Chunking

```
CHUNK_SIZE=2048
CHUNK_OVERLAB=128
```

### Embedding Models

```
EMBEDDING_MODEL=text-embedding-3-large
SPARSE_MODEL=bm25-sparse
EMEDDING_NORMALIZE=false
EMBEDDING_SIZE=1536
TRUNCATE=true
TRUNCATE_DIRECTION=right
DOCUMENT_LANGUAGE=en
```

### Prompt Configuration

```
EMBEDDING_DOC_PROMPT_NAME=doc_prompt.txt
EMBEDDING_QUERY_PROMPT_NAME=query_prompt.txt
```

### LLM / Embedding Hosts

```
EMBEDDING_HOST=http://embedding-service:8000
IS_EMBEDDING_HOST_SECURE=false

RERANK_HOST=http://rerank-service:8001
```

### S3 Storage

```
S3_HOST=http://minio:9000
S3_ACCESS_KEY=minio
S3_SECRET_KEY=minio123
S3_SESSION_KEY=
S3_IS_SECURE=false
```

### PostgreSQL

```
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
POSTGRES_DATABASE=embedding-db
POSTGRES_USER=root
POSTGRES_PASSWORD=password
```

### Qdrant Vector Store

```
QDRANT_HOST=http://qdrant:6333
QDRANT_PORT=6333
QDRANT_API_KEY=
QDRANT_GRPC_PORT=6334
QDRANT_PREFER_GRPC=true
VECTOR_COLLECTION=documents
VECTOR_BATCH_SIZE=64
```

### Neo4j (Hippo-RAG Only)

```
NEO4J_HOST=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
```

### Hippo-RAG Additional Settings

```
TEMPERATUR=0.3
LLM_REQUEST_TIMEOUT=60
SYNONYME_EDEGE_TOP_N=5
SYNONYMY_EDGE_SIM_THRESHOLD=0.35
DOES_SUPPORT_STRUCTURED_OUTPUT=false
QUED_TASKS=128
```

### OpenAI / LLM Provider (Optional)

```
OPENAI_HOST=http://openai-service:8080
OPENAI_MODEL=gpt-4o
```

### OpenTelemetry

```
OTEL_HOST=127.0.0.1:4317
OTEL_ENABLED=true
OTEL_INSECURE=true
```

---

Also note:  
The effective resolved configuration is persisted at runtime under:

```
/config/embedding_config.json
```

This file reflects the *active* configuration (after merging environment variables and file-based overrides).

---

### Deployment Example  
*(omitted here for brevity — use the large docker-compose block from your original text)*  

---

### How It Works (High-Level Flow)

1. **Configuration Load** – `ConfigLoaderImplementation.Instance()` reads env + file config.  
2. **Application Startup** – Constructs `RAGEmbeddingConfigLoaderApplication`.  
3. **Embedding Configuration** – Runs either `update_simple` or `update_graph`.  
4. **Prefect Flow Registration** – Builds a flow that reacts to `FILE_CONVERTED` events.  
5. **Task Execution** – `embedd_file` handles startup → embedding → shutdown.

---

### Testing  

End-to-end tests validate both simple and Hippo-RAG configurations.

