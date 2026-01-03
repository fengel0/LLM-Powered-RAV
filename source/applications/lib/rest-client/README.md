
# REST‑Client Wrapper

## Introduction
**REST‑Client** is a lightweight Python wrapper that provides a unified interface for making HTTP requests both synchronously (using `requests`) and asynchronously (using `httpx`).
It is designed for projects that need reliable HTTP communication while automatically collecting tracing information and request‑duration metrics.

## Features
- **Dual‑mode operation** – choose between synchronous and asynchronous clients depending on your workload.  
- **Built‑in OpenTelemetry tracing** – each request starts a span (`http.<method> <url>`) and propagates the trace context via header injection.  
- **Request‑duration histogram** – every request records its total time, tagged with HTTP method, status code, and URL, enabling easy performance monitoring.  
- **Automatic response handling** – attempts to parse JSON responses and falls back to plain‑text when JSON parsing fails.  
- **Streaming support (async)** – can stream text chunks from a response while still measuring total duration.  
- **Configurable timeout** – both clients respect a user‑defined timeout value.  

These capabilities are implemented in the async client (`async_client.py`) and sync client (`sync_client.py`) modules.

## Installation
```bash
uv sync
```
The package requires Python 3.12–3.13 and depends on:
- `httpx==0.28.1`
- `requests==2.32.5`

## Configuration
When creating a client instance you can specify:
- **Base URL** – the root endpoint for all requests.  
- **Headers** – default headers that will be merged with per‑request headers.  
- **Timeout** – maximum time to wait for a response.  

Both clients accept the same configuration options, ensuring a seamless switch between sync and async usage.

## Usage Overview
1. **Instantiate the client** (choose `RestClientSync` or `RestClientAsync`).  
2. **Call HTTP methods** (`GET`, `POST`, `PUT`, `DELETE`) with the target URL, optional headers, and an optional JSON payload.  
3. **Handle the response** – the wrapper returns an object containing the status code, raw body, and parsed JSON (if applicable).  
4. **Observe metrics** – request durations are automatically recorded in a histogram that can be exported to your monitoring system.  
5. **Leverage tracing** – each request is traced, making it easy to correlate HTTP calls across distributed services.

## Metrics & Tracing
- **Histogram** – records request duration with the tags `http.method`, `http.status_code`, and `http.url`.  
- **OpenTelemetry spans** – automatically created for each request, with context propagation via the `inject` function.

These observability features are baked into the request flow for both sync and async paths.

