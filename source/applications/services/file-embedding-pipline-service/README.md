**File‑Embedding‑Pipline‑Service – Use‑Case Package**

---

### Overview  

The **file‑embedding‑pipline‑service** package implements the business logic that turns stored files into DocumentIndex.
It coordinates a file‑storage layer, a vector store (async document indexer), and the domain models that describe pages, text, images, tables, etc.

---

### Core Capabilities  

| Capability | What It Does |
|------------|--------------|
| **Singleton use‑case** | `EmbeddFilePiplineUsecase` inherits from `BaseSingleton`, guaranteeing a single shared instance throughout the application lifecycle. |
| **Dependency injection** | During `_init_once` the use‑case receives concrete implementations of `FileStorage`, an async vector store (`AsyncDocumentIndexer`), a `FileDatabase`, a configuration object, and an embedding configuration. These are stored as private attributes for later calls [5]. |
| **Embedding configuration** | A `EmbeddFilePiplineUsecaseConfig` model allows toggling of options such as `consider_images` (default `True`). |
| **Metadata handling** | When a file is processed, its metadata is normalised (date fields converted to strings) and merged with any additional metadata before being used to build the collection name for the vector store [5]. |
| **Document preparation** | The use‑case extracts pages (`Page`, `PageLite`) and fragments (`TextFragement`, `ImageFragment`, `TableFragement`, etc.) from the file, preparing them for embedding. |
| **DocumentIndexer* | After fragments are created, they are sent to the provided `AsyncDocumentIndexer` for asynchronous indexing, making the content searchable via similarity search. |
| **OpenTelemetry tracing** | A tracer named `"EmbeddFileUsecase"` is created and used to wrap the main embedding flow, providing end‑to‑end observability. |
| **Typed domain models** | Works with the rich domain models from `domain.file_converter.model` (pages, fragments, etc.), ensuring type safety throughout the pipeline. |

---

### Architecture Highlights  

- **Workspace‑based dependencies** – The package’s `pyproject.toml` lists `core` and `domain` as workspace dependencies, keeping versions aligned across the monorepo [1].  
- **Clear separation of concerns** – Persistence (`FileStorage`, `FileDatabase`), vector indexing (`AsyncDocumentIndexer`), and orchestration (`EmbeddFilePiplineUsecase`) are isolated behind interfaces, allowing easy replacement for testing or alternative implementations.  
- **Result‑oriented API** – Methods return `Result` objects, so callers can handle success and failure without raising exceptions, which simplifies async control flow.  

---

### Typical Workflow  

1. **Initialize the use‑case** – The framework calls `_init_once` once, providing the storage, indexer, database, and configuration objects. The tracer is also created at this point [5].  
2. **Fetch the file** – When `embedd_file` is invoked with a `file_id`, the use‑case retrieves the file from the `FileDatabase` (or storage) and extracts its metadata.  
3. **Prepare document fragments** – The file is parsed into a list of `Page` objects, then into lightweight `PageLite` fragments (text, images, tables, etc.).  
4. **Build collection name** – A collection identifier is constructed from the project ID and the embedding configuration ID, ensuring that embeddings are stored in the correct namespace.  
5. **Index fragments** – The prepared fragments are sent asynchronously to the `AsyncDocumentIndexer` for embedding and storage in the vector store.  
6. **Return result** – The method finishes with a `Result[None]` indicating success or propagating any error that occurred during the process.  

---

### Extensibility  

- **Document Index** – Implement another `AsyncDocumentIndexer` (e.g., a different embedding provider) and inject it without changing the use‑case logic.  
- **Custom fragment handling** – Extend or replace the fragment extraction logic to support additional file types or richer metadata.  
- **Configurable pipelines** – Add more fields to `EmbeddFilePiplineUsecaseConfig` (e.g., language detection, chunk size) and adjust the embedding flow accordingly.  
- **Enhanced observability** – Add custom attributes to the OpenTelemetry spans (file size, processing duration, number of fragments) for deeper monitoring.  


