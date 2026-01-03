# Simple RAG Service  

## Overview  

The **Simple RAG Service** is a lightweight Python package that provides a ready‑to‑use Retrieval‑Augmented Generation (RAG) use‑case.
It wraps a RAG interface (`RAGLLM`) and exposes a single asynchronous `request` method that sends a conversation to the model, optionally filters by metadata, and returns a structured `RAGResponse`. OpenTelemetry tracing is built‑in, allowing you to monitor each request as a span named `simple-rag-request`.  

## What the Package Can Do  

| Capability | Description |
|------------|-------------|
| **Send RAG Requests** | Accepts a `Conversation` object (user messages, role information) and forwards it to the configured `RAGLLM` implementation. |
| **Metadata Filtering** | Allows optional metadata filters to limit the retrieval scope. |
| **Collection Scoping** | Supports specifying a collection name (e.g., a project‑specific vector store) for the request. |
| **OpenTelemetry Tracing** | Automatically creates a trace span for each request, making performance and error monitoring straightforward. |
| **Result Handling** | Returns a `Result[RAGResponse]` that clearly distinguishes successful responses from errors. |
| **Dependency‑Free Core** | Relies only on the `core` and `domain` packages (both provided as workspace sources), keeping the footprint small. |
| **Optional Test Extras** | Provides a `test` optional dependency that pulls in `domain-test==0.2.0` for unit‑ and integration‑testing. |

## Key Components  

- **`SimpleRAGUsecase`** – The main class that holds a reference to a `RAGLLM` implementation and an OpenTelemetry tracer. Its `request` method forwards the conversation to the model and returns the result wrapped in a `Result` object. The class is instantiated with a concrete `RAGLLM` implementation, making it easy to swap out the underlying model.  
- **`Conversation` & `Message` Models** – Defined in the `domain.rag.model` module, they represent the dialogue context sent to the LLM.  
- **`Result` Wrapper** – From `core.result`, it provides a functional‑style error handling pattern (e.g., `Result.Ok()`, `Result.Err()`).  

Implementation details, including the tracer initialization and the async request forwarding, are defined in `rag.py`【3】.  


## Development & Testing  

- **Workspace Development** – UV workspaces keep the `core`, `domain`, and `domain-test` packages in sync while you develop locally.  
- **Tracing** – The service uses OpenTelemetry; configure a compatible exporter (e.g., Jaeger, Zipkin) to view the `simple-rag-request` spans.  
- **Testing** – After installing the `test` extra, run the test suite with `pytest`

