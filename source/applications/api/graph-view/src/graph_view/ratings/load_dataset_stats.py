from __future__ import annotations

import logging
from typing import List, Tuple, Optional

from domain.database.validation.model import TestSample
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.figure import Figure

from evaluation_service.usecase.evaluation import EvaluationServiceUsecases

logger = logging.getLogger(__name__)


async def load_dataset_sets(
    dataset_name: str, metadata_attribute: str, metadata_value: str
) -> Tuple[Optional[Figure], str]:
    """
    Load dataset and plot a simple bar chart:
    mean number of expected_facts per question_type.
    """
    result = await EvaluationServiceUsecases.Instance().fetch_dataset_question_number(
        dataset_id=dataset_name
    )
    if result.is_error():
        err_msg = str(result.get_error())
        logger.error(err_msg)
        return None, err_msg

    n_questions: int = result.get_ok()

    result = await EvaluationServiceUsecases.Instance().fetch_dataset_question(
        dataset_id=dataset_name,
        from_number=0,
        to_number=n_questions,
    )
    if result.is_error():
        err_msg = str(result.get_error())
        logger.error(err_msg)
        return None, err_msg

    questions: List[TestSample] = result.get_ok()
    if not questions:
        return None, "Dataset returned no questions."
    if metadata_attribute and metadata_value:
        questions = [
            question
            for question in questions
            if metadata_attribute in question.metatdata.keys()
            and question.metatdata[metadata_attribute] == metadata_value
        ]

    df = pd.DataFrame(
        {
            "question_type": [q.question_type or "Unknown" for q in questions],
            "facts_count": [len(q.expected_facts or []) for q in questions],
        }
    )

    fig: Figure = plt.figure(figsize=(10, 6))
    ax = fig.add_subplot(1, 1, 1)

    for q_type, group in df.groupby("question_type"):
        ax.hist(
            group["facts_count"],
            bins=range(0, max(df["facts_count"]) + 2),
            alpha=0.6,
            label=q_type,
            edgecolor="black",
        )

    ax.set_title("Distribution of # Expected Facts by Question Type")
    ax.set_xlabel("# of Expected Facts")
    ax.set_ylabel("# of Questions")
    ax.legend(title="Question Type")
    ax.grid(axis="y", linestyle="--", alpha=0.4)

    fig.tight_layout()
    return fig, ""
