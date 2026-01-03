# vector‑db  

## Overview  

`vector-db` is a Python package that provides an asynchronous vector‑store implementation built on top of **LlamaIndex** and **Qdrant**.
It integrates custom embedding and reranking services, allowing you to store, split, and query documents efficiently with both dense and sparse vector representations.  

Key capabilities include:  

- Automatic document splitting using a configurable `DocumentSplitter`.  
- Support for custom embedding clients and asynchronous rerankers.  
- Configuration of top‑N results for dense, sparse, and reranker‑based retrieval.  
- Integration with OpenTelemetry for tracing database operations.  

The package follows the `AsyncDocumentIndexer` interface, making it suitable for scalable Retrieval‑Augmented Generation (RAG) pipelines.  

---

## Features  

| Feature | Description |
|---------|-------------|
| **Asynchronous indexing** | Non‑blocking document insertion and retrieval. |
| **Hybrid search** | Combines dense vectors, BM25‑style sparse vectors, and reranker‑based re‑ranking. |
| **Customizable components** | Plug‑in your own embedding service (`EmbeddClient`) and reranker (`AsyncRerankerClient`). |
| **Tracing** | Built‑in OpenTelemetry tracing for observability. |
| **Configurable top‑N** | Separate control over the number of results returned from dense, sparse, and reranker stages. |

The implementation relies on the `LlamaIndexVectorStoreConfig` dataclass to hold these settings, and the `LlamaIndexVectorStore` class orchestrates the indexing workflow [1].  

---

## Installation  

```bash
uv sync
```

- `llama-index-extension==0.2.0`  

These are declared in the project's `pyproject.toml` file.  

### Optional dependencies  

For testing, you can install the extra `test` group:  

- `testcontainers==4.13.2`  
- `rest-client==0.2.0`  
- `domain-test==0.2.0`  

Install them with:  

```bash
uv sync --all-extras
```  

---

## Configuration  

Create a `LlamaIndexVectorStoreConfig` instance with the following fields:  

- **embedding** – an `EmbeddClient` implementation that provides text embeddings.  
- **reranker** – an `AsyncRerankerClient` for re‑ranking results.  
- **top_n_count_dens** – number of dense results to return.  
- **top_n_count_sparse** – number of sparse (BM25) results to return.  
- **top_n_count_reranker** – number of results to feed into the reranker.  
- **sparse_model** (optional) – name of the sparse model to use, defaulting to `"Qdrant/bm25"`.

The configuration is passed to the `LlamaIndexVectorStore` constructor together with a `DocumentSplitter` implementation.  

---

## Environment Variables (for integration tests)  

When running the integration test script, the following environment variables are expected:  

- `EMBEDDING_HOST` – address of the embedding service.  
- `RERANKER_HOST` – URL of the reranker service.  
- `MODEL_RERANKER` – identifier of the reranker model (e.g., `BAAI/bge-reranker-base`).  
- `RERANKER_API_KEY` – API key for the reranker service.  

These are demonstrated in the test helper script `integrationstest_local.sh` [4].  

---

## Testing  

The test suite can be executed with `pytest` by running the provided script:  

```bash
pytest tests/qdrant_tests.py
```  

(see `integrationstest.sh` for the command).
