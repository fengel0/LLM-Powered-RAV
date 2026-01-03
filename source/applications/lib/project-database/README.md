
# validation‑database  

**Version:** 0.2.0  

## Overview  
`validation-database` is a Python package that provides a thin persistence layer for the validation domain of a Retrieval‑Augmented Generation (RAG) system. It defines the data‑model mappings between domain objects (DTOs) and the underlying database entities, and offers a simple asynchronous API for creating and updating test samples and ratings. The package is built for Python 3.12 and uses **pydantic**, **tortoise‑orm**, and **uv** workspace sources to keep the core, domain, and database components in sync.

## Installation  
The package can be installed from a local source tree or via a package index that hosts the built wheel. It requires Python ≥ 3.12 ,< 3.13 and the dependencies listed in the project configuration (e.g., `pydantic==2.11.10`) [1].

## Core Concepts  

### Domain ↔ Database Mapping  
The module `validation_database.model` contains a set of conversion utilities that translate between domain objects (DTOs) and their corresponding ORM models:

| Function | Purpose |
|----------|---------|
| `dto_to_db` / `db_to_dto` (TestSample) | Convert a `TestSampleDomain` object to a `TestSample` ORM instance and back, handling fields such as dataset ID, question, expected answer, and metadata. |
| `dto_to_db_rating_user` / `db_to_dto_rating_user` | Map user‑generated rating data (rationale, creator, correctness, completeness) between the DTO and the `RatingUser` table. |
| `dto_to_db_rating_llm` / `db_to_dto_rating_llm` | Perform the same mapping for LLM‑generated ratings, including configuration ID and factual completeness. |
| `dto_to_db_rag_system_answer` / `db_to_dto_rag_system_answer` | Translate system answer records, preserving answer text, latency metrics, and fact counts. |
| `db_to_dto_rag_system_answer_with_rating` | Produce a rich DTO that includes the system answer together with placeholders for future LLM and human ratings. |

These helpers ensure that optional list fields default to empty lists and that missing metadata is represented by empty dictionaries, thereby keeping the database representation consistent [2].

### Database Interface  
The package implements the `EvaluationDatabase` and `EvaluatorDatabase` interfaces defined in the domain layer. The concrete implementation (`PostgresEvaluationDatabase` in `validation_db_implementation.py`) provides asynchronous CRUD operations:

* **`create(obj: TestSample) -> Result[str]`** – Inserts a new test sample after checking for duplicate question hashes. If a duplicate is found, a `DublicateException` is returned.  
* **`update(obj: TestSample) -> Result[None]`** – Updates an existing test sample identified by its primary key.  

Both methods return a `Result` object that encapsulates either a successful value or an error, enabling callers to handle failures in a functional style. The implementation also initializes a Postgres‑specific internal database layer for each entity type (samples, user ratings, LLM ratings, system answers, and evaluators) and sets up an OpenTelemetry tracer named `"PostgresEvaluation"` for observability [3].

### Error Handling  
* **`DublicateException`** – Raised when attempting to store a test sample whose `question_hash` already exists in the database.  
* **`NotFoundException`** – Propagated by lower‑level ORM calls when a requested record cannot be located.  

All exceptions are wrapped in the `Result` type so that the API surface remains consistent.

### Observability  
The package integrates with **OpenTelemetry**. Each database operation runs within a tracing span obtained from the tracer, allowing performance metrics (e.g., query latency) to be exported to any compatible tracing backend.

## Usage Summary (without code)  

1. **Prepare DTOs** – Construct domain objects (`TestSampleDomain`, `RatingUserDomain`, etc.) using your application logic.  
2. **Persist Data** – Call the `create` or `update` methods of the evaluation database implementation to store or modify records.  
3. **Retrieve & Convert** – Use the provided `db_to_dto_*` functions to read ORM objects from the database and convert them back into domain DTOs for further processing.  

All interactions are asynchronous and return `Result` containers, making it straightforward to compose pipelines that react to success or failure.

## License  
The package is released under the same license as the surrounding project (refer to the repository’s `LICENSE` file).

---  

*For detailed API documentation, refer to the module docstrings and the `validation_database` source code.*
