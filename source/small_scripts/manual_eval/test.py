import pandas as pd

df = pd.read_csv("judge_vs_golden_blocks_with_correctness.csv")

weird = df[
    (df["judge"] == "646d03ca-e231-4776-a823-cffb65da179a")
    & (df["has_both_correctness"])
    & ((~df["correctness_judge"].isin([0, 1])) | (~df["correctness_ich"].isin([0, 1])))
][["question_id", "system_id", "correctness_judge", "correctness_ich"]]

print(weird)
