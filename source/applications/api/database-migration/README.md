
# Database‑Migration


A small utility that boots a Tortoise‑ORM / Aerich environment, loads the models of the various sub‑databases and runs the configured migrations against a PostgreSQL instance.

---

## Table of Content

- [Database‑Migration](#databasemigration)
  - [Overview](#overview)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Configuration](#configuration)
  - [Running the Application](#running-the-application)
  - [Migration Workflow](#migration-workflow)
  - [Development Notes](#development-notes)

---

## Overview  

The project bundles the following pieces:

| Component | Description |
|-----------|-------------|
| **Aerich configuration** | `aerich_conf.py` defines the DB URL (built from environment variables) and registers all models that Aerich should manage. |
| **Tortoise‑ORM settings** | supplied to Aerich via `tool.aerich.tortoise_orm` in `pyproject.toml`. |
| **Application bootstrap** | `application_startup.py` and `main.py` create a `DatbaseMigrationApplication`, load settings, initialise a `PostgresSession` with all model modules, and trigger migrations. |
| **Settings loader** | `settings.py` declares a single configurable attribute `UPDATE_MESSAGE` used to pass a custom migration description. |
| **Shell script** | `start_application.sh` shows the required environment variables and starts the app. |

All of this is wired together through the **uv** workspace configuration in `pyproject.toml` (see the `[tool.uv.sources]` sections).  

---

## Prerequisites  

* **Python 3.12** (the project requires `>=3.12,<3.13`).  
* **PostgreSQL** instance reachable from the container/host.  
* **uv** (the modern Python package manager) – install via `curl -LsSf https://astral.sh/uv/install.sh | sh`.  

---

## Installation  

```bash
uv sync
```
---

## Configuration  

The application reads its configuration exclusively from environment variables. The most important ones are:

| Variable | Default (if not set) | Meaning |
|----------|----------------------|---------|
| `POSTGRES_HOST` | `127.0.0.1` | PostgreSQL host |
| `POSTGRES_PORT` | `5432` | PostgreSQL port |
| `POSTGRES_DATABASE` | `production-db` | Database name |
| `POSTGRES_USER` | `root` | DB user |
| `POSTGRES_PASSWORD` | `password` | DB password |
| `UPDATE_MESSAGE` | – | Optional description passed to the migration command (see `settings.py`). |

These variables are referenced when building the connection string in `aerich_conf.py`:

```python
DB_URL = (
    f"postgres://{os.getenv('POSTGRES_USER', 'root')}:"
    f"{os.getenv('POSTGRES_PASSWORD', 'password')}@"
    f"{os.getenv('POSTGRES_HOST', '127.0.0.1')}:"
    f"{os.getenv('POSTGRES_PORT', '5432')}/"
    f"{os.getenv('POSTGRES_DATABASE', 'production-db')}"
)
```  

A ready‑made example is provided in `start_application.sh`:

```bash
export LOG_LEVEL=info
export LOG_SECRETS=False

export POSTGRES_HOST="127.0.0.1"
export POSTGRES_PORT=5432
export POSTGRES_DATABASE="production-db"
export POSTGRES_USER="root"
export POSTGRES_PASSWORD="password-v2"

export UPDATE_MESSAGE="add config type"

python src/database_migration/main.py
```  

---

## Running the Application  

```bash
# Make sure the environment variables are set (source the script or export manually)
source start_application.sh   # or copy the exports into your shell

# Run the main entry point
uv run python src/database_migration/main.py
```

The script performs the following steps (see `main.py`):

1. Creates the `DatbaseMigrationApplication`.  
2. Loads the configuration (`ConfigLoaderImplementation`).  
3. Starts the application and the PostgreSQL session.  
4. Calls `PostgresSession.migrations()` with the value of `UPDATE_MESSAGE`.  
5. Gracefully shuts down.  

---

## Migration Workflow  

Aerich stores migration scripts under the `migrations/` folder (configured via `tool.aerich.location`). The list of models that Aerich will manage is defined in `aerich_conf.py`:

```python
MODELS = [
    "file_database.model",
    "project_database.model",
    "validation_database.model",
    "config_database.model",
    "hippo_rag_database.model",
    "fact_store_database.model",
    "aerich.models",
]
```  

Typical workflow:

- changes made to data models made
- add additional models if a new package has been added
- update Message in start_application.sh
- call ./start_application.sh
- will create migrations scripts in migrations folder and apply them


Alternative Workflows
```bash
# Initialise Aerich (run once)
uv run aerich init -t aerich_conf.TORTOISE_ORM

# Generate a new migration after changing models
uv run aerich migrate -m "add new table"

# Apply pending migrations to the database
uv run aerich upgrade
```

---

## Development Notes  

* **Adding a new sub‑package** – add it to the `[tool.uv.sources]` section of `pyproject.toml` and list its models in `MODELS` inside `aerich_conf.py`.  
* **Logging** – the application uses the `LoggerStartupSequence` component; adjust `LOG_LEVEL` and `LOG_SECRETS` as needed.  
* **Testing migrations** – you can run the app against a local Docker PostgreSQL container and verify the generated SQL in `migrations/`.  

