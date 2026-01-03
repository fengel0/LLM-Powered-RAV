
# HippoRAG Database – State Store Implementation  

This package implements the **state‑store** component of HippoRAG.  
It provides the persistence layer that maps:

* **chunks ↔ entities & facts**  
* **entities ↔ chunks**  
* **facts ↔ chunks**  

and stores arbitrary **metadata** attached to each document.  

---

## Overview  

The HippoRAG Database is a lightweight PostgreSQL‑backed store that keeps the relationships between textual chunks, the entities/facts extracted from them, and the surrounding metadata. It is used by the HippoRAG pipeline to:

* retrieve the entities/facts that belong to a particular chunk  
* look up a document’s metadata (e.g., source, timestamps)  

The implementation follows the `StateStore` interface defined in the `domain.hippo_rag.interfaces` module.

---

## Key Features  

| Feature | Description |
|---------|-------------|
| **Bidirectional mapping** | Efficient many‑to‑many tables (`EntNodeChunkDB` and `TripleToDocDB`) link chunks ↔ entities/facts. |
| **Metadata storage** | The `OpenIEDocumentDB` model stores the full passage, extracted entities, triples, and a flexible JSON‑field for arbitrary metadata. |
| **Bulk operations** | Helper methods in `state_holder.py` batch‑insert and fetch records to minimise round‑trips. |
| **Async API** | All database interactions are asynchronous, compatible with modern async‑first applications. |
| **Test‑ready** | Integration test scripts (`integrationstest.sh`, `integrationstest_local.sh`) are provided for CI pipelines. |

---

## Package Structure  

```
hippo_rag_database/
│
├─ model.py                # Tortoise‑ORM models and conversion helpers [8]
│   ├─ TripleToDocDB       # maps a triple hash → document ID
│   ├─ EntNodeChunkDB      # maps an entity node → chunk ID
│   └─ OpenIEDocumentDB    # stores passages, entities, triples & metadata
│
├─ state_holder.py         # High‑level StateStore implementation [7]
│   ├─ async methods to insert, fetch and upsert mappings
│   └─ utility functions for chunked processing
│
├─ pyproject.toml          # Package metadata and dependencies [1]
│
└─ tests/
    ├─ test_state_holder_integration.py
    └─ vectore_store_integration.py   (used by other HippoRAG components)
```

### Important Modules  

* **`model.py`** – defines the database tables using Tortoise‑ORM and provides conversion helpers between domain objects (`Document`, `Triple`) and ORM instances.  
* **`state_holder.py`** – implements the `StateStore` interface: inserting new chunk‑entity links, fetching chunks for a set of entity hashes, and managing metadata.  

---

## Testing  

Two helper scripts are provided:

* `integrationstest.sh` – runs the generic test suite (`pytest`).  
* `integrationstest_local.sh` – sets environment variables for a local embedding service before invoking the test runner.  

```bash
# Run all integration tests
./integrationstest.sh
```

The state‑store tests (`tests/test_state_holder_integration.py`) verify correct insertion, retrieval, and deduplication behavior.

---

