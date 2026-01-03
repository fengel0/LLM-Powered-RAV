z
# text‑splitter

**text‑splitter** is a lightweight Python library that splits raw text into manageable chunks (nodes) for downstream processing such as embedding, retrieval‑augmented generation, or indexing.
It implements a hierarchical, token‑aware splitter that works on paragraphs, sentences, and sub‑sentence fall‑backs (regex → words → chars).
The splitter is language‑aware (via *pysbd*) and can be configured for chunk size, overlap, and truncation direction.

---

## What the package contains

| Module / File | Purpose |
|---------------|---------|
| `text_splitter/__init__.py` | Public entry point – exposes the `NodeSplitter` class that orchestrates the splitting process. |
| `text_splitter/node_splitter.py` | Core implementation: detects language, tokenises text, recursively splits by paragraph → sentence → sub‑sentence, and merges pieces into chunks respecting the configured size and overlap. |
| `pyproject.toml` | Project metadata, dependencies, optional test dependencies, and build configuration. |
| `tests/` | Unit‑ and integration‑tests that verify splitting behaviour for different languages, chunk sizes, and edge cases. |

The splitter relies on the following runtime dependencies (declared in `pyproject.toml`):

* `pysbd==0.3.4` – language‑aware sentence segmentation
* `tiktoken==0.12.0` – token counting
* `langdetect==1.0.9` – language detection for fallback handling【3】

Key implementation details can be seen in `node_splitter.py` where the recursive splitting algorithm prefers paragraph‑level splits, falls back to sentence‑level, and finally to regex/word/character splits when necessary.

---

## Installation

```bash
uv sync
```

```bash
# Run all tests
pytest
# or
./unittest.sh
```

If the repository contains a convenience script (e.g., `integrationstest.sh` used by other packages), you can invoke it directly; otherwise the generic `pytest` command above is sufficient.

---

## Configuration (high‑level)

When creating a `NodeSplitter` you can specify:

| Parameter | Meaning |
|-----------|---------|
| `chunk_size` | Maximum number of tokens per chunk (default is defined in the splitter config). |
| `chunk_overlap` | Number of tokens to overlap between consecutive chunks. |
| `default_language` | Fallback language for sentence segmentation (e.g., `"en"`). |

These options are passed via a `NodeSplitterConfig` data class (see `node_splitter.py`).

