# text‑embedding

**text‑embedding** is a Python package that provides client‑side functionality for embedding documents and reranking text using a gRPC‑based service. It bundles:

* **Embedding client** – sends text to a remote embedding service and returns dense vector representations.  
* **Reranker client** – forwards a query and a list of candidate documents to a reranking model and receives ranked results.  
* **Pydantic models** for request/response payloads.  
* **OpenTelemetry tracing** for observability of embedding and reranking calls.  


---

## What the package contains

| Module / File | Purpose |
|---------------|---------|
| `text_embedding/__init__.py` | Core client classes (`EmbeddClient`, `RerankerClient`) and helper methods for embedding and reranking. |
| `text_embedding/proto/` | Generated protobuf definitions (`tei_pb2`, `tei_pb2_grpc`) used for gRPC communication. |
| `domain/text_embedding/interface.py` | Abstract interfaces that the concrete clients implement. |
| `domain/text_embedding/model.py` | Pydantic data models (`EmbeddingRequestDto`, `EmbeddingResponseDto`, `RerankRequestDto`, `RerankResponseDto`). |
| `tests/` | Unit‑ and integration‑tests for both embedding and reranking functionality. |
| `integrationstest_local.sh` | Bash script that sets the required environment variables before invoking the test runner. |
| `integrationstest.sh` | Executes the actual test suite with `pytest`. |

The package’s runtime dependencies are declared in its `pyproject.toml` file and include `pydantic`, `core`, `domain`, `protobuf`, `grpcio`, and `grpcio-tools`.

---

## Installation

```bash
# Install the package (requires Python 3.12)
pip sync
```
---

## Running the test suite

The tests rely on a set of environment variables that point to the embedding and reranking services. These variables are exported by the helper script **integrationstest_local.sh**:

```bash
export EMBEDDING_HOST=10.0.0.12:8085
export RERANKER_HOST="http://127.0.0.1:7998"
export MODEL_RERANKER=Qwen/Qwen3-Reranker-0.6B
export RERANKER_API_KEY="my-dummy-key"
```

These exports are **necessary for testing** because the integration tests contact the actual services running at the specified hosts【1】.

To run the tests:

1. Make sure the services referenced by the environment variables are reachable.
2. Execute the wrapper script:

```bash
./integrationstest_local.sh
```

The wrapper script subsequently calls **integrationstest.sh**, which runs the pytest commands for the relevant test modules【2】:

```bash
pytest ./tests/reranker_vllm.py
```

(Additional test modules can be added to the script as needed.)

