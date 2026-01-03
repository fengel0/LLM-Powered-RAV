# Fact‑Store‑Database

## Overview

`fact-store-database` is a concrete implementation of the **`FactStore`** interface defined in the `domain` package.  
It provides a persistent store for factual data (key‑value pairs, JSON blobs, etc.) that can be queried and updated by the rest of the system.

The implementation uses a lightweight SQLite database via **SQLAlchemy**, includes Alembic migration scripts, a small state‑holder helper, and a public API that mirrors the abstract `FactStore` contract.

## Features

- **Full `FactStore` contract compliance** – all required methods (`get_fact`, `set_fact`, `delete_fact`, `list_facts`, …) are implemented.
- **Typed models** – `model.py` defines the SQLAlchemy/Pydantic schema.
- **State holder** – `state_holder.py` provides a singleton‑style wrapper for the DB engine/session.
- **Test suite** – integration tests under `tests/` validate behaviour against the `FactStore` contract.

## Quick start

### Installation

```bash
# From the repository root
cd applications/lib/fact-store-database
uv sync
```

### Running the test suite

```bash
pytest -s test_fact_store.py
```

*Happy coding!*