# validation‑database  

## Overview  
`validation-database` is a Python package that provides a thin persistence layer for the validation domain of a Retrieval‑Augmented Generation (RAG) system.
It defines the data‑model mappings between domain objects (DTOs) and the underlying database entities, and offers a simple asynchronous API for creating and updating test samples and ratings.


## Core Concepts  

### Database Interface  
The package implements the `EvaluationDatabase` and `EvaluatorDatabase` interfaces defined in the domain layer.
The concrete implementation (`PostgresEvaluationDatabase` in `validation_db_implementation.py`) provides asynchronous CRUD operations:

### Error Handling  
* **`DublicateException`** – Raised when attempting to store a test sample whose `question_hash` already exists in the database.  
* **`NotFoundException`** – Propagated by lower‑level ORM calls when a requested record cannot be located.  

All exceptions are wrapped in the `Result` type so that the API surface remains consistent.

### Observability  
The package integrates with **OpenTelemetry**. Each database operation runs within a tracing span obtained from the tracer, allowing performance metrics (e.g., query latency) to be exported to any compatible tracing backend.
