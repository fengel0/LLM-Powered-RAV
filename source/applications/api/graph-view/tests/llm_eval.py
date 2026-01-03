# tests/test_validation_database_postgres.py
import logging
import os
import re
from typing import Any
from core.result import str_to_bool
import pandas as pd
import unittest


from core.config_loader import ConfigLoaderImplementation
from core.logger import init_logging

from graph_view.application_startup import GraphViewApplication
from graph_view.ratings.load_eval_rating import load_eveything
from config_service.usecase.config_eval import ConfigServiceUsecases

from graph_view.ratings.load_eval_rating import (
    load_retrival_times,
)


datasets_prod = [
    "fachhochschule_erfurt",
]

eval_cfgs_prod = [
    # ("deepkseek", "23559f90-14dd-41eb-8b30-f0c868ea447d"),
    ("gpt", "13824aea-7862-4d9b-b6c7-0ceeee33adbe"),
    # ("llama3.3", "8e8409c8-f2e5-49f4-b098-109cc12ced18"),
]
system_cfgs_prod = [
    # ("hippo-undirected", "2c51406c-4a13-4714-b523-4f5e723422c4"),
    # ("hippo-undirected-r5", "018984d8-db9e-4f21-a7e3-4ba563019c4c"),
    # ("hippo-undirected-rerun", "e93f83eb-d3ad-4211-ab88-fdf955ed0fa3"),
    ("hyp-r20-1024", "4093c138-9266-4ce5-9ee7-ed4b4cc0c13a"),
]


init_logging("info")
logger = logging.getLogger(__name__)


dataset_map = {
    "dragonball": "dragonball",
    "fachhochschule_erfurt": "Fachhochschule Erfurt",
    "graphrag_bench_medical": "Medizinischer",
    "graphrag_bench_novel": "Novel",
    "weimar": "Weimar",
}


def map_dataset(dataset_old: str) -> str:
    assert dataset_map[dataset_old]
    return dataset_map[dataset_old]


def name_from_rules(cfg_row: dict[str, Any]) -> str | None:
    retrieval_type = None
    n_retriebed = None
    chunk_size = None
    cfg_row = cfg_row["data"]
    assert cfg_row["model"]
    model = cfg_row["model"]

    assert cfg_row["retrieval"]
    retrieval_config = cfg_row["retrieval"]

    assert retrieval_config["metadata"]
    assert retrieval_config["strategy"]
    metadata = retrieval_config["metadata"]

    assert metadata["CHUNK_SIZE"]

    if retrieval_config["strategy"] == "kg_traversal":
        assert metadata["QA_TOP_N"]
        assert metadata["PPR_DIRECTED"]
        n_retriebed = metadata["QA_TOP_N"]
        if str_to_bool(str(metadata["PPR_DIRECTED"])):
            retrieval_type = "HipDi"
        else:
            retrieval_type = "HipUn"
    if retrieval_config["strategy"] == "bm25+dense":
        n_retriebed = metadata["TOP_N_COUNT_DENSE"]
        retrieval_type = "Hyp"
    if retrieval_config["strategy"] == "dense_per_subq":
        n_retriebed = metadata["TOP_N_COUNT_DENSE"]
        retrieval_type = "Sub"

    chunk_size = metadata["CHUNK_SIZE"]

    assert chunk_size
    assert n_retriebed
    assert chunk_size

    return f"{retrieval_type}-R{n_retriebed}-{chunk_size}-{model}"


# -------------------------------
# Helpers
# -------------------------------

UUID_RE = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)


def extract_uuid(s: str) -> str | None:
    m = UUID_RE.search(s or "")
    return m.group(0) if m else None


def extract_prefix_without_uuid(s: str) -> str:
    """
    Return the part before the final '-' + UUID, if present.
    e.g. "hybrid-retrieval-bm25+dense-<uuid>" -> "hybrid-retrieval-bm25+dense"
    """
    if not s:
        return ""
    u = extract_uuid(s)
    if not u:
        return s
    # strip trailing "-" + uuid
    if s.endswith(u):
        s2 = s[: -len(u)]
        return s2[:-1] if s2.endswith("-") else s2
    return s


