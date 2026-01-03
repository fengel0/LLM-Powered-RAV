DATASETS = [
    # "fachhochschule_erfurt",
    # "graphrag_bench_medical",
    # "graphrag_bench_novel",
    "weimar",
]

EVAL_CFGS = [
    ("deepseek-r1:70b", "646d03ca-e231-4776-a823-cffb65da179a"),
    # ("gpt-4o-mini-2024-07-18", "882e3d5b-0c1a-42a9-b595-c6eceef229c8"),
    ("llama3.3:70b", "71a14eeb-8d52-423e-9fc5-34233ba4ef62"),
]

SYSTEM_CFGS = [
    ("HipUn-R5-1024-deepseek-r1:70b", "5046c7b2-0740-4a36-93af-041579f837d4"),
    ("HipDi-R5-1024-deepseek-r1:70b", "ee0ce611-624e-4df0-b344-b27c32f3fa71"),
    ("Hyp-R20-1024-deepseek-r1:70b", "eca5f272-d251-4855-ab4c-8d165290d69c"),
    ("Sub-R5-1024-deepseek-r1:70b", "232c4e11-521d-4657-9502-8f2fc535a565"),
]

DATASET_MAP = {
    "dragonball": "dragonball",
    "fachhochschule_erfurt": "Fachhochschule Erfurt",
    "graphrag_bench_medical": "Medizinischer",
    "graphrag_bench_novel": "Novel",
    "weimar": "Weimar",
}


def get_base_dataframe():
    import pandas as pd

    return pd.DataFrame(
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
