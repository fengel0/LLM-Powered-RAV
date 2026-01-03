# pdf‑converter

**pdf‑converter** is a lightweight Python package that turns common document formats into a simple, uniform
representation – a list of `Page` objects containing `TextFragement`, `TableFragement`, and (optionally)
`ImageFragement`.  
The package ships three ready‑to‑use converters:

| Converter | Supported format | What it does |
|-----------|------------------|--------------|
| **SimpleTXTConverter** | `.txt` / `.text` | Wraps an entire file in one `TextFragement` (no pagination, no tables). |
| **SimpleHTMLConverter** | `.html` | Converts HTML to Markdown with `markdownify`, splits the document into a single `Page`. |
| **MarkerPDFConverter** | `.pdf` | Uses the *Marker* framework to render PDFs to Markdown, then splits them into pages based on a pagination marker. |



## ⚙️ Installation

```bash
# Install the package with all its runtime dependencies
uv sync
```

`pyproject.toml` lists the core dependencies:  
- `marker-pdf` for PDF rendering  
- `markdownify` for HTML → Markdown conversion  


## 🧪 Testing


```bash
./unittest.sh
```

