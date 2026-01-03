# Prefect Deployment Run Time Extractor

This project provides a utility script for fetching flow-run metadata from multiple Prefect deployments, exporting the results to CSV, and generating a summary report of execution statistics.

## Features

- Retrieves all flow runs for a given Prefect deployment using the Prefect Cloud/Server API.
- Handles pagination automatically.
- Extracts start and end timestamps for each run.
- Computes run-time durations.
- Saves raw run data to per-deployment CSV files.
- Uses pandas to calculate summary statistics:
  - Average duration
  - Median duration
  - Minimum and maximum durations
  - Failed and successful run counts
- Produces a consolidated `deployment_summary.csv` across all specified deployments.

## File Overview

`prefect_times.py` contains:

- **`list_flow_run_times`**  
  Asynchronously retrieves all flow runs for a deployment.

- **`write_to_csv`**  
  Saves run-time records to a CSV file.

- **`compute_stats_with_pandas`**  
  Reads a deployment’s CSV file and computes execution statistics.

- **Main execution block**  
  Iterates through configured deployment IDs, generates individual CSVs, computes statistics, and writes a final summary CSV.

## Requirements

- Python 3.9+
- Prefect 2.x
- pandas

## Installation

```bash
pip install prefect pandas

Usage
	1.	Edit DEPLOYMENT_IDS in the script to include the deployment IDs you want to analyze.
	2.	Run the script:

python prefect_times.py

3. Output files:
- <deployment_id>.csv containing raw run data
- deployment_summary.csv containing aggregated statistics

Output Example

deployment_summary.csv includes one row per deployment with calculated metrics such as:

deployment_id	avg_duration	median_duration	min_duration	max_duration	success_count	failed_count


Notes
- Durations are computed in seconds unless modified.
- Only runs with both start_time and end_time are included.
