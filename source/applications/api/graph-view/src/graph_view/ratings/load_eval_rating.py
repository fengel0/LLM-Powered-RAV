from __future__ import annotations
from typing import Optional
import logging
import pandas as pd
import numpy as np
from pandas import DataFrame

from domain.database.validation.model import RatingGeneral, RatingLLM, RatingUser


from graph_view.ratings.calc_ratings import bootstrap_mean_ci
from graph_view.ratings.fetch_helper import (
    fetch_anwers,
    fetch_ratings_eval_system,
    fetch_ratings_of_answer_system,
    fetch_ratings_of_answer_system_by_system,
    fetch_ratings_of_multiable_systems_all_agree,
    fetch_ratings_of_multiable_systems_most_agree,
)
from typing import Literal, Sequence, Tuple, Any

from matplotlib.figure import Figure

from graph_view.ratings.dataframe_helper import ratings_df
from graph_view.ratings.graph_helper import (
    empty_fig,
    hist_correctness,
    plot_relativ_completeness_answer_to_fact_count,
    plot_relativ_completeness_context_to_fact_count,
    plot_relativ_correctness_to_fact_count,
)

_NUMBER_OF_CORRECTNESS_INTERVALS = 10  # default histogram granularity
logger = logging.getLogger(__name__)


def _prepare_summary_and_plots(
    ratings: Sequence[RatingGeneral],
    dataset: str,
    sys_config: str,
    number_of_correctness_intervals: int = _NUMBER_OF_CORRECTNESS_INTERVALS,
) -> Any:
    # --- kleine Helfer nur für diese Funktion ---

    def _add_recall_cis(df: DataFrame, group_cols: list[str]) -> DataFrame:
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
    df_ratings: DataFrame = ratings_df(ratings, dataset=dataset, sys_config=sys_config)
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
        "percision_context_chunk_based",
        "f1_answer",
        "f1_answer_transfer",
        "f1_context",
        "f1_context_chunk_based",
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
    df_grouped_means = df_ratings.groupby(group_cols)[numeric_cols].mean().reset_index()  # type: ignore

    # --- NEU: CIs für die drei Recall-Spalten hinzufügen ---
    df_recall_cis = _add_recall_cis(df_ratings, group_cols)
    df_grouped_with_ci = df_grouped_means.merge(
        df_recall_cis, on=group_cols, how="left"
    )

    # ── Per-source means / Plots ------------------------------------------------
    # fig_corr = plot_relativ_correctness_to_fact_count(df_ratings)
    # fig_comp_ans = plot_relativ_completeness_answer_to_fact_count(df_ratings)
    # fig_comp_ctx = plot_relativ_completeness_context_to_fact_count(df_ratings)
    # fig_hist = hist_correctness(df_ratings, n_intervals=number_of_correctness_intervals)
    fig = empty_fig("")

    return (
        df_grouped_with_ci,  # <- enthält zusätzlich recall_*_ci_low / recall_*_ci_high
        fig,
        fig,
        fig,
        fig,
        # fig_corr,
        # fig_comp_ans,
        # fig_comp_ctx,
        # fig_hist,
    )


# ────────────────────────────────────────────────────────────────────────────
# Shared template & public wrappers (signatures unchanged)
# ────────────────────────────────────────────────────────────────────────────


async def _calc_ratings_template(
    fetch_fn: callable[[...], RatingLLM | RatingUser],  # type: ignore
    *fetch_args,  # type: ignore
    err_title: str = "Error",
    empty_title: str = "No ratings found",
    dataset: str,
    sys_config: str,
) -> Tuple[pd.DataFrame, Figure, Figure, Figure, Figure, str]:
    ratings, err = await fetch_fn(*fetch_args)  # type: ignore
    if err:
        fig = empty_fig(err_title)
        return pd.DataFrame(), fig, fig, fig, fig, err  # type: ignore
    if not ratings:  # type: ignore
        fig = empty_fig(empty_title)
        return pd.DataFrame(), fig, fig, fig, fig, ""  # type: ignore
    figs_and_frames = _prepare_summary_and_plots(
        ratings, dataset=dataset, sys_config=sys_config
    )  # type: ignore
    return *figs_and_frames, ""


async def calc_ratings_eval(
    dataset: str,
    eval_config: str,
    number_of_facts_start: int,
    number_of_facts_end: int,
    metadata_attribute: str,
    metadata_attribute_value: str,
) -> Tuple[pd.DataFrame, Figure, Figure, Figure, Figure, str]:
    """Ratings from *eval* system."""
    return await _calc_ratings_template(
        fetch_ratings_eval_system,
        dataset,
        eval_config,
        number_of_facts_start,
        number_of_facts_end,
        metadata_attribute,
        metadata_attribute_value,
        dataset=dataset,
        sys_config="",
    )


