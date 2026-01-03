# Config‑Service Usecases – README  

## Overview  
The **config‑service** package bundles a small set of high‑level use‑case classes that encapsulate all interactions with the configuration layer of the application. Their responsibilities are:

| Use‑case class | Primary tasks |
|----------------|---------------|
| **`ConfigServiceUsecases`** | • Holds references to the system‑wide configuration database (`SystemConfigDatabase`) and the RAG configuration database (`RAGConfigDatabase`). <br>• Instantiates an OpenTelemetry tracer named **“ConfigServiceUsecase”** for end‑to‑end observability. |
| **`ConfigEvalUsecases`** (part of the same module) | • Retrieves grading‑service configuration IDs (`get_grading_configs`). <br>• Retrieves all RAG system configuration IDs (`get_system_configs`). |
| **`ConfigLoaderUsecase`** (generic) | • Loads a stored configuration object by its ID (`load_from_id`). <br>• Updates an existing configuration by applying a user‑provided lambda (`load_config_update_config`). <br>• Persists a new configuration back to the loader (`write_config`). |

All use‑cases rely on the **Result** wrapper (from `core.result`) to surface success or error states in a functional style.

---

## Detailed Tasks  

### 1. `ConfigServiceUsecases`  
*Location:* `config_eval.py`  

*Initialization* – The singleton is created once via `_init_once`, where it receives the concrete implementations of `SystemConfigDatabase` and `RAGConfigDatabase`. It also creates a tracer for tracing all subsequent operations **[5]**.  

*Typical responsibilities*  

- Provide a central point to access the two configuration databases.  
- Ensure that any operation performed by downstream use‑cases is automatically traced for observability.

---

### 2. `ConfigEvalUsecases` (part of the same file)  

| Method | What it does | Return type |
|--------|--------------|-------------|
| `get_grading_configs` | Calls `SystemConfigDatabase.fetch_by_config_type` for the `GradingServiceConfig` model, extracts a human‑readable identifier (`system_name‑model‑config_id`) and returns a list of `(display_name, config_id)` tuples. Errors are propagated via `Result.Err`. | `Result[list[Tuple[str, str]]]` |
| `get_system_configs` | Calls `RAGConfigDatabase.fetch_all` to obtain every RAG system configuration, then builds the same `(display_name, config_id)` tuple list. | `Result[list[Tuple[str, str]]]` |

Both methods handle error cases gracefully and wrap the final list in a `Result.Ok` **[5]**.

---

### 3. `ConfigLoaderUsecase[T]` (generic)  

*Location:* `config_storage.py`  

*Key responsibilities*  

- **Loading a configuration by ID** – `load_from_id(id)` forwards the request to the underlying `ConfigDatabase.get_config_by_id`. It returns `Result[T | None]`.  
- **Updating a stored configuration** – `load_config_update_config(key, update_lamda)` follows these steps:  
  1. Retrieve the file‑based configuration holder via `ConfigLoader.get_model`.  
  2. If the holder exists but has no stored config, load it from the database (`_load_from_id`).  
  3. If a stored config is present, apply the supplied `update_lamda` to produce a new model instance and persist the changes (`_load_update_attributes`).  
  4. Return the updated configuration wrapped in `Result.Ok` or an error if the key is missing. **[6]**  

- **Persisting a configuration** – `write_config` writes the final configuration back through the `ConfigLoader`.  

These tasks make the loader a single entry point for “read‑modify‑write” cycles on configuration objects.

---

## How the Pieces Fit Together  

1. **Application start‑up** creates a `ConfigServiceUsecases` singleton, wiring the concrete database implementations.  
2. Business logic that needs configuration IDs calls `ConfigEvalUsecases.get_grading_configs` or `get_system_configs`.  
3. When a specific configuration must be read, modified, or created, the code instantiates a `ConfigLoaderUsecase` with the appropriate model type and uses its `load_from_id`, `load_config_update_config`, or `write_config` methods.  
4. Throughout the flow, OpenTelemetry traces are emitted automatically, enabling observability across the whole configuration lifecycle.

---
