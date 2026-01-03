# trigger‑evaluation‑prefect

## Overview

**trigger‑evaluation‑prefect** is a Python 3.12+ service that orchestrates the ingestion of datasets and the triggering of evaluation jobs for Retrieval‑Augmented Generation (RAG) systems.  
It is built on **Prefect** for workflow orchestration, uses **PostgreSQL** for persistence, and emits Prefect events to signal downstream consumers. 

## Purpose

The service serves as a bridge between a dataset source and an evaluation service.  
It:

1. **Loads a slice of a dataset** and stores the questions in the validation database.  
2. **Triggers an evaluation** for those questions via the evaluation service.  
3. **Emits Prefect events** (`ASK_RAG_SYSTEM` and `EVALUATE_RAG_SYSTEM`) to notify other components of the system when new data is ready or a job has been queued.

This enables an event‑driven pipeline where data ingestion and evaluation are decoupled, improving scalability and observability.

## Key Features

| Feature | Description |
|---------|-------------|
| **Prefect Flow Integration** | Two primary flows – `upload_dataset` and `trigger_eval` – are defined in `prefrect_tasks.py` [4] and exposed as deployments in `main.py` [3]. |
| **Event Emission** | Uses `prefect.events.emit_event` to send structured events that carry resource identifiers, facilitating downstream processing. |
| **Startup Sequences** | The `TriggerApplication` class configures logging and PostgreSQL startup sequences via `LoggerStartupSequence` and `PostgresStartupSequence` [2]. |
| **Configuration Driven** | Application settings (API name, version) reside in `settings.py` [5] and are loaded by `ConfigLoaderImplementation`. |
| **Modular Design** | Dependencies are declared in `pyproject.toml` [1], allowing each component to be developed or tested in isolation. |

## Use Cases

1. **Automated RAG Evaluation** – Periodically upload new datasets and trigger evaluation jobs without manual intervention.  
2. **Event‑Driven Orchestration** – Downstream services can subscribe to the Prefect events to start downstream workflows (e.g., model training, metric collection).  
3. **Continuous Integration** – Integrate with CI pipelines to validate new data and models automatically before deployment.

## Architectural Highlights

- **Prefect Deployment** – The `serve` function in `main.py` publishes both `upload_dataset` and `trigger_eval` as deployments, making them available to a Prefect server or Cloud instance.  
- **Event‑Driven Flow** – Each flow emits events upon key milestones, enabling a decoupled, observable architecture.  
- **PostgreSQL Integration** – `PostgresStartupSequence` guarantees that database migrations and connections are ready before the application begins processing.  
- **Configuration Layer** – The `ConfigLoaderImplementation` allows for environment‑specific configuration without code changes.

## Environment File (`.env`)

The trigger-evaluation-prefect service reads all configuration from environment variables.  
The following `.env` template includes the required logging, database, observability, and Prefect settings.

### Logging

```
LOG_LEVEL=info
LOG_SECRETS=true
```

### PostgreSQL (validation / evaluation databases)

```
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
POSTGRES_DATABASE=production-db
POSTGRES_USER=root
POSTGRES_PASSWORD=password-v2
```

### OpenTelemetry (optional)

```
OTEL_HOST=127.0.0.1:4317
OTEL_ENABLED=true
OTEL_INSECURE=true
```

### Prefect API

```
PREFECT_API_URL=http://0.0.0.0:4200/api
```

This loads the configuration and exposes the `upload_dataset` and `trigger_eval` Prefect deployments.

---

### docker-compose Reference

```yaml
trigger-evaluation-prefrect-v02:
  image: trigger-evaluation-prefect:v02
  container_name: trigger-evaluation-prefrect-masterarbeit-v02
  restart: unless-stopped
  networks:
    - dev_env
  environment:
    LOG_LEVEL: ${LOG_LEVEL}
    LOG_SECRETS: ${LOG_SECRETS}
    POSTGRES_HOST: ${POSTGRES_HOST}
    POSTGRES_PORT: ${POSTGRES_PORT}
    POSTGRES_DATABASE: ${POSTGRES_DATABASE}
    POSTGRES_USER: ${POSTGRES_USER}
    POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    OTEL_HOST: ${OTEL_HOST}
    OTEL_ENABLED: ${OTEL_ENABLED}
    OTEL_INSECURE: ${OTEL_INSECURE}
    PREFECT_API_URL: ${PREFECT_API_URL}
```