async def calc_ratings_answer_for_eval_systems_all_agree(
    dataset: str,
    system_config: str,
    eval_config: list[str],
    number_of_facts_start: int,
    number_of_facts_end: int,
    metadata_attribute: str,
    metadata_attribute_value: str,
) -> Tuple[pd.DataFrame, Figure, Figure, Figure, Figure, str]:
    """Ratings for an *answer* system evaluated by *another system*."""
    return await _calc_ratings_template(
        fetch_ratings_of_multiable_systems_all_agree,
        dataset,
        system_config,
        eval_config,
        number_of_facts_start,
        number_of_facts_end,
        metadata_attribute,
        metadata_attribute_value,
        dataset=dataset,
        sys_config=system_config,
    )


async def calc_ratings_answer_for_eval_systems_most_agree(
    dataset: str,
    system_config: str,
    eval_config: list[str],
    number_of_facts_start: int,
    number_of_facts_end: int,
    metadata_attribute: str,
    metadata_attribute_value: str,
) -> Tuple[pd.DataFrame, Figure, Figure, Figure, Figure, str]:
    """Ratings for an *answer* system evaluated by *another system*."""
    return await _calc_ratings_template(
        fetch_ratings_of_multiable_systems_most_agree,
        dataset,
        system_config,
        eval_config,
        number_of_facts_start,
        number_of_facts_end,
        metadata_attribute,
        metadata_attribute_value,
        dataset=dataset,
        sys_config=system_config,
    )


async def calc_ratings_answer_system_from_system(
    dataset: str,
    system_config: str,
    eval_config: str,
    number_of_facts_start: int,
    number_of_facts_end: int,
    metadata_attribute: str,
    metadata_attribute_value: str,
) -> Tuple[pd.DataFrame, Figure, Figure, Figure, Figure, str]:
    """Ratings for an *answer* system evaluated by *another system*."""
    return await _calc_ratings_template(
        fetch_ratings_of_answer_system_by_system,
        dataset,
        system_config,
        eval_config,
        number_of_facts_start,
        number_of_facts_end,
        metadata_attribute,
        metadata_attribute_value,
        dataset=dataset,
        sys_config=system_config,
    )


async def calc_ratings_answer_system(
    dataset: str,
    system_config: str,
    number_of_facts: int,
    metadata_attribute: str,
    metadata_attribute_value: str,
) -> Tuple[pd.DataFrame, Figure, Figure, Figure, Figure, str]:
    """Ratings for an *answer* system (human-rated)."""
    return await _calc_ratings_template(
        fetch_ratings_of_answer_system,
        dataset,
        system_config,
        number_of_facts,
        metadata_attribute,
        metadata_attribute_value,
        dataset=dataset,
        sys_config=system_config,
    )


async def build_plot(
    eval_configs: list[tuple[str, str]],
    system_configs: list[tuple[str, str]],
    datasets: list[str],
):
    results: dict[str, dict[str, Figure]] = {}
    for dataset in datasets:
        for eval_config in eval_configs:
            frames: list[DataFrame] = []
            for system_config in system_configs:
                ratings, err = await fetch_ratings_of_answer_system_by_system(
                    dataset=dataset,
                    eval_config=eval_config[1],
                    system_config=system_config[1],
                    number_of_facts_start=0,
                    number_of_facts_end=0,
                    metadata_attribute="",
                    metadata_attribute_value="",
                )

                df_ratings: DataFrame = ratings_df(
                    ratings, dataset=dataset, sys_config=system_config[1]
                )
                frames.append(df_ratings)
                fig_corr = plot_relativ_correctness_to_fact_count(
                    df_ratings, parameter_name="config_system", plot_type="Scatterplot"
                )
                fig_comp_ans = plot_relativ_completeness_answer_to_fact_count(
                    df_ratings, parameter_name="config_system", plot_type="Scatterplot"
                )
                fig_comp_ctx = plot_relativ_completeness_context_to_fact_count(
                    df_ratings, parameter_name="config_system", plot_type="Scatterplot"
                )
                fig_hist = hist_correctness(df_ratings, n_intervals=10)
                results[f"{dataset}-{eval_config[0]}-{system_config[0]}"] = {
                    "fig_corr": fig_corr,
                    "fig_comp_ans": fig_comp_ans,
                    "fig_comp_ctx": fig_comp_ctx,
                    "fig_hist": fig_hist,
                }

            complete_frames = pd.concat(frames, axis=0)

            fig_corr = plot_relativ_correctness_to_fact_count(
                complete_frames, parameter_name="config_system", plot_type="Boxplot"
            )
            fig_comp_ans = plot_relativ_completeness_answer_to_fact_count(
                complete_frames, parameter_name="config_system", plot_type="Boxplot"
            )
            fig_comp_ctx = plot_relativ_completeness_context_to_fact_count(
                complete_frames, parameter_name="config_system", plot_type="Boxplot"
            )
            results[f"{dataset}-{eval_config[0]}"] = {
                "fig_corr": fig_corr,
                "fig_comp_ans": fig_comp_ans,
                "fig_comp_ctx": fig_comp_ctx,
                # "fig_hist": fig_hist,
            }
    return results


