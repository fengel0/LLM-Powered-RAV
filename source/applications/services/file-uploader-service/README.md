
**File‑Uploader‑Service – Use‑Case Package**

---

### What the package does  

The **file‑uploader‑service** package implements the business logic for receiving, storing, and version‑controlling files that belong to a specific project.
It coordinates a file‑storage backend, a file‑metadata database, and a project database, while applying rules about supported file types and handling updates across application versions.

---

### Core capabilities  

| Capability | Description |
|------------|-------------|
| **Singleton use‑case** | `UploadeFilesUsecase` inherits from `BaseSingleton`, guaranteeing a single shared instance throughout the application lifecycle. |
| **Dependency injection** | The `_init_once` method receives concrete implementations of `FileStorage`, `FileDatabase`, `ProjectDatabase`, a list of supported file extensions, a root directory for temporary files, and the current application version. These are stored as instance attributes for later calls [8]. |
| **Project handling** | If a project does not exist, the service falls back to a default project name (`"default_project"`), defined in `defaults.py` [7]. |
| **Supported file‑type validation** | The service checks the file’s suffix against a configurable list of allowed extensions before accepting the upload. |
| **Version‑aware update logic** | When a file already exists, the service determines whether an update is required based on: <br>• the file not existing (`NotExisting`) <br>• a newer application version (`NewVersionOfApplication`) <br>• a newer file version (`NewVersionOfFile`) <br>• or no change needed (`NoReasonForUpdate`). This logic is expressed by the `ReasonForUpdate` enum [8]. |
| **Metadata generation** | For each uploaded file a `FileMetadata` object is created, containing a deterministic hash (via `compute_mdhash_id`), timestamps, the originating project ID, and the current application version. |
| **Storage interaction** | The file is written to the configured `FileStorage` backend (e.g., an S3 bucket or local filesystem) and a reference is stored in the `FileDatabase`. |
| **OpenTelemetry tracing** | A tracer named `"UploadeFilesUsecase"` is created and used to wrap the entire upload flow, providing end‑to‑end observability of the operation. |
| **Error handling** | All public methods return a `Result` object, allowing callers to handle success and failure without raising exceptions. Errors such as missing files, unsupported types, or storage failures are propagated via `Result.Err`. |
| **Typed models** | The service works with Pydantic models (`UploadedFiles`, `File`, `FileMetadata`, `Project`) from the shared `domain` package, ensuring type safety. |

---

### Typical workflow  

1. **Initialization** – The framework calls `_init_once` once, providing the storage, databases, supported extensions, root directory, and application version. A tracer is also created at this point.  
2. **Upload request** – A client invokes the upload use‑case with a filename, target bucket (project ID), and file content.  
3. **Project resolution** – The service looks up the project in `ProjectDatabase`. If it does not exist, the default project (`"default_project"`) is used.  
4. **File‑type check** – The file suffix is compared against the configured list of allowed extensions; if it is not allowed, the operation fails.  
5. **Version decision** – The service determines the appropriate `ReasonForUpdate` (e.g., new version of the file or application) and proceeds accordingly.  
6. **Metadata creation** – A deterministic hash of the file content is computed, timestamps are added, and a `FileMetadata` record is built.  
7. **Storage** – The file is saved to the configured `FileStorage` backend, and a corresponding `File` entry is persisted in `FileDatabase`.  
8. **Result** – The method returns `Result[UploadedFiles]` containing the identifiers of the stored files, or an error if any step failed.  

---

### Extensibility  

- **Alternative storage backends** – Implement a new `FileStorage` (e.g., cloud object store, database BLOB) and inject it without changing the use‑case logic.  
- **Additional validation rules** – Extend the upload flow with virus scanning, checksum verification, or size limits by adding checks before the storage step.  
- **Custom project resolution** – Replace the default‑project fallback with a more sophisticated project‑creation strategy if needed.  
- **Enhanced tracing** – Add custom attributes (e.g., file size, user ID) to the OpenTelemetry span for deeper monitoring.  

---

