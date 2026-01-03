
# Dataset Loader – Prefect Deployment  

## Overview  
The **dataset‑loader‑prefect** project is a small service that ingests a wide variety of question‑answer (QA) datasets and registers each question in a central evaluation backend.  
It is built on **Prefect** (referred to as “prefrect” in the code) and runs as a single‑process application that starts the required components (logger, Postgres connections, evaluation‑service use‑cases) and then executes a series of Prefect tasks that read files, validate them with Pydantic models and call a helper (`upload_question`) to store the data in the evaluation service [6].  

## What the project does  
**Dataset‑specific upload tasks** – for each supported source (e.g., Dragonball, Fach‑Hochschule Erfurt, GraphRAG‑Bench, DocBench, DocDial, KG‑RAG, Multi‑Hop news, MultiSpanQA, WikiTable, Weimar, BioASQ) there is a Prefect task that:  
- reads the raw file (JSON, JSONL, CSV, or custom text format),  
- validates the content with a Pydantic schema,  
- builds the fields required by the evaluation backend (question, expected answer, context, facts, metadata), and  
- invokes `upload_question` which checks for duplicates (by MD5 hash) and either increments a counter or creates a new entry [6].  
3. **Orchestrated execution** – a top‑level `upload_dataset` task (defined in `prefrect_tasks.py`) runs all individual upload tasks sequentially, handling startup and graceful shutdown of the application [7].  

## Primary use‑case  
The service is intended for **pre‑processing and registration of benchmark datasets** that will later be used to evaluate large language models (LLMs). By centralising the ingestion step, downstream evaluation pipelines can query a single source of truth (the evaluation service) for all questions, expected answers, contexts and supporting facts. This makes it easy to:

* Populate a consistent evaluation database from heterogeneous public datasets.  
* Keep track of which questions have already been loaded (hash‑based deduplication).  
* Attach rich metadata (domain, source, query type, file name, etc.) that can be used for filtering or analysis.  

## Key components  

| Component | Role |
|-----------|------|
| **`pyproject.toml`** | Declares the package metadata (name `dataset-loader-prefect`, version `0.2.0`) and workspace‑based dependencies on internal packages such as `core`, `domain`, `rest-client`, `evaluation-service`, `prefect-core` and `deployment-base` [2]. |
| **`settings.py`** | Holds the API name and version that are used to build the application identifier [18]. |
| **`application_startup.py`** | Sets up logging, connects to the Postgres evaluation databases and creates the `EvaluationServiceUsecases` instance used by all upload tasks [3]. |
| **`prefrect_tasks.py`** | Defines the orchestration flow: `startup`, `upload_dataset`, and `shutdown`. The `upload_dataset` task sequentially calls each dataset‑specific uploader [7]. |
| **`prefrect/*.py`** (e.g., `upload_dragonball.py`, `upload_fh.py`, `upload_graphrag_bench.py`, …) | Implement the concrete logic for reading, validating and uploading each dataset. |
| **`prefrect/helper.py`** | Central helper that interacts with the evaluation service, performing duplicate detection and creation of `TestSample` records [6]. |

## How it works (high‑level flow)  

1. **Start the application** – `ApplicationDatasetloader.create(...)` reads configuration and initialises required services.  
2. **Run the Prefect flow** – the `CustomFlow` created in `main.py` serves the flow under the name derived from the API name and version.  
3. **Execute upload tasks** – each uploader parses its source files, creates Pydantic model instances, and calls `upload_question`.  
4. **Persist to evaluation backend** – `upload_question` either increments a counter for existing questions or inserts a new `TestSample` via `EvaluationServiceUsecases`.  

## Extending the project  

* **Add a new dataset** – create a Pydantic schema for the file format, a parsing helper, and a Prefect task that calls `upload_question`. Then import the task in `prefrect_tasks.py` and add it to the `upload_dataset` sequence.  
* **Customize metadata** – extend the `metadata` or `metatdata_filter` dictionaries passed to `upload_question` to capture additional provenance information.  

## Environment File (`.env`)

The dataset-loader-prefect service reads all configuration from environment variables.  
The following example shows a clean, structured `.env` file that matches the expected deployment settings.

### Logging
- **LOG_LEVEL**  
  Controls verbosity (`debug`, `info`, `warn`, `error`).  
  ```
  LOG_LEVEL=info
  ```

- **LOG_SECRETS**  
  Whether sensitive values may appear in logs.  
  ```
  LOG_SECRETS=True
  ```

---

### PostgreSQL (Evaluation Service Database)

```
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
POSTGRES_DATABASE=production-db
POSTGRES_USER=root
POSTGRES_PASSWORD=password-v2
```

---

### OpenTelemetry (optional)

```
OTEL_HOST=127.0.0.1:4317
OTEL_ENABLED=true
OTEL_INSECURE=true
```

---

### Prefect API

```
PREFECT_API_URL=http://0.0.0.0:4200/api
# Alternative:
# PREFECT_API_URL=https://prefrect.home-vtr4v3n.de/api
```

## Running the service  

1. Set the required environment variables (Postgres connection, OTEL tracing, Prefect API URL, etc.) as shown in `start_application.sh`.  
2. Execute the startup script (`start_application.sh`) which launches the main module.  
3. The service will start, run all upload tasks, and shut down gracefully, leaving the evaluation backend populated with the ingested questions.  

