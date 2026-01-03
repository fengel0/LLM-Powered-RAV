# file-converter-prefect  

## Overview  
`file-converter-prefect` is a **Prefect-based orchestration service** that reacts to file-creation events, runs a conversion pipeline, and (optionally) generates an AI-powered description of the resulting image. It integrates with a PostgreSQL-backed file store, a project database, an OpenAI client, and an S3-compatible object storage, providing a fully automated workflow for handling uploaded files in a micro-service architecture [1].

## Features  

| Feature | Description |
|---------|-------------|
| **Event-driven conversion** | Listens for `FILE_CREATED_UPDATES` events and triggers a Prefect flow that converts the file using the external *file-converter* service. |
| **Optional image description** | When the `ENABLED_IMAGE_DESCRIPTION` flag is true, the pipeline invokes the *image-description* service (OpenAI) to generate a textual description of the converted image. |
| **Robust persistence** | Uses `PostgresFileDatabase` and `PostgresDBProjectDatbase` for reliable storage of file metadata and project information. |
| **S3 integration** | Stores and retrieves files from an S3-compatible bucket (e.g., MinIO). |
| **Observability** | Emits Prefect events (`FILE_CONVERTED`) and supports OpenTelemetry for tracing. |
| **Configurable via environment** | All external endpoints, time-outs, and feature toggles are driven by environment variables defined in `settings.py`. |
| **Modular dependencies** | Declares a clean set of internal packages (`core`, `domain`, `rest-client`, `database`, `file-database`, `project-database`, `file-converter-client`, `prefect-core`, `image-description-service`, `s3`, `deployment-base`, `openai-client`). |

## Use Cases  

**Automated media pipelines** – Convert uploaded media files (PDF, DOCX, etc.) into a standardized format and optionally enrich them with AI-generated descriptions of images.  

---

## Environment File (`.env`)

The `file-converter-prefect` service is fully environment-driven.  
Below is a clean example `.env` file covering all expected configuration groups.

### Logging

```
LOG_LEVEL=info
LOG_SECRETS=true
```

### File Converter

```
FILE_CONVERTER_API=http://file-converter:8000
REQUEST_TIMEOUT_IN_SECONDS=6000
```

### Image Description (optional)

```
ENABLED_IMAGE_DESCRIPTION=false
SYSTEM_PROMPT=/app/api/file-converter-prefect/src/prompts/system.txt
PROMPT=/app/api/file-converter-prefect/src/prompts/prompt.txt
OPENAI_HOST=http://openai:8001
OPENAI_MODEL=gpt-image-1
```

### Prefect

```
PREFECT_API_URL=http://0.0.0.0:4200/api
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

### OpenTelemetry (optional)

```
OTEL_HOST=127.0.0.1:4317
OTEL_ENABLED=true
OTEL_INSECURE=true
```

---

## Configuration Summary  

| Variable | Purpose |
|----------|---------|
| `FILE_CONVERTER_API` | URL of the external file conversion service. |
| `REQUEST_TIMEOUT_IN_SECONDS` | Timeout for HTTP calls to the converter. |
| `ENABLED_IMAGE_DESCRIPTION` | Enables image captioning via OpenAI. |
| `SYSTEM_PROMPT` / `PROMPT` | Prompt templates for the image-description model. |
| `OPENAI_HOST` / `OPENAI_MODEL` | OpenAI endpoint and model selection. |
| `PREFECT_API_URL` | Prefect API to register and run flows. |
| `POSTGRES_*` | Connection details for the file and project databases. |
| `S3_*` | Configuration for S3/MinIO object storage. |
| `OTEL_*` | Optional OpenTelemetry tracing settings. |
| `LOG_*` | Logging verbosity and secret handling. |

---

## Deployment Example  

A typical Docker-Compose service definition might look like the following:

```yaml
file-converter-prefrect-v02:
  image: file-converter-prefect:v02
  container_name: file-converter-prefrect-masterarbeit-v02
  restart: unless-stopped
  networks:
    - dev_env
  environment:
    LOG_LEVEL: ${LOG_LEVEL}
    LOG_SECRETS: ${LOG_SECRETS}
    FILE_CONVERTER_API: ${FILE_CONVERTER_API}
    PREFECT_API_URL: ${PREFECT_API_URL}
    OTEL_HOST: ${OTEL_HOST}
    OTEL_ENABLED: ${OTEL_ENABLED}
    OTEL_INSECURE: ${OTEL_INSECURE}
    S3_HOST: ${S3_HOST}
    S3_ACCESS_KEY: ${MINIO_USER}
    S3_SECRET_KEY: ${MINIO_PASSWORD}
    S3_SESSION_KEY: ${S3_SESSION_KEY}
    S3_IS_SECURE: ${S3_IS_SECURE}
    POSTGRES_HOST: ${POSTGRES_HOST}
    POSTGRES_PORT: ${POSTGRES_PORT}
    POSTGRES_DATABASE: ${POSTGRES_DATABASE}
    POSTGRES_USER: ${POSTGRES_USER}
    POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    OPENAI_HOST: ${OPENAI_HOST}
    OPENAI_MODEL: ${IMAGE_MODEL}
  volumes:
    - ./prompts:/app/api/file-converter-prefect/src/prompts
```

This configuration wires the service to the required databases, object storage, OpenAI endpoint, and observability stack, while mounting the prompt files used for image description.