def map_eval_config_system(val: str) -> str:
    uid = extract_uuid(val or "")
    if not uid:
        # no uuid found; keep original
        return val
    cfg_row = config_map.get(uid)
    if not cfg_row:
        # unknown uuid; keep original
        return val
    assert cfg_row["data"]
    cfg_row = cfg_row["data"]
    assert cfg_row["model"]
    return cfg_row["model"]


def export_zeiten(
    evaluation: pd.DataFrame,
    folder_to_store: str,
    system_config_mapping: list[tuple[str, str]],
) -> None:
    # where to save
    base_out = f"./csv/{folder_to_store}/metric_groups"
    base_out_by_dataset = f"./csv/{folder_to_store}/metric_groups_by_dataset"
    os.makedirs(base_out, exist_ok=True)
    os.makedirs(base_out_by_dataset, exist_ok=True)
    num_cols = evaluation.select_dtypes(include="number").columns
    evaluation[num_cols] = (
        evaluation[num_cols].apply(pd.to_numeric, errors="coerce").round(2)
    )
    evaluation = evaluation.round(2)

    evaluation.to_csv(f"./csv/{folder_to_store}/rag_eval_prod_data.csv", index=False)
    index_cols = ["config_system"]

    metric_groups: dict[str, list[str]] = {
        "times": [
            "retrival_time_mean",
            "retrival_time_median",
            "generation_time_mean",
            "generation_time_median",
        ],
    }

    pretty_headers: dict[str, str] = {
        "config_system": "RAG Konfig",
        "retrival_time_mean": "Retrieval Zeit Durchschnitt",
        "retrival_time_median": "Retrieval Zeit Median",
        "generation_time_mean": "Generation Zeit Durchschnitt",
        "generation_time_median": "Generation Zeit Median",
    }
    # use your mapping helpers if present; otherwise identity
    map_fn = lambda fn_name: globals().get(fn_name, lambda x: x)

    evaluation = evaluation.copy()

    def map_config_system(value: str):
        for name, id in system_config_mapping:
            if id in value:
                return name
        return value

    evaluation["config_system"] = (
        evaluation["config_system"].astype(str).map(map_config_system)
    )

    def _require(cols: list[str], context: str):
        missing = [c for c in cols if c not in evaluation.columns]
        if missing:
            raise KeyError(f"Missing columns for {context}: {missing}")

    # 1) overall (all datasets) -> one CSV per metric group
    for name, cols in metric_groups.items():
        needed = index_cols + cols
        _require(needed, f"'{name}' (overall)")
        df_all = (
            evaluation[needed]
            .groupby(index_cols, as_index=True, dropna=False)
            .mean(numeric_only=True)
            .reset_index()
            .sort_values([index_cols[0], cols[0]], ascending=[True, False])
        )
        # rename_map = {c: pretty_headers.get(c, c) for c in cols}
        df_all_renamed = df_all.rename(columns=pretty_headers)
        df_all_renamed.to_csv(
            f"{base_out}/{name}.csv", index=False, float_format="%.2f"
        )


