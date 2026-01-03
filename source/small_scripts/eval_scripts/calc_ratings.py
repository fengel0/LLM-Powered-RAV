from math import sqrt
from statistics import NormalDist
from typing import Sequence
import logging
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


def calc_miss_match(
    answer_facts: Sequence[bool], context_facts: Sequence[bool]
) -> list[bool]:
    assert len(answer_facts) == len(context_facts)

    output = [False] * len(answer_facts)

    for i in range(len(answer_facts)):
        output[i] = answer_facts[i] and context_facts[i]
    return output


def prf_counts(
    pred: Sequence[bool], number_of_facts: int, id: str
) -> tuple[int, int, int]:
    """Return (TP, FP, FN) for one question (token level)."""
    gold = [True] * len(pred)
    tp = sum(p and g for p, g in zip(pred, gold))
    # fp = sum(p and not g for p, g in zip(pred, gold))
    fp = number_of_facts - tp
    fn = sum((not p) and g for p, g in zip(pred, gold))
    if fp < 0:
        logger.warning(f"{id} fp {fp} tp {tp} fn {fn} size {len(gold)}")
        fp = 0
    return tp, fp, fn


def calc_recall(tp: int, fn: int) -> float:
    if tp + fn == 0:
        return 0.0
    return float(tp) / (float(fn) + float(tp))


def calc_precision(tp: int, fp: int) -> float:
    if tp + fp == 0:
        return 0.0
    return float(tp) / (float(fp) + float(tp))


def calc_f1(prec: float, rec: float) -> float:
    if prec + rec == 0:
        return 0.0
    return 2 * (prec * rec) / (prec + rec)


def calc_complettnes(values: list[bool]) -> float:
    if len(values) == 0:
        return 0.0
    return sum(values) / len(values)


def calc_complettnes_strict(values: list[bool]) -> float:
    if calc_complettnes(values=values) < 1:
        return 0.0
    return 1.0


def z_mean_interval(
    values: list[int] | list[float], alpha: float = 0.05
) -> tuple[float, float]:
    # Konfidenzintervall für den Mittelwert von Proportionen (0..1)
    vals = [v for v in values if pd.notna(v)]
    n = len(vals)
    if n == 0:
        return (float("nan"), float("nan"))
    mean = sum(vals) / n
    var = sum((v - mean) ** 2 for v in vals) / (n - 1) if n > 1 else 0.0
    se = sqrt(var) / sqrt(n) if n > 0 else float("nan")
    z = NormalDist().inv_cdf(1 - 0.05 / 2.0)
    lo = max(0.0, mean - z * se)
    hi = min(1.0, mean + z * se)
    return lo, hi


def wilson_interval(
    values: list[int] | list[float], alpha: float = 0.05
) -> tuple[float, float]:
    # Erwartet 0/1-Werte; NaNs werden ignoriert.
    vals = [v for v in values if pd.notna(v)]
    n = len(vals)
    if n == 0:
        return float("nan"), float("nan")
    k = sum(vals)  # Anzahl "Erfolge"
    p = k / n
    z = NormalDist().inv_cdf(1 - alpha / 2.0)
    denom = 1.0 + z * z / n
    center = p + z * z / (2 * n)
    half = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    lo = (center - half) / denom
    hi = (center + half) / denom
    # Numerische Stabilität (theoretisch unnötig):
    lo = max(0.0, min(1.0, lo))
    hi = max(0.0, min(1.0, hi))
    return lo, hi


def bootstrap_mean_ci(
    values: list[int] | list[float], alpha: float = 0.05, B: int = 10000, seed: int = 1
) -> tuple[float, float]:
    # Konfidenzintervall für den Mittelwert ohne Verteilungsannahme (Percentile-Bootstrap)
    vals = np.array([v for v in values if pd.notna(v)], dtype=float)
    n = len(vals)
    if n == 0:
        return float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    boots = rng.choice(vals, size=(B, n), replace=True).mean(axis=1)
    lo, hi = np.quantile(boots, [alpha / 2, 1 - alpha / 2])
    # Intervall liegt automatisch in [0,1], daher kein Clipping nötig
    return lo, hi
