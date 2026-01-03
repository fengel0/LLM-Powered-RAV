# Fact Counting and Recall Visualization Toolkit

This project analyzes fact annotations inside a dataset, computes per-category recall metrics, and produces recall diagrams for different fact areas. It is designed for evaluating how well systems retrieve or reference facts across multiple categories.

---

## Overview

The toolkit consists of two main scripts:

**`count_facts.py`**  
Extracts, cleans, and counts fact entries stored inside a column such as `expected_facts`, producing numeric fact counts per row and generating a consolidated dataset.

**`recall_diagram.py`**  
Loads the processed data, groups it by fact category, and creates visual plots of recall values across categories. The script generates two diagrams:
- **Antwort-Recall**
- **Kontext-Recall**

Both scripts work together to help quantify factual coverage and recall performance.

---

## `count_facts.py`

### Responsibilities

- Loads the raw dataset (CSV or JSON depending on how the file is executed)
- Extracts fact strings from `expected_facts` or similarly structured fields
- Uses regex patterns to separate multiple fact entries stored in a single cell
- Normalizes empty or malformed entries
- Produces:
  - **Total fact counts per row**
  - **A cleaned dataset saved to disk**

### Output

The script writes enriched data containing fields like:

- `fact_count`
- `fact_area`
- Optional derived metrics depending on the input structure

This file becomes the input to `recall_diagram.py`.

---

## `recall_diagram.py`

### Responsibilities

- Loads the cleaned dataset produced by `count_facts.py`
- Groups data by fact category (e.g., “Geografie”, “Demografie”, “Rechtliches”, etc.)
- Computes recall metrics for each category
- Plots category-level recall curves

### Generated Diagrams

The script produces two figures:

1. **Antwort-Recall nach Faktenbereich**
2. **Kontext-Recall nach Faktenbereich**

Both are saved automatically and also displayed when the script completes.

---

## Requirements

- Python 3.9+
- pandas
- matplotlib

Install dependencies:

```bash
pip install pandas matplotlib

---

Usage

Count facts:

python count_facts.py <path-to-input-file>

This generates a processed file containing fact counts.

Plot recall diagrams:

python recall_diagram.py

Plots will be created and saved alongside the dataset.

---
Notes
- The fact strings are extracted using regex; ensure your input uses a consistent delimiter format.
- Missing or malformed fact fields are safely ignored or treated as zero-length lists.
- The recall diagrams assume the dataset includes per-row recall information for both Antwort and Kontext.
