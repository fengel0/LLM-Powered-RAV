# simple‑rag

**simple‑rag** is a lightweight Python package that provides a Retrieval‑Augmented Generation (RAG) interface built on top of LlamaIndex. It offers two concrete implementations:

* `LlamaIndexRAG` – a basic RAG engine.  
* `LlamaIndexSubRAG` – a sub‑question RAG engine that can handle multi‑step queries.

The library is designed to be easy to integrate into any Python project that needs semantic search or chat‑style RAG capabilities.

---


## Overview

`simple‑rag` bundles the core RAG logic with a thin wrapper around LlamaIndex’s chat engines. It works with any LLM model supported by LlamaIndex and can be configured with metadata filters and collection names.

Key features:

- Simple, typed `Conversation` and `Message` models.
- Automatic conversion of conversation history to LlamaIndex `ChatMessage`s.
- Optional sub‑question handling via `LlamaIndexSubRAG`.
- OpenTelemetry tracing for observability.

The package relies on the following core dependencies:

```
llama-index-extension==0.2.0
``` 

(see `pyproject.toml` for the full list).

---

## Optional test dependencies

For running the test suite you’ll also need the optional dependencies:

```bash
pip install "simple-rag[test]"
```

These install `testcontainers`, `rest-client`, and `domain-test` as defined in the optional‑dependency group.

---



## Development

The repository includes helper scripts for local integration testing:

```bash
# Set up environment variables (example values)
export OPENAI_HOST=https://ollama.home-vtr4v3n.de/v1
export OPENAI_MODEL=gemma3:4b
export OPENAI_HOST_KEY=dummy
export EMBEDDING_HOST=10.0.0.12:8085
export RERANKER_HOST="https://vllm.home-vtr4v3n.de"
export MODEL_RERANKER=BAAI/bge-reranker-base
export RERANKER_API_KEY="my-dummy-key"

# Run the integration test suite
./integrationstest_local.sh   # loads env vars then calls integrationstest.sh
```

`integrationstest.sh` simply executes the unit‑test files with `pytest`【1】【2】.

## Testing

Run the test suite with:

```bash
pytest tests/simple_request_test.py
pytest tests/sub_request_test.py
```

Or simply execute the provided script:

```bash
./integrationstest.sh
```

The tests cover both the simple and sub‑question RAG flows.


