**README – Graph‑View Evaluation Platform**  

---

## Overview  
Graph‑View is a web‑based evaluation platform for Retrieval‑Augmented Generation (RAG) systems. It combines a FastAPI backend with a Gradio UI to load datasets, execute evaluation use‑cases, calculate a comprehensive set of metrics (recall, precision, F1, completeness, strict completeness, confidence intervals) and visualise the results through interactive charts. The application is orchestrated by a custom `GraphViewApplication` that initialises logging, PostgreSQL connections and the evaluation use‑cases at start‑up [1].

---

## Features  

| Category | Description |
|----------|-------------|
| **Backend orchestration** | A singleton `GraphViewApplication` sets up logger and PostgreSQL components, creates the evaluation and configuration use‑cases, and exposes the FastAPI service. |
| **Unified API & UI** | The FastAPI app is wrapped with a Gradio interface, allowing both programmatic access and an interactive web UI from a single entry point. |
| **Metric computation** | Implements token‑level true‑positive / false‑positive / false‑negative counting, precision, recall, F1, completeness, strict completeness and bootstrap / Wilson confidence intervals. |
| **Dataset handling** | Asynchronously loads dataset metadata, filters by arbitrary metadata attributes and builds a pandas DataFrame with question types and expected‑fact counts. |
| **Rating aggregation** | Merges human and LLM ratings, applies strict majority voting for boolean fields, and computes per‑question and per‑system aggregates. |
| **Visualisations** | Provides reusable plotting helpers for bar charts, scatter plots, box plots and histogram‑style correctness distributions. |
| **Configurable metadata** | API name and version are defined centrally, enabling consistent labeling across the UI. |
| **Modular project layout** | Separate modules for startup, calculations, data fetching, graph helpers and UI construction keep concerns isolated and promote extensibility. |
| **Dependency management** | Uses a `pyproject.toml` with pinned versions for core libraries (FastAPI, Gradio, Matplotlib, Scikit‑learn, NumPy, etc.) ensuring reproducible builds. |

---

## Use Cases  

1. **RAG System Benchmarking** – Load a collection of generated answers, compute recall/precision/F1 and completeness metrics, and compare multiple system configurations side‑by‑side.  
2. **Human vs. LLM Rating Analysis** – Visualise and contrast human‑provided ratings with automated LLM evaluations to assess alignment and bias.  
3. **Dataset Insight Generation** – Inspect the distribution of expected facts per question type, helping data curators understand dataset complexity.  
4. **Confidence‑Interval Reporting** – Produce statistically robust performance reports using Wilson or normal‑approximation intervals for proportion metrics.  
5. **Interactive Exploration** – End‑users can select datasets, system and evaluation configurations via the Gradio UI and instantly view updated charts and tables without writing code.  

---

## How It Works  

1. **Startup** – The `GraphViewApplication` registers logging and PostgreSQL startup sequences, then creates the evaluation and configuration use‑case instances [1].  
2. **Lifespan handling** – FastAPI’s `lifespan` context starts the application, runs asynchronous initialisation (`create_usecase`), and shuts down gracefully [2].  
3. **Data ingestion** – The platform fetches datasets through `EvaluationServiceUsecases`, optionally filtering by metadata, and prepares pandas DataFrames for analysis [7].  
4. **Metric calculation** – For each question, token‑level matches are derived, counts of TP/FP/FN are computed, and derived metrics (recall, precision, F1, completeness) are calculated, including confidence intervals via Wilson or normal‑approximation methods [3].  
5. **Aggregation** – Ratings from multiple annotators are merged using strict majority voting; per‑system and per‑evaluation aggregations are produced [5][9].  
6. **Visualization** – The prepared DataFrames feed the plotting helpers, generating bar, scatter, box, and histogram figures that are embedded in the Gradio UI [6][7].  

---

## Environment File (`.env`)

The Graph-View evaluation platform is configured entirely through environment variables.  
The following `.env` template covers logging, database access, and observability settings required for deployment.

### Logging

```
LOG_LEVEL=info
LOG_SECRETS=true
```

### PostgreSQL

```
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
POSTGRES_DATABASE=evaluation-db
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

Start the Graph-View server by loading your configuration and running FastAPI:

```bash
source .env
uvicorn graph_view.main:app --host 0.0.0.0 --port 8000
```

---

And here is the corresponding docker-compose snippet for completeness:

```yaml
graph-view-v02:
  image: graph-view
  container_name: graph-view-masterarbeit-v02
  ports:
    - 9005:8000
  environment:
    LOG_LEVEL: ${LOG_LEVEL}
    LOG_SECRETS: ${LOG_SECRETS}
    OTEL_HOST: ${OTEL_HOST}
    OTEL_ENABLED: ${OTEL_ENABLED}
    OTEL_INSECURE: ${OTEL_INSECURE}
    POSTGRES_HOST: ${POSTGRES_HOST}
    POSTGRES_PORT: ${POSTGRES_PORT}
    POSTGRES_DATABASE: ${POSTGRES_DATABASE}
    POSTGRES_USER: ${POSTGRES_USER}
    POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
  networks:
    - dev_env
```
