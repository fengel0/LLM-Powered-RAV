# Domain Package Overview

The **domain** package provides the core business contracts and data transfer objects (DTOs) used throughout the project.
Its purpose is to define **interfaces** (the “what”) and **models/DTOs** (the “data”) without containing any implementation logic.
All other packages (e.g., `infrastructure`, `application`, `ui`) depend on these definitions, ensuring a clean separation of concerns and making the system easily testable and extensible.

## What the Package Contains

- **Interfaces** – Abstract base classes or protocols that describe the required behavior for services such as:
  - Database configuration and access
  - File handling
  - HTTP client operations
  - LLM (large language model) interaction
  - Pipeline orchestration and event handling

- **DTOs / Models** – Pydantic (or similar) data classes that define the shape of data exchanged between layers. These include:
  - Configuration objects (e.g., database connection settings)
  - Request/response schemas for HTTP clients
  - File metadata structures
  - LLM request/response payloads
  - Pipeline event payloads

The package deliberately contains **no concrete implementations**—only contracts and data shapes.
Implementations live in other layers (e.g., `infrastructure` or `adapters`) and are injected wherever needed.

## General Project Structure

```
domain/
├── src/
│   └── domain/
│       ├── __init__.py                # Package export
│       ├── database/
│       │   ├── config/
│       │   │   ├── interface.py      # Abstract DB config interface
│       │   │   └── model.py          # Concrete config DTO
│       │   ├── file/
│       │   │   ├── interface.py      # File storage interface
│       │   │   └── model.py          # File metadata DTO
│       │   ├── project/
│       │   │   ├── interface.py      # Project persistence interface
│       │   │   └── model.py          # Project DTO
│       │   └── validation/
│       │       ├── interface.py      # Validation interface
│       │       └── model.py          # Validation result DTO
│       ├── file_converter/
│       │   ├── interface.py          # Converter contract
│       │   └── model.py              # Conversion request/response DTOs
│       ├── hippo_rag/
│       │   ├── interfaces.py         # Retrieval‑augmented generation interfaces
│       │   └── model.py              # RAG request/response DTOs
│       ├── http_client/
│       │   ├── async_client.py       # Async client abstract base
│       │   ├── sync_client.py        # Sync client abstract base
│       │   └── model.py              # HTTP request/response DTOs
│       ├── llm/
│       │   ├── interface.py          # LLM service contract
│       │   └── model.py              # LLM interaction DTOs
│       └── pipeline/
│           ├── __init__.py
│           └── events.py            # Event definitions and payload DTOs
└── pyproject.toml                     # Package metadata
```

## How to Use

Developers can import the interfaces and DTOs throughout the codebase, then provide concrete implementations in the appropriate layers. This approach promotes:
- **Loose coupling:** Modules only know the contract, not the concrete class.
- **Testability:** Mocks/stubs can replace implementations in unit tests.
- **Maintainability:** Changing an implementation does not affect dependent code.

---

**Remember:** The `domain` package is the *source of truth* for contracts and data shapes. Keep it focused on definitions; any business logic belongs in higher‑level layers.
