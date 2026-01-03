
# HippoRAG – Retrieval‑Augmented Generation Framework  

## Overview  

**HippoRAG** is a modular, async‑first framework that combines large‑language‑model (LLM) reasoning with a knowledge graph, vector store, and a state‑store to provide end‑to‑end retrieval‑augmented generation (RAG).  
It orchestrates four main subsystems:

| Subsystem | Role |
|-----------|------|
| **Graph DB** (Neo4j) | Stores entities, chunks, and weighted edges; supports personalized PageRank and graph‑based retrieval. |
| **Vector Store** (Qdrant) | Holds dense embeddings for entities, chunks, and facts; enables fast similarity search. |
| **State Store** (PostgreSQL via Tortoise‑ORM) | Persists the mapping *chunk ↔ entities/facts* and arbitrary metadata. |
| **LLM Reranker / OpenIE** | Extracts named entities and triples from passages, filters them, and re‑ranks retrieved results. |

All components implement the interfaces defined in `domain.hippo_rag.interfaces`, allowing you to swap out implementations (e.g., replace Neo4j with another graph DB) without changing the core logic.

## Key Features  

- **Async architecture** – all I/O (DB, LLM calls, embedding service) is asynchronous for high throughput.  
- **Configurable retrieval pipelines** – top‑k settings for vector, graph, and QA stages are defined in a single `HippoRAGConfig`.  
- **Personalized PageRank** – graph‑based relevance scoring using Neo4j GDS with seed‑based weighting.  
- **OpenIE integration** – automatic extraction of entities and RDF‑style triples from raw text.  
- **Metadata‑aware filtering** – store and query arbitrary document metadata (e.g., source, timestamps).  
- **Extensible interfaces** – `EmbeddingStoreInterface`, `GraphDBInterface`, `StateStore`, `LLMReranker`, etc., are defined in the `domain` package.  

## Package Structure  

### Core Classes  

| Class | Description |
|-------|-------------|
| `HippoRAG` | Implements `HippoRAGInterface` and coordinates vector, graph, and state stores, plus the LLM reranker. Handles the public `request` method. |
| `HippoRAGConfig` | Holds all tunable hyper‑parameters (top‑k values, damping factor, etc.) [10]. |
| `HippoRAGIndexer` | Asynchronous document indexer that runs OpenIE, creates embeddings, and populates the graph & state stores. |

## Installation  

```bash
uv sync
```

The `pyproject.toml` declares the required runtime libraries:

- `core`, `domain` (shared interfaces)  
- `numpy`, `regex`, `tqdm` for utility work [1]  
- Optional extras install the graph, vector, and database back‑ends (`hippo-rag-graph`, `hippo-rag-vectore-store`, `hippo-rag-database`) for integrations tests


## Development & Testing  

- **Unit / integration tests** are located in `tests/`. Run them with the helper scripts:  

```bash
./integrationstest.sh          # vector‑store tests
./integrationstest_local.sh    # runs tests with a local embedding service
```

- **Adding a new backend** – implement the appropriate interface from `domain.hippo_rag.interfaces` and register the class in the main `HippoRAG` constructor.  
