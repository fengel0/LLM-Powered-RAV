from pydantic import BaseModel, Field
import pandas as pd

from calc_ratings import bootstrap_mean_ci
from utile import (
    compare_bool_lists_most_agree,
    parse_pg_bool_array,
    compare_bool_lists_all_agree,
)


class RatingGeneral(BaseModel):
    question_id: str
    eval_config_id: str
    system_config_id: str
    correctness: float = Field(ge=0, le=1)
    completeness: list[bool] = Field([])
    completeness_in_data: list[bool] = Field([])
    number_of_facts_in_context: int
    number_of_facts_in_answer: int


def load_questions(path: str) -> dict[str, str]:
    df = pd.read_csv(path, sep=";")
    return dict(zip(df["id"], df["dataset_id"]))  # type: ignore


def load_eval_config(path: str) -> pd.DataFrame:
    return pd.read_csv(path, sep=";")


def load_ratings(path: str) -> pd.DataFrame:
    return pd.read_csv(path, sep=";")


def filter_by_system(
    eval: pd.DataFrame,
    system_config_to_consider: str,
) -> pd.DataFrame:
    # Map question_id → dataset_id
    filtered = eval[eval["config_id.1"] == system_config_to_consider]
    print(f"size after config filter {len(filtered)}")

    return filtered  # type: ignore


def filter_by_dataset(
    eval: pd.DataFrame,
    dataset_map: dict[str, str],
    dataset: str,
) -> pd.DataFrame:
    # Map question_id → dataset_id
    print(eval.columns)
    eval["dataset_id"] = eval["test_sample_id"].map(dataset_map)  # type: ignore
    filtered = eval[eval["dataset_id"] == dataset]

    return filtered  # type: ignore


def build_array(
    eval: pd.DataFrame,
) -> list[RatingGeneral]:
    ratings: list[RatingGeneral] = []

    for _, row in eval.iterrows():
        rating = RatingGeneral(
            question_id=str(row["test_sample_id"]),
            eval_config_id=str(row["config_id"]),
            system_config_id=str(row["config_id.1"]),
            correctness=float(row["correctness"]),
            completeness=parse_pg_bool_array(row["completeness"]),  # type:ignore
            completeness_in_data=parse_pg_bool_array(row["completeness_in_data"]),  # type: ignore
            number_of_facts_in_context=int(row["number_of_facts_in_context"]),
            number_of_facts_in_answer=int(row["number_of_facts_in_answer"]),
        )
        ratings.append(rating)

    return ratings


def build_most_agree(
    ratings: list[RatingGeneral], system_config_id: str
) -> list[RatingGeneral]:
    per_question: dict[str, list[RatingGeneral]] = {}
    combined: list[RatingGeneral] = []

    for rating in ratings:
        per_question.setdefault(rating.question_id, []).append(rating)

    for qid, ratings in per_question.items():
        n = len(ratings)
        if n == 0:
            continue

        # ECHTE binäre Mehrheitsabstimmung (Gleichstand -> 0)
        votes_1 = sum(1 for r in ratings if int(r.correctness) == 1)
        majority_correct = 1 if votes_1 > n / 2 else 0

        # Elementweise Mehrheit mit deinen asserts
        comp_majority = compare_bool_lists_most_agree([r.completeness for r in ratings])
        comp_in_data_majority = compare_bool_lists_most_agree(
            [r.completeness_in_data for r in ratings]
        )

        # getrennte Mittelwerte; Bug fix (nicht überschreiben)
        avg_facts_answer = int(
            round(sum(r.number_of_facts_in_answer for r in ratings) / n)
        )
        avg_facts_context = int(
            round(sum(r.number_of_facts_in_context for r in ratings) / n)
        )

        combined.append(
            RatingGeneral(
                question_id=qid,
                eval_config_id="most-agree",
                system_config_id=system_config_id,
                correctness=majority_correct,
                completeness=comp_majority,
                completeness_in_data=comp_in_data_majority,
                number_of_facts_in_answer=avg_facts_answer,
                number_of_facts_in_context=avg_facts_context,
            )
        )

    return combined


