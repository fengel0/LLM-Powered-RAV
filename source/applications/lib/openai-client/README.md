
# OpenAI‑Client – Async OpenAI Wrapper

## Overview

`openai-client` provides a thin, **async‑first** wrapper around the official OpenAI Python SDK.  
It exposes three high‑level helper methods:

* `run_against_model` – simple text‑to‑text completion.  
* `run_image_against_multimodal_model` – text + image → text.  
* `get_structured_output` – text → typed JSON (via OpenAI’s JSON mode or tool‑calling mode).

The wrapper also integrates OpenTelemetry tracing and automatic retry handling, making it a drop‑in component for the HippoRAG ecosystem and any other async application that needs to call OpenAI models.  

The package metadata, Python version requirement, and dependencies are defined in its `pyproject.toml` file [1].

---

## Key Features

| Feature | Description |
|---------|-------------|
| **Fully asynchronous** | All calls use `await` and the `AsyncOpenAI` client under the hood. |
| **Retry logic** | The wrapper guarantees at least one attempt and retries up to the user‑specified `retries` value. |
| **OpenTelemetry tracing** | Each request is wrapped in a trace span (`openai-chat-stream`). |
| **Tokenisation utilities** | Uses `tiktoken` to expose the tokenizer for the selected model. |
| **Typed configuration** | `ConfigOpenAI` (a Pydantic model) validates all runtime settings. |
| **Convenient helper methods** | Text‑only, multimodal, and structured‑output helpers hide the low‑level OpenAI API details. |

---

## Installation

```bash
uv sync
```

The package requires Python 3.12‑3.13 and the following runtime dependencies [1]:

* `openai==1.109.1`
* `tiktoken==0.12.0`

---

## Quick Start


The wrapper automatically creates an OpenTelemetry span named `"OpenAIAsyncLLM"` for each request and handles tokenisation via `tiktoken` [20].

---

## Configuration Details (`ConfigOpenAI`)

| Field | Meaning | Default |
|-------|---------|---------|
| `api_key` | Your OpenAI API key (required). | – |
| `base_url` | Optional custom endpoint (e.g., self‑hosted OpenAI compatible server). | `https://api.openai.com/v1` |
| `model` | Default model used when `model` is not supplied per‑call. | `"gpt-4o"` |
| `temperature` | Sampling temperature (0.0 – 2.0). | `0.7` |
| `max_tokens` | Upper limit for generated tokens. | `1024` |
| `retries` | Number of retry attempts on recoverable errors (minimum 1). | `1` |
| `timeout` | HTTP timeout in seconds. | `60` |
| `tokinzer_model` | Tokeniser name for `tiktoken`. | Same as `model` |

All fields are validated by Pydantic, ensuring type safety before any request is sent [20].

---

## Error Handling & Retries

The wrapper catches the most common OpenAI exceptions (`BadRequestError`, `RateLimitError`, `APIError`) and retries the request up to `retries` times. After exhausting retries, the original exception is propagated as a `Result.Err` (see the `core.result` module used throughout HippoRAG).

---

## Testing

Two helper scripts are provided for CI:

* `integrationstest.sh` – runs the unit / integration suite for the async OpenAI client.  
* `integrationstest_local.sh` – sets environment variables for a local OpenAI‑compatible server (e.g., Ollama) before invoking the test runner.


*  ./integrationstest_local.sh 
* defines env variables for test
```bash
# Run against a local server
export OPENAI_HOST=http://192.168.83.3:11434/v1
export OPENAI_MODEL=llama3.2
export OPENAI_HOST_KEY=dummy
./integrationstest.sh
```

The test suite lives under `tests/` and verifies:

* correct construction of `ConfigOpenAI`  
* successful calls to each helper method  
* proper retry behavior on simulated failures  

---

