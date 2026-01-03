# Core Package

The **core** package provides fundamental building blocks and utilities used across the entire project. It includes configuration loading, logging, result handling, and singleton patterns that other packages depend on.

## Features

- **Config Loader** – Load configuration values from environment variables or files with type safety.
- **Singleton Base** – Easy-to-use thread‑safe singleton implementation.
- **Result Handling** – Consistent `Result` type for success/error propagation.
- **Logging Integration** – OpenTelemetry‑compatible logging with colourised console output.
- **Utility Functions** – Hashing, string handling, and queuing helpers.

## Modules

| Module | Description |
|--------|-------------|
| `config_loader` | Load, validate, and write configuration values. |
| `hash` | Simple hashing utilities. |
| `logger` | Set up OpenTelemetry logging, colour formatter, and tracing integration. |
| `model` | Pydantic models used across the core utilities. |
| `que_runner` | Helper for running background queues/tasks. |
| `result` | `Result` monad‑like class for functional error handling. |
| `singelton` | Thread‑safe singleton base class. |
| `string_handler` | String manipulation helpers. |

## Installation

The core package is part of the monorepo. To install its dependencies:

```bash
cd applications/lib/core
uv sync
```

## Usage Example

```python
from core.config_loader import ConfigLoaderImplementation, EnvConfigAttribute
from core.result import Result

# Define configuration attributes
attributes = [
   EnvConfigAttribute(
       name="APP_PORT",
       default_value=8000,
       value_type=int,
       is_secret=False,
   )
]

# Load configuration
config_loader = ConfigLoaderImplementation.create()
load_result: Result[None] = config_loader.load_values(attributes)

if load_result.is_ok():
   port = config_loader.get_int("APP_PORT")
   print(f"Application will run on port {port}")
else:
   print(f"Failed to load config: {load_result.error}")
```

## Development

Run tests:

```bash
cd applications/lib/core
pytest
```
---

For more detailed documentation, see the module source files in `src/core/`.
