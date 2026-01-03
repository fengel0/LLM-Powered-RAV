# FastAPI‑Core Package

## Overview

`fastapi-core` provides a lightweight, opinionated foundation for building FastAPI services.  
The heart of the package is the abstract **`BaseAPI`** class (`src/fastapi_core/base_api.py`) which bundles together:

* **FastAPI app** creation with configurable title and version.
* **OpenTelemetry** instrumentation (traces, metrics, logging).
* **Prometheus** metrics exposition (`/metrics`).
* **Health‑check** endpoint (`/health`).
* **CORS** handling via a configurable `CORSMiddleware`.
* **Global error handling** that maps common Python exceptions to appropriate HTTP responses.

Concrete services simply subclass `BaseAPI` and implement the abstract `_register_api_paths` method to expose their own routes.

## Features

- **Abstract base class** – enforces a consistent service skeleton.  
- **Automatic metrics** – Prometheus endpoint and OpenTelemetry OTLP exporter.  
- **Health endpoint** – `/health` returns service status, title, and version.  
- **CORS support** – configurable via `CorsConfig` (defaults to permissive `*`).  
- **Global error handling** – maps `ValueError`, `KeyError`, `NotFoundException`,
  `PermissionError` to proper HTTP status codes.  
- **Minimal dependencies** – only FastAPI, Pydantic, OpenTelemetry, Prometheus‑FastAPI,
  and Starlette.

## Quick start

### Prerequisites

* Python 3.9+  
* **`uv`** for package management (recommended). Install it with:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

* The `domain` package (provides `NotFoundException`) should be installed in
  editable mode if needed:

### Installation

From the repository root:

```bash
cd applications/lib/fastapi-core
uv sync
```

### Running a service

Create a concrete implementation, e.g. `my_service.py`:

```python
from fastapi_core.base_api import BaseAPI, CorsConfig
from fastapi import APIRouter

class MyAPI(BaseAPI):
    def _register_api_paths(self):
        @self.app.get("/hello")
        async def hello(name: str = "world"):
            return {"message": f"Hello, {name}!"}


# Instantiate and expose the ASGI app
api = MyAPI(title="My Service", version="0.1.0", cors_config=CorsConfig())
app = api.get_app()
```

Run with any ASGI server, e.g. `uvicorn`:

```bash
uvicorn my_service:app --host 0.0.0.0 --port 8000
```

Open your browser (or curl) and visit:

* `http://localhost:8000/health` – health check.  
* `http://localhost:8000/metrics` – Prometheus metrics.  
* `http://localhost:8000/hello?name=FastAPI` – example route.

## Development

- **Adding new routes** – implement them inside `_register_api_paths` of your subclass.  
- **Extending error handling** – modify `_register_error_handling` in `BaseAPI` or subclass it for custom behaviour.  
- **Running tests** – the package includes a test suite under `tests/`. Run with:
