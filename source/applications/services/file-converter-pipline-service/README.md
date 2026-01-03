**File‑Converter‑Pipeline‑Service – Use‑Case Package**

---

## Overview  

The **file-converter-pipeline-service** package implements the business‑logic for converting uploaded files into a structured page‑level representation. It orchestrates the interaction between a file storage layer, a project metadata layer, and an external file‑conversion micro‑service, while exposing tracing and error‑handling utilities.  

*Project metadata* (name, version, Python requirement, and workspace‑linked dependencies) is defined in its `pyproject.toml` file [1].

---

## Core Capabilities  

| Capability | What it does |
|------------|--------------|
| **Singleton use‑case** | `ConvertFileUsecase` inherits from `BaseSingleton`, guaranteeing a single shared instance throughout the application lifecycle. |
| **Dependency injection** | At initialization the use‑case receives a `FileDatabase`, a `ProjectDatabase`, a `FileConverterServiceClient`, and the current application version. These are stored as instance attributes for later calls. |
| **Project validation** | Before conversion begins, the service fetches the associated project from `ProjectDatabase`. If the project cannot be found, a `NotFoundException` is returned, preventing unnecessary work. |
| **File conversion orchestration** | The core method calls the external `FileConverterServiceClient.convert_file`, passing the filename and the project bucket identifier. The result is a list of `Page` objects (or similar fragments) that represent the converted content. |
| **Error propagation** | All operations return a `Result` object. Errors from the project lookup or the conversion service are propagated unchanged, preserving the original exception type and message. |
| **OpenTelemetry tracing** | Each public operation is wrapped in a span (`self.tracer.start_as_current_span`) so that the full conversion pipeline can be observed in distributed tracing systems. |
| **Logging** | Important steps (creation of the use‑case, errors, and successful conversions) are logged via the standard `logging` module. |
| **Typed domain models** | The service works with domain models such as `File`, `FilePage`, `PageMetadata`, and `PageFragment`, ensuring type safety across the pipeline. |

---

## Architecture Highlights  

- **Workspace‑based dependencies** – The package depends on the shared `core` and `domain` workspaces, keeping versioning consistent across the monorepo.  
- **Clear separation of concerns** – Persistence (`FileDatabase`, `ProjectDatabase`), external conversion (`FileConverterServiceClient`), and orchestration (`ConvertFileUsecase`) are isolated behind interfaces, allowing easy swapping of implementations (e.g., mock databases for testing).  
- **Result‑oriented API** – By returning `Result` objects, callers can handle success and failure without raising exceptions, simplifying async flow control.  

---

## Typical Workflow  

1. **Fetch and validate the project** – The use‑case retrieves the project using `ProjectDatabase`. If the project does not exist, a `NotFoundException` is returned.  
2. **Convert the file** – Within an OpenTelemetry span named “convert file”, the service invokes `file_converter_service.convert_file`, supplying the file name and the project bucket ID.  
3. **Handle the conversion result** – If the conversion succeeds, the list of `Page` objects is returned inside a successful `Result`. If the conversion fails, the error is propagated unchanged.  



