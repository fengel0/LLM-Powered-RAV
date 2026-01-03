import sys
import json
import re
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path


def count_facts(cell):
    """Count number of fact strings inside the expected_facts cell."""
    if pd.isna(cell):
        return 0
    s = str(cell).strip()
    if s == "" or s.lower() in {"nan", "none", "null"}:
        return 0

    # Try proper JSON first
    try:
        parsed = json.loads(s)
        if isinstance(parsed, list):
            return len(parsed)
        if isinstance(parsed, dict):
            # Sometimes facts are keys with dummy values
            return len(parsed.keys())
    except Exception:
        pass

    # If it looks like a brace-delimited set of strings (no colons), coerce to JSON list
    if s.startswith("{") and s.endswith("}") and ":" not in s:
        candidate = "[" + s[1:-1] + "]"
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, list):
                return len(parsed)
        except Exception:
            pass

    # Fallback: count quoted strings
    return len(re.findall(r'"([^"]+)"', s))


def main(csv_path: str):
    p = Path(csv_path)
    if not p.exists():
        print(f"File not found: {p}")
        sys.exit(1)

    # Read CSV (use engine='python' for flexible delimiter inference)
    df = pd.read_csv(p, engine="python", sep=None)

    # Normalize column name if needed
    # Count facts
    df["fact_count"] = df["expected_facts"].apply(count_facts)

    # Define bins and labels (left-closed, right-open: [0,5), [5,10), …)
    bins = [0, 5, 10, 15, 20, 25, 30]
    labels = ["0–5", "5–10", "10–15", "15–20", "20–25", "25–30"]

    cats = pd.cut(
        df["fact_count"], bins=bins, right=False, labels=labels, include_lowest=True
    )
    count_by_bin = cats.value_counts().reindex(labels, fill_value=0)

    # Print summary table
    result_df = pd.DataFrame(
        {
            "Facts per question (bin)": labels,
            "Count of questions": [int(x) for x in count_by_bin.values],
        }
    )
    print(result_df.to_string(index=False))

    # Save summary as CSV next to input (optional)
    out_csv = p.with_suffix(".facts_histogram.csv")
    result_df.to_csv(out_csv, index=False)
    print(f"\nSaved summary table to: {out_csv}")

    # Plot bar chart (no custom colors/styles; single plot)
    plt.figure(figsize=(8, 5))
    plt.bar(result_df["Facts per question (bin)"], result_df["Count of questions"])
    plt.xlabel("Anzahl der Fakten pro Frage")
    plt.ylabel("Anzahl der Fragen")
    plt.title("Verteilung der Fragen nach Anzahl der erwarteten Fakten")
    plt.tight_layout()

    out_png = p.with_suffix(".facts_histogram.png")
    plt.savefig(out_png, dpi=150)
    print(f"Saved chart to: {out_png}")


if __name__ == "__main__":
    main("./questions.csv")
