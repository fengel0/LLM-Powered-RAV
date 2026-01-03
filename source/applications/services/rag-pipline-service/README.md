# RAG‑Pipeline Service  

## Overview  

The **RAG‑Pipeline Service** is a Python package that implements a simple Retrieval‑Augmented Generation (RAG) workflow.
It coordinates a language model, a validation database, and a project database to retrieve relevant information, generate answers, and store evaluation results.
The use‑case is built as a singleton, includes OpenTelemetry tracing, and provides configurable retry behaviour.

## What the Package Can Do  

| Capability | Description |
|------------|-------------|
| **Orchestrate RAG Calls** | Calls a `RAGLLM` implementation to retrieve context, generate a response, and return the answer together with any retrieved context. |
| **Configurable Retries** | Automatically retries failed LLM calls up to a configurable number of attempts, with a configurable wait time between attempts. |
| **Evaluation Persistence** | Stores generated answers and related metadata in an `EvaluationDatabase` for later analysis. |
| **Project‑Aware Operations** | Interacts with a `ProjectDatabase` to associate evaluations with specific projects. |
| **OpenTelemetry Tracing** | Emits spans named `"SimpleRAGUsecase"` to allow observability of the whole pipeline. |
| **Typed Configuration** | Uses Pydantic models (`RAGUsecaseConfig`, `RagUsecaseConfig`) to hold both system‑wide and use‑case‑specific settings. |
| **Optional Test Extras** | Provides a `test` optional dependency that pulls in `domain-test==0.2.0` for unit‑ and integration‑testing. |

## Key Components  

- **`RAGUsecase` (singleton)** – Central class that holds references to the LLM, databases, and configuration, and exposes the RAG workflow. Initialized via `_init_once` which sets up tracing and stores injected dependencies.  
- **`RagUsecaseConfig`** – Pydantic model defining the number of retries (`retries`) and the wait time between retries (`time_to_wait_in_secondes`).  
- **`RAGConfig`** – Imported from the domain database module; contains system‑wide RAG settings (not detailed in the source).  
- **`AsyncLLM` / `RAGLLM` Interfaces** – Abstract the language‑model calls; the use‑case invokes them asynchronously and handles result propagation.  

*Implementation details such as the retry loop, tracing, and dependency injection are defined in `rag.py`*.

