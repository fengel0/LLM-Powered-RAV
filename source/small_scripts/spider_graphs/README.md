# Metric Group Visualization  
Generate Bar Charts (and Optional Spider Charts) for Judge-Level Metrics

This project loads grouped evaluation metrics for multiple datasets and produces visual summaries per judge. It is intended to analyze model or system performance across different domains such as *fachhochschule_erfurt*, *medizinischer*, *novel*, and *weimar*.

The script currently outputs per-judge bar plots and supports generating spider/radar plots as well.

---

## Features

- Load metric groups for each dataset from a shared directory structure.
- Produce per-judge bar charts showing the metric distribution.
- (Optional) Generate spider/radar charts for the same metrics.
- Save every figure automatically into the dataset's output folder.

---

## Directory Structure

The script expects:

prod/
metric_groups_by_dataset/
fachhochschule_erfurt/
.csv
medizinischer/
.csv
novel/
.csv
weimar/
.csv

Each `<judge>.csv` must contain:

- Metric names  
- Metric values  
- One row per metric  

---

## Script Overview

### `main.py`

- Defines the dataset list:  
  `["fachhochschule_erfurt", "medizinischer", "novel", "weimar"]`
- For each dataset:
  - Builds the dataset path
  - Calls `create_barchart(path)` to produce judge-level bar plots
  - (Optional) `create_spider(path)` can be enabled to generate radar charts instead

### `create_barchart(path)`
- Reads all metric CSV files inside the dataset directory.
- Groups metrics per judge.
- Creates a bar chart per judge.
- Saves each figure as:

barchart_.png

### `create_spider(path)`  
(Currently commented out, but available in code)
- Builds radar charts for the same metrics.

---

## Requirements

- Python 3.9+
- pandas  
- numpy  
- matplotlib

Install dependencies:

```bash
pip install pandas numpy matplotlib

---

Usage

Run the full visualization pipeline:

python main.py

All generated figures will be written to:

prod/metric_groups_by_dataset/<dataset_name>/

---

Output

For each judge in each dataset:
- barchart_<judge>.png
- (Optional) spider_<judge>.png if the function is enabled

These images provide a quick visual comparison of metric dimensions such as correctness, recall, precision, coverage, completeness, and any custom metrics present in the input CSVs.

Notes
- The script assumes all metric files in each dataset directory belong to a judge.
- No preprocessing is done on metrics; values are plotted as-is.
- Spider charts require the metric order to be consistent across judges.

If you’ve got yet another mystery project queued up, drop the files, not just the dramatic “next project.” |oai:code-citation|
