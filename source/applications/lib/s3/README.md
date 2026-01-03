# s3 Mini Wrapper

A lightweight Python wrapper around **MinIO** (Amazon S3 compatible) that provides a simple, typed interface for storing and retrieving files.  
It is built with **Pydantic** for configuration validation, **OpenTelemetry** for tracing, and returns results using a custom `Result` type.

---

---

## Features

- **Typed configuration** with Pydantic (`MinioFileStorageConfig`)  
- **Multiton connection management** – one `MinioConnection` per host  
- **OpenTelemetry tracing** for each operation  
- Returns a `Result` object (`Ok`/`Err`) to handle success and failure cleanly  
- Automatic handling of custom metadata stored in MinIO objects  

The core implementation can be found in `minio.py` where the `MinioConnection` class manages connections and the `fetch_file` method retrieves objects along with their metadata [1].

---

## Installation

```bash
uv sync
```

The package requires Python **3.12** ( < 3.13 ) and the following dependencies are declared in `pyproject.toml` [2]:

- `minio==7.2.18`

Optional test dependencies:

```bash
uv pip install .[test]   # installs testcontainers, domain-test, etc.
```

---

## Configuration

Create a `MinioFileStorageConfig` instance with the connection details:

```python
from minio_wrapper.minio import MinioFileStorageConfig

config = MinioFileStorageConfig(
    host="play.min.io",
    access_key="YOUR_ACCESS_KEY",
    secret_key="YOUR_SECRET_KEY",
    sesssion_token=None,   # optional
    secure=True            # use TLS?
)
```

The fields are:

| Field | Description |
|-------|-------------|
| `host` | MinIO server host (e.g., `play.min.io`) |
| `access_key` | Access key / username |
| `secret_key` | Secret key / password |
| `sesssion_token` | Session token for temporary credentials (optional) |
| `secure` | Whether to use HTTPS (TLS) |

---

## Testing

The repository includes integration tests for the MinIO wrapper. Run them with:

```bash
pytest tests/minio_tests.py
```

(Or invoke the helper script `integrationstest.sh` which runs the same command).

Make sure Docker is running, as the tests use `testcontainers` to spin up a temporary MinIO container.

