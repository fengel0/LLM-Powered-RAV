import pandas as pd
import re

df = pd.read_csv("./manual_eval_with_correctness.csv")


def normalize(c):
    if pd.isna(c):
        return []
    c = c.replace("{", "[").replace("}", "]").lower()
    values = re.findall(r"[tf]", c)
    return [v.upper() for v in values]


df["completeness_list"] = df["commplettness"].apply(normalize)

gt = df[df["judge"] == "ich"]
others = df[df["judge"] != "ich"]

records = []
TOLERANCE = 0.00

for _, row in others.iterrows():
    gt_row = gt[
        (gt["question id"] == row["question id"])
        & (gt["system id"] == row["system id"])
        & (gt["type"] == row["type"])
    ].iloc[0]

    comp_j = row["completeness_list"]
    comp_gt = gt_row["completeness_list"]

    total = min(len(comp_gt), len(comp_j))
    matches = sum(a == b for a, b in zip(comp_gt, comp_j))
    mismatches = total - matches
    t_to_f = sum(a == "T" and b == "F" for a, b in zip(comp_gt, comp_j))
    f_to_t = sum(a == "F" and b == "T" for a, b in zip(comp_gt, comp_j))

    corr_j = row["correctness"]
    corr_gt = gt_row["correctness"]
    has_correctness = not pd.isna(corr_j) and not pd.isna(corr_gt)
    correctness_match = 0
    judge_higher = 0
    judge_lower = 0

    if has_correctness:
        diff = corr_j - corr_gt
        if abs(diff) <= TOLERANCE:
            correctness_match = 1
        elif diff > TOLERANCE:
            judge_higher = 1
        elif diff < -TOLERANCE:
            judge_lower = 1

    records.append(
        {
            "type": row["type"],
            "judge": row["judge"],
            "question id": row["question id"],
            "system id": row["system id"],
            "vector_blocks": total,
            "total_matches": matches,
            "total_mismatches": mismatches,
            "total_t_to_f": t_to_f,
            "total_f_to_t": f_to_t,
            "blocks_with_correctness": int(has_correctness),
            "correctness_agreements": correctness_match,
            "judge_1_ich_0": judge_higher,
            "judge_0_ich_1": judge_lower,
        }
    )

df_comp = pd.DataFrame(records)
df_comp.to_csv("./judge_vs_golden_blocks_with_correctness.csv")

# --- Aggregate ---
summary = df_comp.groupby(["type", "judge"], as_index=False).agg(
    {
        "vector_blocks": "sum",
        "total_matches": "sum",
        "total_mismatches": "sum",
        "total_t_to_f": "sum",
        "total_f_to_t": "sum",
        "blocks_with_correctness": "sum",
        "correctness_agreements": "sum",
        "judge_1_ich_0": "sum",
        "judge_0_ich_1": "sum",
    }
)

# Add a question-level count
summary["question_blocks"] = (
    df_comp.groupby(["type", "judge"])["question id"].nunique().values
)

summary["overall_accuracy_vectors"] = (
    summary["total_matches"] / summary["vector_blocks"]
)
summary["correctness_agreement_rate"] = (
    summary["correctness_agreements"] / summary["blocks_with_correctness"]
)

print(summary.to_string(index=False))
summary.to_csv("./summary_by_type_and_judge_with_correctness.csv")
