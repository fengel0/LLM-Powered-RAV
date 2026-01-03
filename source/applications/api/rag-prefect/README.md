**RAG‑Prefect Deployment**  
*A flexible, event‑driven Retrieval‑Augmented Generation (RAG) platform built on Prefect.*

---

## Overview
RAG‑Prefect provides a configurable orchestration layer for various RAG strategies (Hippo‑RAG graph‑based, sub‑question decomposition, hybrid/simple pipelines). It loads runtime configuration, initializes the appropriate retrieval components, and exposes a Prefect‑driven automation that reacts to incoming query events and generates answers through an LLM backend.

The core entry point is `RAGConfigLoaderApplication`, which builds the application name from the selected RAG type and version [1]. Configuration values are defined through environment variables and JSON files, enabling seamless adaptation to different deployment contexts.

---

## Key Features
- **Multiple RAG Strategies** – Choose between Hippo‑RAG (graph), Sub‑Question, Hybrid, or Simple pipelines via the `RAG_TYPE` setting.  
- **Dynamic Configuration Loading** – Uses a central `ConfigLoader` to pull values from environment and JSON files (`rag_config.json`, `retrival_config.json`) [3].  
- **Prefect Automation** – An event‑triggered Prefect flow (`generate_ans`) runs with automatic retries and concurrency limits, exposing a reactive API for query handling [2].  
- **Modular Component Startup** – Startup sequences initialise vector stores (Qdrant), graph databases (Neo4j), and LLM/reranker services based on the selected RAG type [1].  
- **Extensible Prompt Management** – Update functions (`update_graph`, `update_naive`, `update_sub`) customise prompts and additional information (e.g., reranker model) for each retrieval mode [4].  
- **Observability & Scaling** – Built‑in OpenTelemetry support, configurable parallel request limits, and integration with external services (embedding, reranker, LLM providers).  
- **Docker‑Ready Deployment** – Container images can be run with a single‑service definition, injecting all required environment variables and mounting prompt/config files.

---

## Use Cases
| Scenario | How RAG‑Prefect Helps |
|---------|-----------------------|
| **Knowledge‑Graph QA** | Deploy the Hippo‑RAG configuration to query Neo4j‑backed graphs with vector similarity search in Qdrant. |
| **Complex Question Decomposition** | Use the Sub‑Question mode to break down large queries into manageable sub‑queries, improving answer relevance. |
| **Hybrid Retrieval** | Combine dense vector search with sparse keyword retrieval for balanced recall and precision. |
| **Scalable API Service** | Leverage Prefect’s concurrency limits and event‑driven flow to serve many simultaneous requests while respecting rate limits. |
| **Custom Prompt Engineering** | Update prompts via the `update_*` functions without code changes, adapting to domain‑specific language. |

---

## Configuration Highlights
- **Core Settings (settings.py)** – Define required environment variables such as `RAG_TYPE`, `RAG_CONFIG_NAME`, `EMBEDD_CONFIG_TO_USE`, and `PARALLEL_REQUESTS` [3].  
- **Retrieval & RAG Config Files** – JSON files (`retrival_config.json`, `rag_config.json`) hold model identifiers, prompts, and additional service URLs.  
- **Dynamic Prompt Loading** – `update_naive` and `update_sub` read prompts from the configuration service and inject them into the retrieval config, also attaching the selected reranker model [4].  

---

## Deployment Example (Docker Compose)
A typical deployment runs the image `rag-prefect:v02` with a set of environment variables that select the RAG type, database hosts, and external service credentials.
Volumes mount the prompts directory and the JSON configuration files into the container. The service restarts automatically unless stopped and is attached to a pre‑existing Docker network.

---

## Extending the Platform
1. **Add a New RAG Type** – Implement a startup sequence in `application_startup.py` and a corresponding `update_*` function to handle prompts and additional information.  
2. **Custom Prompts** – Place new prompt files under the `prompts/` directory and reference them via the configuration service; the update functions will automatically inject them.  
3. **Observability Enhancements** – Extend the OpenTelemetry exporter configuration in the environment variables to integrate with your monitoring stack.

---

**RAG‑Prefect** offers a robust, configurable foundation for building production‑grade RAG services, enabling rapid experimentation with different retrieval strategies while maintaining operational stability through Prefect orchestration.

## Environment File (`.env`)

RAG-Prefect loads all configuration from environment variables and JSON config files.  
The following `.env` template covers logging, RAG-type selection, vector/graph databases, LLM endpoints, reranker settings, and Prefect connectivity.

### Logging

```
LOG_LEVEL=info
LOG_SECRETS=true
TZ=Europe/Berlin
```

### RAG Mode Selection

```
# One of: hippo-rag | subquestion | hybrid
RAG_TYPE=hippo-rag
```

### PostgreSQL (metadata, retrieval state, evaluation)

```
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
POSTGRES_DATABASE=production-db
POSTGRES_USER=root
POSTGRES_PASSWORD=password-v2
```

### Neo4j (graph retrieval, Hippo-RAG)

```
NEO4J_HOST=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
```

### Qdrant (vector database)

```
QDRANT_HOST=127.0.0.1
QDRANT_PORT=6333
QDRANT_GRPC_PORT=6334
QDRANT_API_KEY=your-qdrant-key
QDRANT_PREFER_GRPC=true
VECTOR_COLLECTION=rag_vectors
VECTOR_BATCH_SIZE=32
```

### Reranker

```
RERANK_HOST=http://rerank:8080
RERANK_API_KEY=your-rerank-api-key
RERANK_MODEL=bge-reranker-base
```

### Embedding Service

```
EMBEDDING_HOST=http://embedding:8080
IS_EMBEDDING_HOST_SECURE=false

# Which embedding config stored in DB to use
EMBEDD_CONFIG_TO_USE=b1b6e50f-5919-4ca0-9973-7a6c03dde716
```

### RAG Configuration Name

```
# Determines which rag_config.json is loaded
RAG_CONFIG_NAME=hippo-rag-undirected-R5-1024
```

### LLM Backend

```
OPENAI_HOST=http://llm:8000
LLM_REQUEST_TIMEOUT=120
```

### Parallel Requests (Prefect Concurrency)

```
PARALLEL_REQUESTS=4
```

### OpenTelemetry (optional)

```
OTEL_ENABLED=true
OTEL_HOST=127.0.0.1:4317
OTEL_INSECURE=true
```

### Prefect API

```
PREFECT_API_URL=http://0.0.0.0:4200/api
```

---

### Using the `.env` File

Start a RAG-Prefect deployment with:

```bash
source .env
docker compose up -d
```

Each RAG mode (Hippo-RAG undirected, Hippo-RAG directed, Sub-Question, Hybrid/Simple) uses the same image;  
**the environment variables and mounted config files determine the active retrieval pipeline.**
