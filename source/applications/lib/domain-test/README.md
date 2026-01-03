# Domain-Test Package

## Overview

`domain-test` is a test suite that provides reusable integration tests for the
different interfaces provided in the `domain` package.  
The goal is to ensure that any concrete implementation of a given interface
behaves consistently across the code base.

The package contains:

* **Base test classes** – abstract test classes that define a common test
  contract.
* **Concrete test modules** – ready‑to‑run test files for each domain component
  (e.g., database, environment, file‑converter, LLM, etc.).

All tests are written with **pytest** and can be executed with:

```bash
cd applications/lib/domain-test
pytest
```

## Getting Started

### Prerequisites

## How to Use

### 1. Subclass a Base Test

Each interface in the `domain` package has a corresponding abstract test class
in `src/domain_test/<component>/`.  
To create a concrete implementation test you subclass the base class and
implement the required setup/teardown hooks.

```python
# src/domain_test/database/config/config_db_test.py
from domain_test.database.config import TestRAGConfigDatabase

class TestPostgresRAGConfigDatabase(TestRAGConfigDatabase):
    __test__ = True

    # Implement the required hooks (see below) to spin up a concrete
    # implementation (e.g., a Postgres container) and run the generic tests.
```

### 2. Implement Required Hooks

All base classes provide synchronous and asynchronous hook methods that you
should override as needed:

| Hook type                     | Method signature                                 | Purpose |
|-------------------------------|--------------------------------------------------|---------|
| Class‑level (once per class) | `setup_class_sync(cls)`                         | Synchronous class setup |
|                               | `async setup_class_async(cls)`                  | Asynchronous class setup |
|                               | `teardown_class_sync(cls)`                      | Synchronous class teardown |
|                               | `async teardown_class_async(cls)`               | Asynchronous class teardown |
| Method‑level (per test)      | `setup_method_sync(self, test_name: str)`       | Synchronous per‑test setup |
|                               | `async setup_method_async(self, test_name: str)`| Asynchronous per‑test setup |
|                               | `teardown_method_sync(self, test_name: str)`    | Synchronous per‑test teardown |
|                               | `async teardown_method_async(self, test_name: str)`| Asynchronous per‑test teardown |

Only the hooks you need for your implementation have to be overridden; the
defaults are no‑ops.

### 3. Base Async Test Class

For code that requires async setup/teardown, the package provides an
asynchronous base class.  It is **not** collected as a test case itself
(`__test__ = False`).  Concrete test classes should inherit from it and
implement the hooks described above.

### 4. Where to Place Concrete Unit Tests

The abstract base classes in **`domain-test`** only verify that an *interface*
behaves consistently across multiple implementations. They are **not** meant
to contain the full suite of unit tests for a concrete implementation.

Developers should write those implementation‑specific tests **inside the
package that provides the implementation**.  This keeps the shared test suite
lightweight and ensures that edge‑case behaviour unique to an implementation
is exercised where the code lives.

**Example:** A `SentenceChunker` implementation of a generic `TextChunker`
interface will have its own behaviour (different chunking granularity,
punctuation handling, etc.). Those details belong in the
`sentence_chunker` package’s own test directory, not in the shared
`domain-test` suite.

In short:

* **`domain-test`** – defines reusable *integration* style tests for shared
  contracts.
* **Implementation packages** – contain their own *unit* tests that validate
  behaviour unique to that implementation.

## Directory Layout

```
applications/lib/domain-test/
├─ README.md                # ↹ This file
├─ pyproject.toml           # Build metadata
├─ requirements.txt         # Test dependencies
├─ pytest.ini               # Pytest configuration
├─ src/
│   └─ domain_test/
│       ├─ __init__.py
│       ├─ database/
│       │   ├─ __init__.py
│       │   ├─ config/
│       │   │   ├─ __init__.py
│       │   │   └─ config_db_test.py
│       │   ├─ facts/
│       │   │   └─ facts_store.py
│       │   ├─ file/
│       │   │   └─ file_database.py
│       │   ├─ project/
│       │   │   └─ project_database.py
│       │   └─ validation/
│       │       └─ validation_database.py
│       ├─ enviroment/
│       │   ├─ __init__.py
│       │   ├─ embedding.py
│       │   ├─ llm.py
│       │   └─ rerank.py
│       ├─ file_converter/
│       │   └─ client_test.py
│       ├─ hippo_rag/
│       │   ├─ __init__.py
│       │   ├─ hippo_rag_database_test.py
│       │   └─ hippo_rag_vector_store.py
│       ├─ http_client/
│       │   └─ __init__.py
│       ├─ llm/
│       │   └─ llm_test.py
│       └─ pipeline/
│           └─ __init__.py
└─ tests/                     # Optional additional test utilities
```

## Extending the Test Suite

1. **Add a new interface** in the `domain` package.
2. **Create a base test** in `src/domain_test/<new_component>/` mirroring the
   pattern of existing bases (inherit from `unittest.TestCase` or use `pytest`
   fixtures).
3. **Document the new test** in this README under “How to Use”.

--- 

*Happy testing!*