def filter_by_eval_config(
    ratings: list[RatingGeneral], eval_config_id: str
) -> list[RatingGeneral]:
    return [r for r in ratings if r.eval_config_id == eval_config_id]


def build_all_agree(
    ratings: list[RatingGeneral], system_config: str
) -> list[RatingGeneral]:
    per_question: dict[str, list[RatingGeneral]] = {}
    combined: list[RatingGeneral] = []

    for rating in ratings:
        per_question.setdefault(rating.question_id, []).append(rating)

    for qid, ratings in per_question.items():
        n = len(ratings)
        if n == 0:
            continue

        # ECHTE binäre Mehrheitsabstimmung (Gleichstand -> 0)
        votes_1 = sum(1 for r in ratings if int(r.correctness) == 1)
        majority_correct = 1 if votes_1 == n else 0

        # Elementweise Mehrheit mit deinen asserts
        comp_majority = compare_bool_lists_all_agree([r.completeness for r in ratings])
        comp_in_data_majority = compare_bool_lists_all_agree(
            [r.completeness_in_data for r in ratings]
        )

        # getrennte Mittelwerte; Bug fix (nicht überschreiben)
        avg_facts_answer = int(
            round(sum(r.number_of_facts_in_answer for r in ratings) / n)
        )
        avg_facts_context = int(
            round(sum(r.number_of_facts_in_context for r in ratings) / n)
        )

        combined.append(
            RatingGeneral(
                question_id=qid,
                eval_config_id="all-agree",
                system_config_id=system_config,
                correctness=majority_correct,
                completeness=comp_majority,
                completeness_in_data=comp_in_data_majority,
                number_of_facts_in_answer=avg_facts_answer,
                number_of_facts_in_context=avg_facts_context,
            )
        )

    return combined


def prepare_summary(
    df: pd.DataFrame,
) -> pd.DataFrame:
    # --- kleine Helfer nur für diese Funktion ---

    def _add_recall_cis(df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
        recall_cols = [
            "recall_answer",
            "recall_answer_transfer",
            "recall_context",
            "percision_answer",
            "percision_answer_transfer",
            "percision_context",
            "completeness_strict_answer",
            "completeness_strict_answer_transfer",
            "completeness_strict_context",
        ]
        rows: list[dict] = []
        for keys, df_g in df.groupby(group_cols, dropna=False):
            if not isinstance(keys, tuple):
                keys = (keys,)
            row = {col: keys[i] for i, col in enumerate(group_cols)}
            for col in recall_cols:
                # Mittelwert NICHT in row schreiben – den hat df_grouped_means schon
                lo, hi = bootstrap_mean_ci(df_g[col].tolist(), alpha=0.05)
                row[f"{col}_ci_low"] = lo
                row[f"{col}_ci_high"] = hi
            rows.append(row)
        return pd.DataFrame(rows)

    # --- Originalcode ---
    metric_cols: list[str] = [
        "config_system",
        "config_eval",
        "dataset",
        "correctness",
        "element_count",
        "recall_answer",
        "recall_answer_transfer",
        "recall_context",
        "percision_answer",
        "percision_answer_transfer",
        "percision_context",
        "f1_answer",
        "f1_answer_transfer",
        "f1_context",
        "completeness_answer",
        "completeness_context",
        "completeness_strict_answer",
        "completeness_strict_answer_transfer",
        "completeness_strict_context",
    ]

    # Define grouping columns
    group_cols = ["config_system", "config_eval", "dataset"]

    # Define numeric columns for mean calculation (excluding grouping columns)
    numeric_cols = [col for col in metric_cols if col not in group_cols]
    df_grouped_means = df.groupby(group_cols)[numeric_cols].mean().reset_index()  # type: ignore

    # --- NEU: CIs für die drei Recall-Spalten hinzufügen ---
    df_recall_cis = _add_recall_cis(df, group_cols)
    df_grouped_with_ci = df_grouped_means.merge(
        df_recall_cis, on=group_cols, how="left"
    )
    return df_grouped_with_ci
