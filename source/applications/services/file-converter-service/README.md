**File‑Converter‑Service – Use‑Case Package**

---

### Overview  

The **file‑converter‑service** package contains the business‑logic that drives the conversion of uploaded files into a structured, page‑level representation. It coordinates three main concerns:

1. **Persistence** – access to stored files (`FileDatabase`) and project metadata (`ProjectDatabase`).  
2. **External conversion** – a client (`FileConverterServiceClient`) that calls a remote file‑conversion micro‑service.  
3. **Observability** – OpenTelemetry spans and logging for full traceability of the conversion pipeline.  

The package is defined as a Python project with a strict version requirement (`>=3.12,<3.13`) and workspace‑linked dependencies on the shared `core` and `domain` libraries [1].

---

### Key Capabilities  

| Capability | What It Does |
|------------|--------------|
| **Singleton use‑case** | `ConvertFileUsecase` inherits from `BaseSingleton`, guaranteeing a single shared instance throughout the application lifecycle. |
| **Dependency injection** | During initialization the use‑case receives concrete implementations of `FileDatabase`, `ProjectDatabase`, the conversion client, and the application version. These are stored as attributes for later calls [3]. |
| **Project validation** | Before any conversion, the service fetches the associated project from `ProjectDatabase`. If the project cannot be found, a `NotFoundException` is returned, preventing unnecessary processing. |
| **File conversion orchestration** | The core method invokes `file_converter_service.convert_file`, passing the file name and the project bucket identifier. The external service returns a list of `Page` (or similar) objects that represent the converted content. |
| **Error handling & propagation** | All operations return a `Result` object. Errors from the project lookup or the conversion service are propagated unchanged, preserving the original exception type and message. |
| **OpenTelemetry tracing** | Each public operation is wrapped in a span (`self.tracer.start_as_current_span`) so the full conversion pipeline can be observed in distributed tracing systems. |
| **Logging** | Important steps (creation of the use‑case, errors, and successful conversions) are logged via the standard `logging` module. |
| **Typed domain models** | Works with domain models such as `File`, `FilePage`, `PageMetadata`, and `PageFragment`, ensuring type safety across the pipeline. |

---

### Architecture Highlights  

- **Workspace‑based dependencies** – The service depends on the shared `core` and `domain` workspaces, keeping versioning consistent across the monorepo [1].  
- **Clear separation of concerns** – Persistence, external conversion, and orchestration are isolated behind interfaces, allowing easy swapping of implementations (e.g., mock databases for testing).  
- **Result‑oriented API** – By returning `Result` objects, callers can handle success and failure without raising exceptions, simplifying async flow control.  

---

### Typical Workflow  

1. **Fetch and validate the project** – The use‑case retrieves the project using `ProjectDatabase`. If the project does not exist, a `NotFoundException` is returned.  
2. **Convert the file** – Within an OpenTelemetry span named “convert file”, the service invokes `file_converter_service.convert_file`, supplying the file name and the project bucket ID.  
3. **Handle the conversion result** – If the conversion succeeds, the list of `Page` objects is returned inside a successful `Result`. If the conversion fails, the error is propagated unchanged.  

These steps are implemented in the `ConvertFileUsecase` class and its `convert` method.

---

### Extensibility  

- **Alternative converters** – Implement another `FileConverterServiceClient` (e.g., a local library or a different remote service) and inject it without modifying the use‑case logic.  
- **Additional validation** – Insert extra checks (e.g., file‑type validation, size limits) before the conversion call by extending the `_init_once` method or adding pre‑span logic.  
- **Enhanced tracing** – Add custom attributes (e.g., file size, project tier) to the current span to enrich observability.  