def export_metric_groups(
    evaluation: pd.DataFrame,
    folder_to_store: str,
    system_config_mapping: list[tuple[str, str]],
    eval_config_mapping: list[tuple[str, str]],
) -> None:
    # where to save
    base_out = f"./csv/{folder_to_store}/metric_groups"
    base_out_by_dataset = f"./csv/{folder_to_store}/metric_groups_by_dataset"
    os.makedirs(base_out, exist_ok=True)
    os.makedirs(base_out_by_dataset, exist_ok=True)

    def map_config_eval(value: str):
        for name, id in eval_config_mapping:
            if id in value:
                return name
        return value

    def map_config_system(value: str):
        for name, id in system_config_mapping:
            if id in value:
                return name
        return value

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
            "percision_context_chunk_based",
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
        "percision_context_chunk_based": "Kontext-Chunk-Precision",
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
        "f1_context_chunk_based": "Kontext-Chunk-F1",
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
        evaluation["dataset"] = evaluation["dataset"].astype(str).map(map_dataset)
    if "config_eval" in evaluation.columns:
        evaluation["config_eval"] = (
            evaluation["config_eval"].astype(str).map(map_config_eval)
        )
    evaluation["config_system"] = (
        evaluation["config_system"].astype(str).map(map_config_system)
    )
    evaluation.to_csv(f"./csv/{folder_to_store}/rag_eval_prod_data.csv", index=False)

    def _require(cols: list[str], context: str):
        missing = [c for c in cols if c not in evaluation.columns]
        if missing:
            raise KeyError(f"Missing columns for {context}: {missing}")

    def _slugify(value: str) -> str:
        value = value.strip().lower()
        value = re.sub(r"[^a-z0-9]+", "_", value)
        return value.strip("_") or "dataset"

    def _pick_sort_metric(df: pd.DataFrame, candidates: list[str]) -> str | None:
        # nimm die erste Kandidaten-Spalte, die nach dem Groupby/Mean noch existiert
        for c in candidates:
            if c in df.columns:
                return c
        return None

    # 1) overall (all datasets) -> one CSV per metric group
    for name, cols in metric_groups.items():
        needed = index_cols + cols
        _require(needed, f"'{name}' (overall)")

        df_all = (
            evaluation[needed]
            .groupby(index_cols, as_index=True, dropna=False)
            .mean(numeric_only=True)
            .reset_index()
        )

        sort_metric = _pick_sort_metric(df_all, cols)
        if sort_metric:
            df_all = df_all.sort_values(
                [index_cols[0], sort_metric], ascending=[True, False]
            )
        else:
            # Fallback: nur nach config_system sortieren
            df_all = df_all.sort_values([index_cols[0]], ascending=[True])

        df_all_renamed = df_all.rename(columns=pretty_headers)
        df_all_renamed.to_csv(
            f"{base_out}/{name}.csv", index=False, float_format="%.2f"
        )

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


def filter_config(
    all_models: list[tuple[str, str]], models_to_use: list[tuple[str, str]]
) -> list[tuple[str, str]]:
    ids = [m[1] for m in models_to_use]
    return [model for model in all_models if model[1] in ids]


class TestPostgresSystemConfigDatabase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        GraphViewApplication.create(ConfigLoaderImplementation.create())
        GraphViewApplication.Instance().start()
        await GraphViewApplication.Instance().astart()
        await GraphViewApplication.Instance().create_usecase()

    async def asyncTearDown(self) -> None:
        await GraphViewApplication.Instance().ashutdown()
        GraphViewApplication.Instance().shutdown()
        return await super().asyncTearDown()

    async def tests_load_all_evals(self):
        cfg_uc = ConfigServiceUsecases.Instance()

        system_configs_result = await cfg_uc.get_system_configs()
        if system_configs_result.is_error():
            raise system_configs_result.get_error()
        eval_configs_results = await cfg_uc.get_grading_configs()
        if eval_configs_results.is_error():
            raise eval_configs_results.get_error()

        system_configs = system_configs_result.get_ok()
        eval_configs = eval_configs_results.get_ok()

        system_configs_to_use_prod = filter_config(system_configs, system_cfgs_prod)
        eval_configs_to_use_to_prod = filter_config(eval_configs, eval_cfgs_prod)

        # system_configs_to_use_test = filter_config(system_configs, system_cfgs_test)
        # eval_configs_to_use_to_test = filter_config(eval_configs, eval_cfgs_test)

        # system_configs_to_use_llm_eval = filter_config(system_configs, system_cfgs_llm)
        # eval_configs_to_use_to_llm_eval = filter_config(eval_configs, eval_cfgs_llm)

        # system_configs_to_use_weimer = filter_config(system_configs, system_cfgs_weimar)
        # eval_configs_to_use_to_weimar = filter_config(eval_configs, eval_cfgs_weimar)

        evaluation, err = await load_eveything(
            eval_configs=eval_configs_to_use_to_prod,
            system_configs=system_configs_to_use_prod,
            datasets=datasets_prod,
            number_of_facts_start=0,
            number_of_facts_end=99,
            metadata_attribute="",
            metadata_attribute_value="",
        )
        if err:
            logger.error(err)
            raise Exception(err)

        dataset_llm_prod_times, error = await load_retrival_times(
            datasets=[], system_configs=system_configs_to_use_prod
        )
        if err:
            logger.error(error)
            raise Exception(err)

        export_metric_groups(
            evaluation,
            "prod-rerun-test",
            system_config_mapping=system_cfgs_prod,
            eval_config_mapping=eval_cfgs_prod,
        )
        export_zeiten(
            dataset_llm_prod_times,
            "prod-rerun-test",
            system_config_mapping=system_cfgs_prod,
        )
