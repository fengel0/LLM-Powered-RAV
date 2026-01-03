from matplotlib.figure import Figure
import pandas as pd
import re
import os


def save_figure(fig: Figure, dataset: str, eval_config: str, folder_to_store):
    base_out_by_dataset = f"./{folder_to_store}/metric_groups_by_dataset"
    fig.savefig(
        f"{base_out_by_dataset}/{_slugify(dataset)}/{_slugify(eval_config)}_recall.png",
        dpi=300,
        bbox_inches="tight",
    )


def export_metric_groups(
    evaluation: pd.DataFrame,
    folder_to_store: str,
    eval_config_map: dict[str, str],
    sys_config_map: dict[str, str],
    dataset_map: dict[str, str],
) -> None:
    base_out_by_dataset = f"./{folder_to_store}/metric_groups_by_dataset"
    os.makedirs(base_out_by_dataset, exist_ok=True)

    index_cols = ["config_system", "config_eval"]

    metric_groups: dict[str, list[str]] = {
        "correctness": ["correctness"],
        "recall_ci": [
            "recall_answer_ci_low",
            "recall_answer_ci_high",
            "recall_answer_transfer_ci_low",
            "recall_answer_transfer_ci_high",
            "recall_context_ci_low",
            "recall_context_ci_high",
        ],
        "revall_ci_strict": [
            "completeness_strict_answer_ci_low",
            "completeness_strict_answer_ci_high",
            "completeness_strict_answer_transfer_ci_low",
            "completeness_strict_answer_transfer_ci_high",
            "completeness_strict_context_ci_low",
            "completeness_strict_context_ci_high",
        ],
        "recall": [
            "recall_answer",
            "recall_answer_transfer",
            "recall_context",
        ],
        "precision": [
            "percision_answer",
            "percision_answer_transfer",
            "percision_context",
        ],
        "precision_ci": [
            "percision_answer_ci_low",
            "percision_answer_ci_high",
            "percision_answer_transfer_ci_low",
            "percision_answer_transfer_ci_high",
            "percision_context_ci_low",
            "percision_context_ci_high",
        ],
        "f1": [
            "f1_answer",
            "f1_answer_transfer",
            "f1_context",
        ],
        "completeness_strict": [
            "completeness_strict_answer",
            "completeness_strict_answer_transfer",
            "completeness_strict_context",
        ],
    }

    pretty_headers: dict[str, str] = {
        # Konfiguration / Meta
        "config_system": "RAG-Konfiguration",
        "config_eval": "Judge-Modell",
        "dataset": "Datensatz",
        "element_count": "Anzahl Elemente",
        "correctness": "Richtigkeit",
        # Recall (Mittelwerte)
        "recall_answer": "Antwort-Recall",
        "recall_answer_transfer": "Antwort-Recall (Transfer)",
        "recall_context": "Kontext-Recall",
        # Recall-CIs
        "recall_answer_ci_low": "Antwort-Recall (95 % CI low)",
        "recall_answer_ci_high": "Antwort-Recall (95 % CI high)",
        "recall_answer_transfer_ci_low": "Antwort-Recall (Transfer, 95 % CI low)",
        "recall_answer_transfer_ci_high": "Antwort-Recall (Transfer, 95 % CI high)",
        "recall_context_ci_low": "Kontext-Recall (95 % CI low)",
        "recall_context_ci_high": "Kontext-Recall (95 % CI high)",
        # Precision
        "percision_answer": "Antwort-Precision",
        "percision_answer_transfer": "Antwort-Precision (Transfer)",
        "percision_context": "Kontext-Precision",
        "percision_answer_ci_low": "Antwort-Precision (95 % CI low)",
        "percision_answer_ci_high": "Antwort-Precision (95 % CI high)",
        "percision_answer_transfer_ci_low": "Antwort-Precision (Transfer) (95 % CI low)",
        "percision_answer_transfer_ci_high": "Antwort-Precision (Transfer) (95 % CI high)",
        "percision_context_ci_low": "Antwort-Kontext (95 % CI low)",
        "percision_context_ci_high": "Antwort-Kontext (95 % CI high)",
        # F1
        "f1_answer": "Antwort-F1",
        "f1_answer_transfer": "Antwort-F1 (Transfer)",
        "f1_context": "Kontext-F1",
        # Completeness (Strict)
        "completeness_strict_answer": "Recall (Strict)",
        "completeness_strict_answer_transfer": "Recall (Strict, Transfer)",
        "completeness_strict_context": "Recall (Strict, Kontext)",
        "completeness_strict_answer_ci_low": "Antwort-Recall (Strict) (95 % CI low)",
        "completeness_strict_answer_ci_high": "Antwort-Recall (Strict) (95 % CI high)",
        "completeness_strict_answer_transfer_ci_low": "Antwort-Recall (Strict) (Transfer, 95 % CI low)",
        "completeness_strict_answer_transfer_ci_high": "Antwort-Recall (Strict) (Transfer, 95 % CI high)",
        "completeness_strict_context_ci_low": "Kontext-Recall (Strict) (95 % CI low)",
        "completeness_strict_context_ci_high": "Kontext-Recall (Strict) (95 % CI high)",
    }

    evaluation = evaluation.copy()

    # --- WICHTIG: Alle möglichen Metrikspalten vorab numerisch machen ---
    all_metric_cols = {c for cols in metric_groups.values() for c in cols}
    for c in all_metric_cols:
        if c in evaluation.columns:
            evaluation[c] = pd.to_numeric(evaluation[c], errors="coerce")

    # Optionales Runden NACH der Coercion
    num_cols = evaluation.select_dtypes(include="number").columns
    if len(num_cols) > 0:
        evaluation[num_cols] = evaluation[num_cols].round(2)
    evaluation = evaluation.round(2)

    # Mapping anwenden
    if "dataset" in evaluation.columns:
        evaluation["dataset"] = evaluation["dataset"].map(dataset_map)
    if "config_eval" in evaluation.columns:
        evaluation["config_eval"] = evaluation["config_eval"].map(eval_config_map)
    evaluation["config_system"] = evaluation["config_system"].map(sys_config_map)

    evaluation.to_csv(f"{folder_to_store}/rag_eval_prod_data.csv", index=False)

    def _require(cols: list[str], context: str):
        missing = [c for c in cols if c not in evaluation.columns]
        if missing:
            raise KeyError(f"Missing columns for {context}: {missing}")

    def _pick_sort_metric(df: pd.DataFrame, candidates: list[str]) -> str | None:
        # nimm die erste Kandidaten-Spalte, die nach dem Groupby/Mean noch existiert
        for c in candidates:
            if c in df.columns:
                return c
        return None

    # 2) per-dataset -> **one CSV per dataset per metric group**
    if "dataset" in evaluation.columns:
        datasets = (
            evaluation[["dataset"]]
            .dropna()
            .drop_duplicates()
            .sort_values("dataset")["dataset"]
            .tolist()
        )
    else:
        datasets = []

    for ds in datasets:
        ds_slug = _slugify(str(ds))
        ds_out_dir = os.path.join(base_out_by_dataset, ds_slug)
        os.makedirs(ds_out_dir, exist_ok=True)

        ds_mask = evaluation["dataset"] == ds
        for name, cols in metric_groups.items():
            needed = ["dataset"] + index_cols + cols
            _require(needed, f"'{name}' (per-dataset)")

            df_ds = (
                evaluation.loc[ds_mask, index_cols + cols]
                .groupby(index_cols, as_index=True, dropna=False)
                .mean(numeric_only=True)
                .reset_index()
            )

            sort_metric = _pick_sort_metric(df_ds, cols)
            if sort_metric:
                df_ds = df_ds.sort_values(
                    [index_cols[1], sort_metric], ascending=[True, False]
                )
            else:
                df_ds = df_ds.sort_values([index_cols[1]], ascending=[True])

            df_ds_renamed = df_ds.rename(columns=pretty_headers)
            df_ds_renamed = df_ds_renamed.sort_values("Judge-Modell", ascending=[False])
            out_path = os.path.join(ds_out_dir, f"{name}.csv")
            df_ds_renamed.to_csv(out_path, index=False, float_format="%.2f")


def _slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_") or "dataset"
