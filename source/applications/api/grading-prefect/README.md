**README – grading‑prefect**  

---

## Overview  

**grading‑prefect** is a Prefect‑based orchestration service that evaluates candidate answers using configurable Large Language Model (LLM) back‑ends and a dedicated grading service.
It integrates with a PostgreSQL store, loads runtime configuration from environment variables and files, and exposes a reusable workflow that can be triggered by Prefect events.
The project is designed to be modular, allowing easy substitution of components such as the LLM provider, evaluation strategy, and data sources.  

---

## Purpose  

The primary goal of this repository is to provide an automated, scalable pipeline for **answer grading** in Retrieval‑Augmented Generation (RAG) or similar AI‑driven systems.
By leveraging Prefect automations, the service can react to evaluation events, invoke the grading logic, and store results without manual intervention.  

---

## Key Features  

| Feature | Description |
|---------|-------------|
| **Prefect automation** | Event‑driven workflow that reacts to `EVALUATE_RAG_SYSTEM` events and runs a deployment to grade answers. |
| **Configurable LLM integration** | Supports OpenAI or local models via `OpenAIAsyncLLM` and `ConfigOpenAI` settings (model, tokens, temperature, timeout, base URL). |
| **Parallel request handling** | Controls concurrency through `PARALLEL_REQUESTS` and `PARALLEL_LLM_CALLS` environment settings. |
| **Database‑backed state** | Uses PostgreSQL for fact storage and evaluation persistence (`PostgresDBFactStore`, `PostgresDBEvaluation`). |
| **Modular configuration** | Loads system prompts, grading configuration, and other parameters from files and environment variables (e.g., `SYSTEM_PROMPT_*`, `GRADING_CONFIG`). |
| **Extensible use‑case layer** | Central `GradingServiceUsecases` encapsulates the evaluation logic, making it easy to replace or extend the grading algorithm. |
| **Testing support** | Includes a test suite that can be executed via `pytest`. |

---

## Use Cases  

- **RAG system evaluation** – Automatically assess the correctness, completeness, and factuality of generated answers after each retrieval‑augmented generation request.  
- **Continuous grading pipeline** – Integrate into CI/CD pipelines to continuously validate AI model outputs against a test set.  
- **Local/OpenAI** – Swap between local LLMs and OpenAI models to compare grading performance under different settings.  
- **Enterprise QA monitoring** – Deploy as a background service that grades customer‑facing responses and logs metrics for compliance and quality assurance.  

---

## Configuration  

Runtime behavior is driven by a combination of environment variables and JSON/TXT files:

- **Evaluation type** (`EVAL_TYPE`): `"local"` or `"openai"` determines which LLM backend is used.  
- **Model and token settings** (`FACT_MODEL`, `MAX_TOKENS`, `OPENAI_KEY`, `OPENAI_HOST`).  
- **System prompts** (`SYSTEM_PROMPT_COMPLETENESS`, `SYSTEM_PROMPT_CORRECTNESS`, etc.) are loaded from files under `./prompts/`.  
- **Grading configuration** (`GRADING_CONFIG`) points to a JSON file defining grading criteria.  

All these settings are loaded via the `ConfigLoaderImplementation` and made available to the Prefect tasks and the grading service.  

---
## Environment File (`.env`)

The grading-prefect service is configured entirely through environment variables.  
Below is a complete `.env` template that reflects the expected deployment settings for grading workflows, LLM backends, PostgreSQL, and observability.

### Logging

```
LOG_LEVEL=info
LOG_SECRETS=true
```

### Prefect

```
PREFECT_API_URL=http://0.0.0.0:4200/api
```

### Grading Configuration

```
# Determines which LLM backend to use: "openai" or "local"
EVAL_TYPE=openai

# Number of parallel grading jobs Prefect may run
PARALLEL_REQUESTS=1

# Maximum number of parallel LLM calls inside a single grading task
PARALLEL_LLM_CALLS=1
```

### Model & LLM Settings

```
FACT_MODEL=gpt-4o-mini
MAX_TOKENS=16384
TEMPERATUR=0.2
LLM_REQUEST_TIMEOUT=60
```

### OpenAI / Local LLM

```
OPENAI_KEY=your-openai-key-here
# Optional override for local/OpenAI-compatible endpoints
# OPENAI_HOST=http://openai-service:8080
```

### Prompt Files

```
SYSTEM_PROMPT_COMPLETENESS=./prompts/completeness.txt
SYSTEM_PROMPT_CORRECTNESS=./prompts/correctness.txt
SYSTEM_PROMPT_FACTUALITY=./prompts/factuality.txt

# Optional:
# GRADING_CONFIG=./config/grading_config.json
```

### PostgreSQL

```
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
POSTGRES_DATABASE=grading-db
POSTGRES_USER=root
POSTGRES_PASSWORD=password-v2
```

### OpenTelemetry (optional)

```
OTEL_HOST=127.0.0.1:4317
OTEL_ENABLED=true
OTEL_INSECURE=true
```

### Running with the `.env`

```bash
source .env
python src/grading_prefect/main.py
```
---

## Extending the Project  

- **Add new LLM providers** by implementing a class that conforms to the `AsyncLLM` interface and updating the configuration loader.  
- **Customize grading logic** by extending `GradingServiceUsecases` or replacing it with a bespoke implementation.  
- **Introduce additional automations** in Prefect by defining new `Automation` objects and linking them to relevant events.  

