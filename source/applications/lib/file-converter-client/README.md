# File‑Converter‑Client Package

## Overview

`file-converter-client` provides a thin, asynchronous client for the **File Converter** service.  
It implements the `FileConverterServiceClient` interface defined in the `domain` package and uses the shared `AsyncHttpClient` for HTTP communication.  

The client is built around **OpenTelemetry** tracing, **Pydantic** configuration, and a functional `Result` wrapper for error handling.

## Features

- **Async API** – all calls are `async` and integrate with the rest of the async stack.
- **OpenTelemetry tracing** – each request is wrapped in a span (`convert-file‑<filename>`), enabling end‑to‑end observability.
- **Strong typing** – request/response payloads are modelled with Pydantic (`FileConverterConfig`, `PageLite`).
- **Result‑based error handling** – success and failure are represented by `Result.Ok` and `Result.Err`.
- **Zero‑configuration defaults** – only a host URL is required.

## Installation

The package uses **uv** for dependency management. From the repository root:

```bash
cd applications/lib/file-converter-client
uv sync
```

## API Reference

### `FileConverterConfig`

A Pydantic model used to configure the client.

| Field | Type | Description |
|-------|------|-------------|
| `host` | `str` | Base URL of the File‑Converter service (e.g., `http://localhost:8000`). |

### `FileConverterServiceClientImpl`

Implements `FileConverterServiceClient`.

#### Constructor
## Development

- **Running tests** – the test suite lives under `tests/`. Execute with:

  ```bash
  uv run pytest
  ```
