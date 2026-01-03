# Rating Analysis Toolkit

This project provides a modular pipeline for loading rating data, filtering and transforming it, computing statistical summaries, and generating plots and CSV outputs. It is designed for evaluating system configurations across multiple datasets using a consistent workflow.

## Overview

The codebase is organized into several focused modules:

**`main.py`**  
Entry point for running the full analysis pipeline:
- Loads ratings
- Filters by dataset and evaluation configuration
- Computes rating results
- Generates boxplots for each evaluation configuration and dataset
- Saves figures and CSV summaries

**`constants.py`**  
Central location for:
- Dataset identifiers  
- Evaluation configuration IDs  
- System configuration IDs  
- File paths and directory names  
- Display name mappings for plots and CSV output

**`utile.py`**  
Utility functions shared across the codebase, such as:
- Data loading helpers  
- File/JSON reading  
- Miscellaneous small operations used by other modules

**`filter.py`**  
Functions for filtering rating data, including:
- Selecting ratings for a given dataset  
- Extracting ratings for a specific evaluation configuration  
- Mapping datasets and systems to IDs

**`dataframe_handler.py`**  
Transformations and helpers for constructing pandas DataFrames:
- Creating unified rating result tables  
- Formatting data for plotting and exporting  
- Normalizing and reshaping rating arrays

**`calc_ratings.py`**  
Core logic for calculating rating statistics:
- Aggregating individual ratings  
- Computing mean values  
- Bootstrap confidence intervals (percentile bootstrap)  
- Producing structured numeric outputs for plotting and CSV writing

**`plot.py`**  
Plotting logic using matplotlib:
- Building boxplots for system performance  
- Styling and label formatting  
- Saving plots to files via `save_figure`

**`save_csv.py`**  
Responsible for exporting CSV files with:
- Raw ratings  
- Aggregated statistics  
- Per-dataset and per-evaluation summaries

## Features

- Load rating data and map systems/datasets to consistent IDs
- Filter any combination of dataset or evaluation configuration
- Compute:
  - Mean values
  - Bootstrap confidence intervals
  - Aggregated comparison tables
- Generate publication-ready boxplots
- Save both visualizations and CSV summaries
- Fully modular design: each part can be reused independently

## Requirements

- Python 3.9+
- pandas  
- numpy  
- matplotlib  
- pydantic

Install dependencies:

```bash
pip install pandas pydantic numpy matplotlib

Usage

Run the full analysis pipeline:

python main.py

This will:
1.	Load and filter all configured datasets
2.	Compute statistics for each evaluation configuration
3.	Generate boxplots
4.	Save figures and CSV outputs to the directories specified in constants.py

Output
The pipeline produces:
- Boxplots
One per evaluation configuration and dataset
- CSV files
- Raw rating data
- Aggregated statistics with confidence intervals
- Summaries for each system configuration

Customization

Modify constants.py to:
- Add or rename datasets
- Add new evaluation configurations
- Change input file paths
- Override display labels for plots or CSV files

The pipeline automatically adapts to these mappings.
