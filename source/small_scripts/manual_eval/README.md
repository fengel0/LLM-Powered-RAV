# True Recall Evaluation and LLM Judge Comparison  
Analysis Toolkit for the FH Erfurt Dataset

This project contains a small collection of scripts to compute true recall from ground-truth completeness annotations and to compare LLM-based judges against human correctness labels on the FH Erfurt dataset.

## Purpose

The codebase supports two main goals:

1. **Calculate true recall**  
Using completeness annotations of the form `[T, F, T, ...]`, the project computes how many items were truly retrieved by a system.
2. **Compare LLM judges with golden labels**  
The project analyzes mismatches between an LLM judge’s correctness decisions and human-provided ground truth.

---

## Repository Structure

### `call_true_recall.py`
Computes true recall percentages from a CSV file.

- Loads `true_recall.csv`
- Parses the `commplettness` field, which contains lists like `[T, F, T]`
- Converts this into a numeric percentage of retrieved items
- Appends a new column `t_percent` to the DataFrame
- Writes the enriched dataset back to disk

This script provides the *ground truth recall* that all further evaluation uses.

---

### `main.py`
Coordinates the evaluation pipeline.

- Loads input rating or correctness datasets
- Merges or filters data as needed
- Produces evaluation summaries comparing:
  - LLM judge correctness  
  - Human correctness labels  
  - True recall values  
- Outputs CSV files containing aligned evaluation rows

This script is intended to be the main entry point for running the comparison.

---

### `test.py`
Diagnostic tool for identifying inconsistent judge behavior.

- Loads `judge_vs_golden_blocks_with_correctness.csv`
- Filters rows where:
  - The selected LLM judge ID matches a given UUID
  - Both judge and human correctness fields should contain valid values
  - But at least one of them is outside the expected `{0, 1}` range
- Prints out all “weird” cases for manual inspection

This is useful for debugging corrupted or unexpected correctness outputs.

---

## Input Files

You should provide the following CSVs in the working directory:

- `true_recall.csv`  
  Must contain `commplettness` field, representing lists of `T`/`F` markers.

- `judge_vs_golden_blocks_with_correctness.csv`  
  Must contain:
  - `correctness_judge`
  - `correctness_ich`
  - `judge`
  - `has_both_correctness`

---

## Output Files

Depending on the script:

- `true_recall_enriched.csv` (or similar) with `t_percent`
- Diagnostic output highlighting mismatches
- Final merged evaluation tables comparing:
  - LLM judge accuracy
  - Human correctness  
  - True recall levels

---

## Requirements

- Python 3.9+
- pandas

Install:

```bash
pip install pandas
