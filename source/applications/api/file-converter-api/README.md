# file‑converter‑api  

**Version:** 0.2.0  

---

## Overview  

`file-converter-api` is a FastAPI‑based service that converts documents stored in an S3‑compatible bucket (e.g., MinIO) into Markdown format.
It supports a variety of source file types—including PDF, Microsoft Word, Excel, HTML, and plain‑text files—and writes the converted Markdown back to a target bucket.
The service is designed for automated pipelines, data‑extraction workflows, and any scenario where human‑readable markdown representations of documents are required.

---

## Features  

| Feature | Description |
|---------|-------------|
| **Multi‑format conversion** | PDF, Word, Excel, HTML, and TXT files are transformed into Markdown using dedicated converters (PDF → Markdown, Office → PDF → Markdown, Excel → Markdown, etc.) [4]. |
| **S3 integration** | Files are fetched from and stored to an S3‑compatible storage backend via the `MinioFileStorage` abstraction [4]. |
| **Configurable device** | The conversion pipeline can be run on CPU or GPU (device set via the `DEVICE` environment variable) [6]. |
| **FastAPI endpoint** | A single `PUT /convert` endpoint accepts the source bucket, destination bucket, and filename, then returns the conversion result [3]. |
| **Modular architecture** | Core logic is separated into use‑case (`ConvertFileToMarkdown`), API layer, and application startup components, facilitating testing and extension [5]. |
| **Dependency management** | Project dependencies are declared in `pyproject.toml`, ensuring reproducible builds [2]. |
| **Docker‑ready** | The service can be containerised and deployed with environment variables for logging, OpenTelemetry, and storage credentials [User provided deployment example]. |

---

## Use Cases  

- **Automated documentation pipelines** – Convert uploaded reports, specifications, or research papers to Markdown for downstream processing or static‑site generation.  
- **Data‑extraction workflows** – Extract text from heterogeneous document formats stored in object storage and feed it into NLP or indexing pipelines.  
- **Content migration** – Move legacy documents from office suites into a version‑controlled Markdown repository.  
- **Server‑less or micro‑service architectures** – Run the converter as a lightweight service behind an API gateway, scaling independently from other components.  

---

## Configuration & Environment Variables  

| Variable | Purpose | Default |
|----------|---------|---------|
| `DEVICE` | Execution device for converters (`cpu` or GPU identifier) | `cpu` |
| `S3_HOST` | Host address of the S3/MinIO service | – |
| `S3_ACCESS_KEY` / `S3_SECRET_KEY` | Credentials for S3 access | – |
| `S3_SESSION_KEY` | Optional session token | – |
| `S3_IS_SECURE` | Toggle TLS for S3 connection (`true`/`false`) | – |
| Logging & OpenTelemetry variables (`LOG_LEVEL`, `OTEL_HOST`, etc.) | Control observability output | – |

All variables are loaded through the core configuration loader (`ConfigLoaderImplementation`) at application start [5].

---

## Deployment  

The service is intended to run inside a container. Below is an example Docker‑Compose snippet illustrating the required environment variables and runtime configuration:

```yaml
services:
  file-converter-service:
    image: file-converter-api:v02
    container_name: file-converter-api
    environment:
      LOG_LEVEL: ${LOG_LEVEL}
      LOG_SECRETS: ${LOG_SECRETS}
      OTEL_HOST: ${OTEL_HOST}
      OTEL_ENABLED: ${OTEL_ENABLED}
      OTEL_INSECURE: ${OTEL_INSECURE}
      DEVICE: cpu
      S3_HOST: ${S3_HOST}
      S3_ACCESS_KEY: ${MINIO_USER}
      S3_SECRET_KEY: ${MINIO_PASSWORD}
      S3_SESSION_KEY: ${S3_SESSION_KEY}
      S3_IS_SECURE: ${S3_IS_SECURE}
    volumes:
      - ./disks/file-converter-api:/root/.cache
```

The container starts the FastAPI application on the configured host and port, ready to receive conversion requests.

---

