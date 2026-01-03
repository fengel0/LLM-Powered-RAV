from typing import Any, Sequence
from graph_view.ratings.calc_ratings import (
    calc_miss_match,
    prf_counts,
    calc_complettnes_strict,
    calc_f1,
    calc_recall,
    calc_precision,
    calc_complettnes,
)
import pandas as pd

from domain.database.validation.model import RatingGeneral

import logging

logger = logging.getLogger(__name__)

# def _source(r: Any) -> str:
# return f"LLM[{getattr(r, 'config_id', 'unknown')}]"


def _rating_row_fast(r: RatingGeneral, dataset: str, sys_config: str) -> dict[str, Any]:
    # Bind attributes to locals to avoid repeated attribute lookups
    comp = r.completeness
    comp_ctx = r.completeness_in_data
    n_ans = r.number_of_facts_in_answer
    n_ctx = r.number_of_facts_in_context
    source = r.source

    # Counts
    tp_a, fp_a, fn_a = prf_counts(comp, n_ans, source)
    tp_c, fp_c, fn_c = prf_counts(comp_ctx, n_ctx, source)

    transferred = calc_miss_match(comp, comp_ctx)

    tp_at, fp_at, fn_at = prf_counts(transferred, n_ans, source)

    recall_answer_transfer = calc_recall(tp_at, fn_at)
    recall_answer = calc_recall(tp_a, fn_a)
    recall_context = calc_recall(tp_c, fn_c)

    precision_answer_transfer = calc_precision(tp_at, fp_at)
    precision_answer = calc_precision(tp_a, fp_a)
    precision_context = calc_precision(tp_c, fp_c)
    precision_context_chunk_based = calc_precision(
        len(r.relevant_chunks), r.number_of_chunks
    )

    f1_answer_transfer = calc_f1(
        prec=precision_answer_transfer, rec=recall_answer_transfer
    )
    f1_answer = calc_f1(prec=precision_answer, rec=recall_answer)
    f1_context = calc_f1(prec=precision_context, rec=recall_context)
    f1_context_chunk_based = calc_f1(precision_context_chunk_based, rec=recall_context)

    completeness_answer = calc_complettnes(comp)
    completeness_context = calc_complettnes(comp_ctx)

    completeness_answer_transfer_strict = calc_complettnes_strict(transferred)
    completeness_answer_strict = calc_complettnes_strict(comp)
    completeness_context_strict = calc_complettnes_strict(comp_ctx)

    # Avoid repeated len()
    elem_count = len(comp)

    # NOTE: keeping your existing (misspelled) keys so this is drop-in compatible.
    return {
        "config_system": sys_config,
        "config_eval": source,
        "dataset": dataset,
        "element_count": elem_count,
        "correctness": r.correctness,
        "recall_answer": recall_answer,
        "recall_answer_transfer": recall_answer_transfer,
        "recall_context": recall_context,
        "percision_answer": precision_answer,
        "percision_answer_transfer": precision_answer_transfer,
        "percision_context": precision_context,
        "percision_context_chunk_based": precision_context_chunk_based,
        "f1_answer": f1_answer,
        "f1_answer_transfer": f1_answer_transfer,
        "f1_context": f1_context,
        "f1_context_chunk_based": f1_context_chunk_based,
        "completeness_answer": completeness_answer,
        "completeness_context": completeness_context,
        "completeness_strict_answer": completeness_answer_strict,
        "completeness_strict_answer_transfer": completeness_answer_transfer_strict,
        "completeness_strict_context": completeness_context_strict,
    }


def ratings_df(
    ratings: Sequence[RatingGeneral], dataset: str, sys_config: str
) -> pd.DataFrame:
    cols: dict[str, list[Any]] = {
        "config_system": [],
        "config_eval": [],
        "dataset": [],
        "element_count": [],
        "correctness": [],
        "recall_answer": [],
        "recall_answer_transfer": [],
        "recall_context": [],
        "percision_answer": [],
        "percision_answer_transfer": [],
        "percision_context": [],
        "percision_context_chunk_based": [],
        "f1_answer": [],
        "f1_answer_transfer": [],
        "f1_context": [],
        "f1_context_chunk_based": [],
        "completeness_answer": [],
        "completeness_context": [],
        "completeness_strict_answer": [],
        "completeness_strict_answer_transfer": [],
        "completeness_strict_context": [],
    }

    append = {k: cols[k].append for k in cols}  # localize appends to reduce lookups

    for r in ratings:
        row = _rating_row_fast(r, dataset=dataset, sys_config=sys_config)
        for k, v in row.items():
            append[k](v)

    return pd.DataFrame(cols)