async def load_compare_metrics(
    eval_configs: list[tuple[str, str]],
    system_configs: list[tuple[str, str]],
    datasets: list[str],
    number_of_facts_start: int,
    number_of_facts_end: int,
    metadata_attribute: str,
    metadata_attribute_value: str,
) -> Tuple[pd.DataFrame, str]:
    """Ratings for an *answer* system (human-rated)."""
    eval_config_ids = [config[1] for config in eval_configs]
    system_config_ids = [config[1] for config in system_configs]
    return_dataframe = pd.DataFrame(
        columns=[  # type: ignore
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
    )
    for dataset in datasets:
        for index_eval, eval_config in enumerate(eval_config_ids):
            for index_system, system_config in enumerate(system_config_ids):
                result = await calc_ratings_answer_system_from_system(
                    dataset=dataset,
                    system_config=system_config,
                    eval_config=eval_config,
                    number_of_facts_start=number_of_facts_start,
                    number_of_facts_end=number_of_facts_end,
                    metadata_attribute=metadata_attribute,
                    metadata_attribute_value=metadata_attribute_value,
                )
                dataframe = result[0]
                error = result[-1]
                if error:
                    return pd.DataFrame(), error  # Return the actual error message
                dataframe["config_system"] = system_configs[index_system][0]
                dataframe["config_eval"] = eval_configs[index_eval][0]
                dataframe["dataset"] = dataset
                return_dataframe = pd.concat(
                    [return_dataframe, dataframe], ignore_index=True
                )

    return return_dataframe, ""


async def load_eveything(
    eval_configs: list[tuple[str, str]],
    system_configs: list[tuple[str, str]],
    datasets: list[str],
    number_of_facts_start: int,
    number_of_facts_end: int,
    metadata_attribute: str,
    metadata_attribute_value: str,
) -> Tuple[pd.DataFrame, str]:
    """Ratings for an *answer* system (human-rated)."""
    eval_config_ids = [config[1] for config in eval_configs]
    system_config_ids = [config[1] for config in system_configs]
    return_dataframe = pd.DataFrame(
        columns=[  # type: ignore
            "config_system",
            "config_eval",
            "dataset",
            "correctness",
            "element_count",
            "recall_answer",
            "recall_answer_ci_low",
            "recall_answer_ci_high",
            "recall_answer_transfer",
            "recall_answer_transfer_ci_low",
            "recall_answer_transfer_ci_high",
            "recall_context",
            "recall_context_ci_low",
            "recall_context_ci_high",
            "percision_answer",
            "percision_answer_transfer",
            "percision_context",
            "percision_context_chunk_based",
            "f1_answer",
            "f1_answer_transfer",
            "f1_context",
            "f1_context_chunk_based",
            "completeness_answer",
            "completeness_context",
            "completeness_strict_answer",
            "completeness_strict_answer_transfer",
            "completeness_strict_context",
        ]
    )
    for dataset in datasets:
        for index_system, system_config in enumerate(system_config_ids):
            for index_eval, eval_config in enumerate(eval_config_ids):
                result = await calc_ratings_answer_system_from_system(
                    dataset=dataset,
                    system_config=system_config,
                    eval_config=eval_config,
                    number_of_facts_start=number_of_facts_start,
                    number_of_facts_end=number_of_facts_end,
                    metadata_attribute=metadata_attribute,
                    metadata_attribute_value=metadata_attribute_value,
                )
                dataframe = result[0]
                error = result[-1]
                if error:
                    return pd.DataFrame(), error  # Return the actual error message
                dataframe["config_system"] = system_configs[index_system][0]
                dataframe["config_eval"] = eval_configs[index_eval][0]
                dataframe["dataset"] = dataset
                return_dataframe = pd.concat(
                    [return_dataframe, dataframe], ignore_index=True
                )

            result = await calc_ratings_answer_for_eval_systems_most_agree(
                dataset=dataset,
                system_config=system_config,
                eval_config=eval_config_ids,
                number_of_facts_start=number_of_facts_start,
                number_of_facts_end=number_of_facts_end,
                metadata_attribute=metadata_attribute,
                metadata_attribute_value=metadata_attribute_value,
            )

            dataframe = result[0]
            error = result[-1]
            if error:
                return pd.DataFrame(), error  # Return the actual error message
            dataframe["config_system"] = system_configs[index_system][0]
            dataframe["config_eval"] = "most-agree"
            dataframe["dataset"] = dataset
            return_dataframe = pd.concat(
                [return_dataframe, dataframe], ignore_index=True
            )

            result = await calc_ratings_answer_for_eval_systems_all_agree(
                dataset=dataset,
                system_config=system_config,
                eval_config=eval_config_ids,
                number_of_facts_start=number_of_facts_start,
                number_of_facts_end=number_of_facts_end,
                metadata_attribute=metadata_attribute,
                metadata_attribute_value=metadata_attribute_value,
            )

            dataframe = result[0]
            error = result[-1]
            if error:
                return pd.DataFrame(), error  # Return the actual error message
            dataframe["config_system"] = system_configs[index_system][0]
            dataframe["config_eval"] = "all-agree"
            dataframe["dataset"] = dataset
            return_dataframe = pd.concat(
                [return_dataframe, dataframe], ignore_index=True
            )

    return return_dataframe, ""


def calculate_latency_metrics(values: list[float]) -> dict[str, float]:
    """Return mean, median, 75th percentile (up_q), and 25th percentile (lower_q)."""
    if not values:
        return {
            "mean": float("nan"),
            "median": float("nan"),
            "up_q": float("nan"),
            "lower_q": float("nan"),
        }
    arr = np.array(values, dtype=float) / 1000.0

    return {
        "mean": float(np.mean(arr)),
        "median": float(np.median(arr)),
        "up_q": float(np.percentile(arr, 75)),
        "lower_q": float(np.percentile(arr, 25)),
    }


async def load_retrival_times(
    datasets: list[str] | None,
    system_configs: list[tuple[str, str]],
) -> Tuple[pd.DataFrame, str]:
    """Ratings for an *answer* system (human-rated)."""
    return_dataframe = pd.DataFrame(
        columns=[  # type: ignore
            "config_system",
            "retrival_time_mean",
            "retrival_time_median",
            "retrival_time_up_q",
            "retrival_time_lower_q",
            "generation_time_mean",
            "generation_time_median",
            "generation_time_up_q",
            "generation_time_lower_q",
        ]
    )

    if datasets:
        for dataset in datasets:
            for cfg_name, cfg_id in system_configs:
                results, error = await fetch_anwers(
                    dataset=dataset, system_config=cfg_id
                )
                if error:
                    return pd.DataFrame(), error

                retrieval_vals = [a.retrieval_latency_ms for a in results]
                generation_vals = [a.generation_latency_ms for a in results]

                # Skip if both empty
                if not retrieval_vals and not generation_vals:
                    continue

                retrieval_stats = calculate_latency_metrics(retrieval_vals)
                generation_stats = calculate_latency_metrics(generation_vals)

                row = {
                    "config_system": f"{dataset} | {cfg_name}",
                    "retrival_time_mean": retrieval_stats["mean"],
                    "retrival_time_median": retrieval_stats["median"],
                    "retrival_time_up_q": retrieval_stats["up_q"],
                    "retrival_time_lower_q": retrieval_stats["lower_q"],
                    "generation_time_mean": generation_stats["mean"],
                    "generation_time_median": generation_stats["median"],
                    "generation_time_up_q": generation_stats["up_q"],
                    "generation_time_lower_q": generation_stats["lower_q"],
                }

                return_dataframe.loc[len(return_dataframe)] = row
    else:
        for cfg_name, cfg_id in system_configs:
            results, error = await fetch_anwers(dataset=None, system_config=cfg_id)
            if error:
                return pd.DataFrame(), error

            retrieval_vals = [a.retrieval_latency_ms for a in results]
            generation_vals = [a.generation_latency_ms for a in results]

            # Skip if both empty
            if not retrieval_vals and not generation_vals:
                continue

            retrieval_stats = calculate_latency_metrics(retrieval_vals)
            generation_stats = calculate_latency_metrics(generation_vals)

            row = {
                "config_system": f"{cfg_name}",
                "retrival_time_mean": retrieval_stats["mean"],
                "retrival_time_median": retrieval_stats["median"],
                "retrival_time_up_q": retrieval_stats["up_q"],
                "retrival_time_lower_q": retrieval_stats["lower_q"],
                "generation_time_mean": generation_stats["mean"],
                "generation_time_median": generation_stats["median"],
                "generation_time_up_q": generation_stats["up_q"],
                "generation_time_lower_q": generation_stats["lower_q"],
            }

            return_dataframe.loc[len(return_dataframe)] = row

    return return_dataframe, ""
