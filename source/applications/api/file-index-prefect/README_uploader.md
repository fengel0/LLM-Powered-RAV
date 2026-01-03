# File-Uploader-Prefect

## Overview  
File-Uploader-Prefect is a lightweight, Prefect-driven service that continuously monitors a configurable directory, selects files of specified types, uploads them to an S3-compatible storage (MinIO), and records each upload in a PostgreSQL database.  
It builds on the **deployment-base** framework, providing structured startup sequences for logging, databases, and S3 connectivity. The upload process is exposed as a Prefect flow, making the service suitable for containerised and automated workflows.

---

## Key Features  

| Feature | Description |
|---------|-------------|
| **Directory Observation** | Watches a root directory and filters files by allowed extensions (`OBSERVE_DIR`, `FILE_TYPES_TO_OBSERVE`). |
| **Prefect Orchestration** | Uses Prefect tasks to identify new files, upload them, and emit domain events. |
| **S3 + PostgreSQL Integration** | Uploads file blobs to MinIO and persists metadata in PostgreSQL. |
| **Structured Startup** | Logging, DB connections, and S3 clients are initialised automatically. |
| **Event Emission** | Emits a `FILE_CREATED_UPDATES` event after successful uploads. |
| **Fully Configurable** | All runtime behaviour is controlled via environment variables. |
| **End-to-End Testing** | Includes a complete upload pipeline test using pytest. |

---

## Typical Use Cases  

* Continuous ingestion of PDFs or office documents into a data lake  
* Batch migration of large file folders to S3  
* Event-driven workflows that trigger downstream services when new files arrive  

---

## Environment File (`.env`)

The File-Uploader-Prefect service is configured **entirely** through environment variables.  
Below is a complete, ready-to-use `.env` template mirroring the expected deployment configuration.

### Logging

```
LOG_LEVEL=info
LOG_SECRETS=true
```

### Directory Watching

```
OBSERVE_DIR=/app/api/file-uploader-prefect/src/files
FILE_TYPES_TO_OBSERVE=pdf,docx,pptx
```

### PostgreSQL

```
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
POSTGRES_DATABASE=production-db
POSTGRES_USER=root
POSTGRES_PASSWORD=password-v2
```

### S3 / MinIO Storage

```
S3_HOST=http://minio:9000
S3_ACCESS_KEY=minio
S3_SECRET_KEY=minio123
S3_SESSION_KEY=
S3_IS_SECURE=false
```

### Prefect

```
PREFECT_API_URL=http://0.0.0.0:4200/api
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
python src/file_uploader_prefect/main.py
```

---

## Deployment Example  

A typical Docker Compose deployment:

```yaml
file-uploader-prefrect-v02:
  image: file-uploader-prefect:v02
  container_name: file-uploader-prefrect-masterarbeit-v02
  restart: unless-stopped
  networks:
    - dev_env
  environment:
    LOG_LEVEL: ${LOG_LEVEL}
    LOG_SECRETS: ${LOG_SECRETS}
    S3_HOST: ${S3_HOST}
    S3_ACCESS_KEY: ${MINIO_USER}
    S3_SECRET_KEY: ${MINIO_PASSWORD}
    S3_SESSION_KEY: ${S3_SESSION_KEY}
    S3_IS_SECURE: ${S3_IS_SECURE}
    OTEL_HOST: ${OTEL_HOST}
    OTEL_ENABLED: ${OTEL_ENABLED}
    OTEL_INSECURE: ${OTEL_INSECURE}
    PREFECT_API_URL: ${PREFECT_API_URL}
    OBSERVE_DIR: ${OBSERVE_DIR}
    POSTGRES_HOST: ${POSTGRES_HOST}
    POSTGRES_PORT: ${POSTGRES_PORT}
    POSTGRES_DATABASE: ${POSTGRES_DATABASE}
    POSTGRES_USER: ${POSTGRES_USER}
    POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    FILE_TYPES_TO_OBSERVE: ${FILE_TYPES_TO_OBSERVE}
  volumes:
    - ./files:/app/api/file-uploader-prefect/src/files
```

This configuration connects the service to S3/MinIO, PostgreSQL, OpenTelemetry, and Prefect while mounting the local directory it will observe for new files.
