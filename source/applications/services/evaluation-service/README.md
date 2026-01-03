
# Evaluation Service – Use‑Case Package  

## Overview  

The **evaluation-service** package provides the business‑logic layer for managing evaluation data in a Retrieval‑Augmented Generation (RAG) system. It acts as the bridge between the domain models (questions, answers, and ratings) and the underlying persistence layer, exposing a clear, token‑protected API for adding questions and recording both user‑generated and LLM‑generated evaluations.  

## Key Capabilities  

| Capability | Description |
|------------|-------------|
| **Administration‑protected operations** | Critical actions such as adding new test questions or LLM‑generated ratings require a valid admin token, ensuring that only authorized personnel can modify the evaluation data. |
| **Question handling** | When a new test question is submitted, the service computes a deterministic hash for the question text, checks whether the question already exists in the database, and stores it if it is new. |
| **User evaluation recording** | Users can submit their own ratings for a given answer. The service first verifies that the rating’s creator exists in the evaluator database before persisting the rating. |
| **LLM evaluation recording** | LLM‑generated ratings are accepted after admin‑token verification, allowing automated quality assessment of system answers. |
| **Tracing and observability** | All public methods are wrapped in OpenTelemetry spans, providing end‑to‑end visibility into request flow and performance characteristics. |
| **Singleton pattern** | The use‑case class is implemented as a singleton, guaranteeing a single, shared instance throughout the application lifecycle. |
| **Typed configuration** | The service is configured via a Pydantic model that currently holds the admin token, making configuration validation straightforward. |
| **Loose coupling via interfaces** | Interaction with the persistence layer is abstracted through `EvaluatorDatabase` and `EvaluationDatabase` interfaces, allowing flexible swapping of concrete implementations (e.g., in‑memory, SQL, NoSQL). |

## Architecture Highlights  

- **Project metadata** – Defined in `pyproject.toml` with a strict Python version requirement (`>=3.12,<3.13`) and workspace‑linked dependencies on the `core` and `domain` packages, ensuring consistent versioning across the monorepo [1].  
- **Core components** – The `EvaluationServiceUsecases` class encapsulates all business logic, receiving its dependencies (databases and configuration) through an initialization method and exposing async methods for each operation [2].  
- **Error handling** – Operations return a `Result` type, allowing callers to distinguish between successful outcomes and specific errors such as permission failures or missing evaluators.  

## Typical Use‑Case Flow  

1. **Add a new test question** – An admin provides a `TestSample`; the service hashes the question, checks for duplicates, and stores it.  
2. **Record a user rating** – A user submits a `RatingUser`; the service verifies the user’s existence and then stores the rating linked to the relevant answer.  
3. **Record an LLM rating** – An admin submits a `RatingLLM`; after token validation, the rating is stored for later analysis.  

## Extensibility  

- **Additional rating types** – New rating models can be added to the domain layer and handled by extending the service methods.  
- **Alternative storage back‑ends** – By implementing the `EvaluatorDatabase` and `EvaluationDatabase` interfaces, the service can work with any persistence technology without changing its core logic.  
- **Enhanced observability** – The existing OpenTelemetry integration can be enriched with custom attributes or exported to various tracing back‑ends.  

## Getting Started  

1. **Install dependencies** – The package relies on the `core` and `domain` workspace packages; ensure they are available in the same workspace.  
2. **Configure** – Provide an admin token via the `EvaluationServiceConfig` model.  
3. **Initialize** – Create a singleton instance of `EvaluationServiceUsecases` with the required database implementations and configuration.  

---

*This README summarizes the functionality and design of the evaluation-service use‑case package based on its source code and project configuration.*
