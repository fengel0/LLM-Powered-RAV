import asyncio
import csv
import pandas as pd
from prefect import get_client
from prefect.client.schemas.filters import DeploymentFilter, DeploymentFilterId
from prefect.client.schemas.sorting import FlowRunSort


# ----------------------------
# Fetch all flow runs for a given deployment_id (handles pagination)
# ----------------------------
async def list_flow_run_times(deployment_id: str, limit_per_page: int = 200):
    async with get_client() as client:
        offset = 0
        runs_data = []

        deployment_filter = DeploymentFilter(
            id=DeploymentFilterId(any_=[deployment_id])
        )

        while True:
            runs = await client.read_flow_runs(
                deployment_filter=deployment_filter,
                sort=FlowRunSort.START_TIME_DESC,
                limit=limit_per_page,
                offset=offset,
            )

            if not runs:
                break

            for run in runs:
                start = run.start_time
                end = run.end_time
                duration = run.total_run_time.total_seconds()

                runs_data.append(
                    {
                        "flow_run_id": run.id,
                        "deployment_id": deployment_id,
                        "name": run.name,
                        "start_time": start,
                        "end_time": end,
                        "duration": duration,
                        "parameters": run.parameters,
                    }
                )

            offset += limit_per_page

        return runs_data


# ----------------------------
# Write runs to CSV
# ----------------------------
def write_to_csv(all_runs: list, output_file: str):
    if not all_runs:
        print("⚠️ No runs to write.")
        return

    with open(output_file, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "flow_run_id",
                "deployment_id",
                "name",
                "start_time",
                "end_time",
                "duration",
                "parameters",
            ],
        )
        writer.writeheader()
        writer.writerows(all_runs)

    print(f"✅ Wrote {len(all_runs)} runs to {output_file}")


# ----------------------------
# Compute stats using pandas
# ----------------------------
def compute_stats_with_pandas(csv_file: str):
    df = pd.read_csv(csv_file, parse_dates=["start_time", "end_time"])

    # Drop rows without duration
    df = df.dropna(subset=["duration"])

    run_count = len(df)
    mean_duration = df["duration"].mean()
    total_duration = df["duration"].sum()

    # Compute first and last run timestamps
    first_run_start = df["start_time"].min()
    last_run_end = df["end_time"].max()

    # Compute wall-clock span (in hours)
    duration_span = (
        (last_run_end - first_run_start).total_seconds() / 3600
        if pd.notna(first_run_start) and pd.notna(last_run_end)
        else None
    )

    print(f"\n📊 Stats for {csv_file}:")
    print(f"• Runs: {run_count}")
    print(f"• Mean Duration: {mean_duration:.2f} seconds")
    print(f"• Total Duration: {total_duration / 3600:.2f} hours")
    print(f"• First run start: {first_run_start}")
    print(f"• Last run end: {last_run_end}")
    print(f"• Time span (first → last): {duration_span:.2f} hours")

    return {
        "deployment_id": df["deployment_id"].iloc[0] if not df.empty else "unknown",
        "run_count": run_count,
        "mean_duration_seconds": mean_duration,
        "total_duration_seconds": total_duration,
        "total_duration_hours": total_duration / 3600,
        "first_run_start": first_run_start,
        "last_run_end": last_run_end,
        "duration_span_hours": duration_span,
    }


# ----------------------------
# Main
# ----------------------------
if __name__ == "__main__":
    DEPLOYMENT_IDS = [
        "d6b32ad3-8bb4-48c0-a252-d628f2a86bca",
        "dad0fc7b-3220-42ec-82b3-9de07debc79a",
    ]

    summary_rows = []

    for deployment_id in DEPLOYMENT_IDS:
        csv_filename = f"{deployment_id}.csv"

        runs = asyncio.run(list_flow_run_times(deployment_id))
        runs = runs[2:]
        write_to_csv(runs, output_file=csv_filename)

        stats = compute_stats_with_pandas(csv_filename)
        summary_rows.append(stats)

    # Write summary CSV
    summary_df = pd.DataFrame(summary_rows)
    summary_df.to_csv("deployment_summary.csv", index=False)
    print("\n✅ Summary written to deployment_summary.csv")
