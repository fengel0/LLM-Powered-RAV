# Dataset-File-Loader Prefect

A Prefect-based service that ingests a variety of datasets (JSON, CSV, JSON-Lines, PDFs, etc.) and uploads them into the **File-Uploader backend**.  
It connects:

- **Tortoise-ORM** models across multiple internal databases (`file_database`, `project_database`, `validation_database`, …)  
- A **PostgreSQL** session created at startup  
- **Prefect tasks** that parse source files, convert them to Pydantic models, and call `UploadeFilesUsecase.custom_upload`  
- Optional **MinIO / S3** file storage  

The entry point is:

```
src/dataset_file_loader_prefect/main.py
```

This script builds the application, wires all components together, and runs the desired Prefect flow.

---

## Table of Contents

1. [Prerequisites](#prerequisites)  
2. [Installation](#installation)  
3. [Configuration (Environment Variables)](#configuration-environment-variables)  
4. [Running the Service](#running-the-service)  
5. [Available Prefect Tasks](#available-prefect-tasks)  
6. [UploadeFilesUsecase](#uploadefilesusecase)  
7. [Testing](#testing)  
8. [License](#license)  

---

## Prerequisites

| Requirement | Version / Details |
|------------|-------------------|
| **Python** | 3.12 (`>=3.12,<3.13`) |
| **PostgreSQL** | Any reachable instance |
| **MinIO / S3** | Optional object storage |
| **Prefect** | Used for orchestration |
| **uv** | Recommended package manager |

Install dependencies:

```bash
uv sync
```

---

## Configuration – Environment Variables

The service reads **all configuration from environment variables**. The most important ones are below.


---

### S3 / MinIO Object Storage

| Variable | Description |
|---------|-------------|
| `S3_HOST` | Base URL of the S3/MinIO endpoint (`http://minio:9000`) |
| `S3_ACCESS_KEY` | Access key (mapped to `${MINIO_USER}`) |
| `S3_SECRET_KEY` | Secret key (mapped to `${MINIO_PASSWORD}`) |
| `S3_SESSION_KEY` | Optional session token |
| `S3_IS_SECURE` | `true` → HTTPS, `false` → HTTP |

---

### PostgreSQL Metadata Database

| Variable | Purpose |
|---------|---------|
| `POSTGRES_HOST` | Hostname |
| `POSTGRES_PORT` | Typically `5432` |
| `POSTGRES_DATABASE` | Target DB name |
| `POSTGRES_USER` | Username |
| `POSTGRES_PASSWORD` | Password |

Stores metadata for each uploaded file.

---

### Logging

**LOG_LEVEL**  
```
DEBUG | INFO | WARN | ERROR
```

**LOG_SECRETS**  
Whether secrets may appear in logs.

```
true  | false
```

---

### Prefect Integration

**PREFECT_API_URL**  
URL of the Prefect API server.

Example:
```
http://prefect:4200/api
```

---

### Telemetry & Observability

| Variable | Purpose |
|----------|---------|
| `OTEL_HOST` | OpenTelemetry collector endpoint |
| `OTEL_ENABLED` | Enables telemetry (`true` / `false`) |
| `OTEL_INSECURE` | Enables insecure mode for OTLP |

---

### Volume Mapping (File Input)

```
./files:/app/api/file-uploader-prefect/src/files
```

This directory contains all files that the watcher will process.

---

## Running the Service

Use the helper script:

```bash
./start_application.sh
```

During startup:

1. Logger initializes  
2. PostgreSQL session created  
3. ORM model modules registered  
4. Prefect tasks loaded  
5. Prefect flow becomes available

---

## Available Prefect Tasks

| Task | Description | Location |
|------|-------------|----------|
| `upload_graphrag_bench` | Reads GraphRAG-Bench JSON and uploads each QA record | `graphrag_bench.py` |
| `upload_docbench` | Walks a directory and uploads PDFs | `upload_docbench.py` |
| `upload_docdial` | Streams `.txt` documents to the *docdial* project | `upload_docdial.py` |
| `upload_dragonball` | Uploads entries from a JSON-Lines dataset | `upload_dragonball.py` |
| `upload_multi_hop` | Processes a news-article dataset | `upload_multi_hop.py` |
| `upload_kg_rag` | Uploads QA CSV rows for KG-RAG | `upload_kg_rag.py` |
| `upload_wikitable` | Handles “wikitablequestions”-style datasets | `upload_tabeldataset.py` |
| `startup` / `shutdown` | Lifecycle hooks | `prefrect_tasks.py` |
| `upload_dataset` | Example full pipeline | `prefrect_tasks.py` |

---

## UploadeFilesUsecase

This is the core component powering all uploads. It wires together:

- **MinIO/S3 storage** (`MinioFileStorage`)  
- **File metadata DB** (`PostgresFileDatabase`)  
- **Project registry** (`PostgresDBProjectDatabase`)  
- **Supported file types** (currently unrestricted)  
- **Root directory & versioning**

All tasks call:

```
UploadeFilesUsecase.custom_upload(...)
```

This saves the file, registers metadata, and emits an event for downstream pipelines.

---

## Testing

Run the end-to-end test:

```bash
bash tests/end_to_end_file_uploader.sh
```

Which executes:

```bash
pytest tests/end_to_end_file_uploader.py
```

---
