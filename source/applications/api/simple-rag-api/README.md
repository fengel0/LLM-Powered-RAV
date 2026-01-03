# simple‑rag‑api – OpenAI‑compatible Retrieval‑Augmented Generation Service  

## Overview  

**simple‑rag‑api** is a FastAPI‑based web service that exposes an OpenAI‑compatible chat‑completion endpoint backed by a customizable Retrieval‑Augmented Generation (RAG) pipeline. The API accepts standard chat‑completion requests, performs document retrieval, runs the selected language model, and streams the generated response while optionally returning the retrieved context nodes. The project is designed for easy integration into existing applications that already consume OpenAI‑style APIs, while allowing full control over the underlying RAG components.  

## Key Features  

| Feature | Description |
|---------|-------------|
| **OpenAI‑compatible endpoint** | Provides `/v1/chat/completions` that follows the OpenAI chat‑completion schema, making it a drop‑in replacement for clients that expect the OpenAI API. The implementation is summarised in the code base as “OpenAI‑compatible chat completion endpoint using custom RAG backend” [3]. |
| **Pluggable RAG back‑end** | Supports multiple RAG implementations (HippoRAG, LlamaIndexRAG, etc.) that can be selected via configuration. |
| **Configurable models & projects** | Model, configuration, and project identifiers are supplied in the request payload, allowing dynamic selection of LLMs, embedding services, and retrieval settings. |
| **In‑memory context store** | A bounded, thread‑safe store with optional TTL keeps per‑conversation context data and can evict expired or excess entries automatically. The store is described as “A simple bounded, thread‑safe in‑memory store with optional TTL” [2]. |
| **Streaming responses** | Generates partial responses as server‑sent events, enabling real‑time UI updates. |
| **Extensible settings** | Environment‑driven configuration (e.g., `CONTEXT_MAX_ITEMS`, `CONTEXT_TTL_SECONDS`, default project and config IDs) is defined in `simple_rag_api/settings.py` [8]. |
| **Modular architecture** | Separate modules for API routing (`rag_api.py`), application startup (`application_startup.py`), data models (`model.py`), and static frontend assets (HTML, CSS, JS). |
| **Observability** | Integrated logging and optional OpenTelemetry support via the core logger. |

## Use Cases  

- **Chat‑bot interfaces** – Build conversational agents that answer queries using both LLM generation and up‑to‑date knowledge from a vector store.  
- **Enterprise knowledge bases** – Provide employees with instant, context‑aware answers drawn from internal documents, manuals, or support tickets.  
- **RAG research & prototyping** – Experiment with different retrieval strategies, embedding providers, and LLMs without changing client code.  
- **Multi‑tenant** – Serve multiple projects or configurations from a single deployment by switching `project_id` and `config_id` in the request.  

## Extending the Project  

- **Add new RAG implementations** – Implement the `RAGLLM` interface and register it in `application_startup.py`.  
- **Customize retrieval** – Modify or extend the configuration overrides in `config_override.py` to tune top‑k, weighting, or reranking behavior.  
- **Persist context** – Replace the in‑memory `ContextStore` with a Redis or database‑backed store for durability across restarts.  

## Environment File (`.env`)

The simple-rag-api service is configured entirely via environment variables.  
The following `.env` template covers logging, RAG backend settings, vector/graph DB access, model selection, and API behavior.

### Logging

```
LOG_LEVEL=info
LOG_SECRETS=true
TZ=Europe/Berlin
```

### RAG Mode

```
# One of: hippo-rag | subquestion | hybrid | simple
RAG_TYPE=hippo-rag
LLM_REQUEST_TIMEOUT=120
```

### PostgreSQL

```
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
POSTGRES_DATABASE=rag-db
POSTGRES_USER=root
POSTGRES_PASSWORD=password-v2
```

### Neo4j (graph-based RAG)

```
NEO4J_HOST=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
```

### Qdrant (vector store)

```
QDRANT_HOST=127.0.0.1
QDRANT_PORT=6333
QDRANT_GRPC_PORT=6334
QDRANT_API_KEY=your-qdrant-key
QDRANT_PREFER_GRPC=true
VECTOR_COLLECTION=documents
VECTOR_BATCH_SIZE=32
```

### Reranking

```
RERANK_API_KEY=your-reranker-key
RERANK_HOST=http://rerank:8080
```

### Embedding Service

```
EMBEDDING_HOST=http://embedding:8080
IS_EMBEDDING_HOST_SECURE=false
```

### LLM Backend

```
OPENAI_HOST=http://llm:8000
DEFAULT_LLM_MODEL=gpt-oss:120b
LLMS_AVAILABALE=gpt-oss:120b,llama3.3,deepseek-r1:70b
```

### Default Project/Config

```
DEFAULT_CONFIG=e93f83eb-d3ad-4211-ab88-fdf955ed0fa3
```

### API Runtime Settings

```
RUNNING_HOST=https://we.ai.fh-erfurt.de
PATH_PREFIX=/chat-ui
PORT=8000
WORKERS=1
```

### OpenTelemetry (optional)

```
OTEL_ENABLED=true
OTEL_HOST=127.0.0.1:4317
OTEL_INSECURE=true
```

---

### Note on Search Support

The API now includes a `/v1/chat/search` endpoint extension (see `rag_api.py`).  
It performs retrieval-only, returning ranked context chunks without LLM generation.  
This allows clients to inspect retrieved evidence directly.
