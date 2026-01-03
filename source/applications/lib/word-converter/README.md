**word‑converter**  

---

### Overview  

`word-converter` is a Python package that transforms Microsoft Word and PowerPoint files (`.doc`, `.docx`, `.ppt`, `.pptx`) into PDF format and then forwards the resulting PDF to a downstream PDF‑aware converter.
It is built for asynchronous pipelines, includes OpenTelemetry tracing, and follows the same clean‑architecture style as the other conversion utilities in the repository.  

---

### Key Features  

| Feature | Description |
|---------|-------------|
| **Office‑to‑PDF conversion** | Uses LibreOffice in head‑less mode to render Office documents as PDFs. |
| **Supported formats** | Handles `.doc`, `.docx`, `.ppt`, and `.pptx` files (case‑insensitive). |
| **Pluggable PDF converter** | After PDF generation, the package delegates conversion to any injected `FileConverter` that supports PDFs. |
| **OpenTelemetry tracing** | Each conversion step is wrapped in a tracing span (`office-to-pdf`). |
| **Simple API** | Provides `does_convert_filetype` and `convert_file` methods that return a `Result` object. |
| **Dependency‑managed** | Relies on the shared `domain`, `core`, and `pdf-converter` packages within the workspace. |

Supported extensions are defined in the `_SUPPORTED_EXTS` constant of `OfficeToPDFConverter` [5].

---

### Installation  

```bash
uv sync
```  

The package requires **Python 3.12** (up to but not including 3.13) and the following core dependencies, as declared in its `pyproject.toml` file [2]:  

- `pandas==2.3.3` (used by related converters)  
- `tabulate==0.9.0`  
- `xlrd==2.0.2`  

Optional test dependencies can be installed with the `test` extra:  

```bash
uv sync --all-extras
```  

---

### Usage Pattern (no code example)  

1. **Create a PDF‑converter** that implements the `FileConverter` interface and declares support for the `"pdf"` filetype.  
2. **Instantiate `OfficeToPDFConverter`** with the PDF‑converter as a dependency.  
3. **Call `does_convert_filetype`** to verify that a given filename is a supported Office type.  
4. **Invoke `convert_file`** with the path to the Office document; the method will:  
   - Convert the file to PDF via LibreOffice.  
   - Pass the generated PDF to the injected PDF‑converter.  
   - Return a `Result` containing a list of `Page` objects or an error.  

All steps are traced under the `"office-to-pdf"` span for observability.

---

### Testing  

The project defines a test suite that can be executed with `pytest`. Run the tests with:

```bash
pytest
```  

(Tests are located in the repository’s `tests/` directory and use the optional `testcontainers` dependency.)

