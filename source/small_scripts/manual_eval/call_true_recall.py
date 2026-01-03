import pandas as pd
import ast

# Load the CSV file
df = pd.read_csv("true_recall.csv")


# Function to compute percentage of 'T' in the completeness field
def calc_t_percentage(completeness_str):
    values = ast.literal_eval(completeness_str.replace("T", '"T"').replace("F", '"F"'))
    return (values.count("T") / len(values)) * 100 if values else 0


# Compute percentage of T for each row
df["t_percent"] = df["commplettness"].apply(calc_t_percentage)

# === ORIGINAL OUTPUT: Mean % of T per system id and type ===
mean_per_system = (
    df.groupby(["system id", "type"])["t_percent"]
    .mean()
    .reset_index()
    .pivot(index="system id", columns="type", values="t_percent")
)

print("=== Mean % of T values per system id ===")
print(mean_per_system.round(2))
print("\n")

# === NEW OUTPUT: Relative frequency of 100% completeness per system id and type ===
# Total count per system id + type
total_counts = df.groupby(["system id", "type"]).size().reset_index(name="total")

# Count where t_percent == 100
count_100 = (
    df[df["t_percent"] == 100]
    .groupby(["system id", "type"])
    .size()
    .reset_index(name="count_100")
)

# Merge and compute relative percentage
relative_100 = pd.merge(
    total_counts, count_100, on=["system id", "type"], how="left"
).fillna(0)
relative_100["relative_100_percent"] = (
    relative_100["count_100"] / relative_100["total"]
) * 100

relative_100_pivot = relative_100.pivot(
    index="system id", columns="type", values="relative_100_percent"
).fillna(0)

print("=== Relative frequency (%) of 100% completeness per system id ===")
print(relative_100_pivot.round(2))

