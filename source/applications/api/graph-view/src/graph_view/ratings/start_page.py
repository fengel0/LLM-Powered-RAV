from __future__ import annotations
import logging
from typing import Any

import pandas as pd

import gradio as gr

from config_service.usecase.config_eval import ConfigServiceUsecases
from evaluation_service.usecase.evaluation import EvaluationServiceUsecases

logger = logging.getLogger(__name__)


async def load_metadata_attributes(dataset_id: str):
    eval_uc = EvaluationServiceUsecases.Instance()
    result = await eval_uc.fetch_metadata_attributes(
        dataset_id=dataset_id,
    )
    if result.is_error():
        return (
            gr.Accordion(visible=False),
            gr.update(
                choices=[],
                value="",
            ),
            str(result.get_error()),
        )

    metadata_attributes = result.get_ok()
    return (
        gr.Accordion(visible=True),
        gr.update(
            choices=metadata_attributes,
            value=metadata_attributes[0] if metadata_attributes else "",
        ),
        "",
    )


async def load_questions(
    dataset_name: str,
    from_number: int,
    to_number: int,
    metadata_attribute: str,
    metadata_value: str,
):
    eval_uc = EvaluationServiceUsecases.Instance()
    result = await eval_uc.fetch_dataset_question(
        dataset_id=dataset_name,
        from_number=from_number,
        to_number=to_number,
        number_of_facts=0,
    )
    if result.is_error():
        return pd.DataFrame(), result.get_error()
    questions = result.get_ok()

    if metadata_attribute and metadata_value:
        questions = [
            question
            for question in questions
            if metadata_attribute in question.metatdata.keys()
            and question.metatdata[metadata_attribute] == metadata_value
        ]

    df_full = pd.DataFrame(
        {
            "#": [i + from_number for i, _ in enumerate(questions)],
            "id": [question.id for question in questions],
            "Question": [question.question for question in questions],
            "Metadata": [str(question.metatdata) for question in questions],
        }
    )
    return df_full, ""


async def load_question_details(  # type: ignore
    event: gr.SelectData,
    dataframe: dict[str, Any],
) -> tuple:  # type: ignore
    # Extract selected question_id
    question_id = dataframe["id"][event.index[0]]

    eval_uc = EvaluationServiceUsecases.Instance()

    # Fetch answers
    result = await eval_uc.fetch_answers_with_rating(sample_id=question_id)
    if result.is_error():
        return (
            "",
            "",
            "",
            "",
            "",
            str(result.get_error()),
            *[gr.update(visible=False), gr.update(value=""), gr.update(value="")] * 5,
        )

    answers = result.get_ok()

    # Fetch question
    result = await eval_uc.fetch_question(sample_id=question_id)
    if result.is_error():
        return (
            "",
            "",
            "",
            "",
            "",
            str(result.get_error()),
            *[gr.update(visible=False), gr.update(value=""), gr.update(value="")] * 5,
        )

    question_optional = result.get_ok()
    if question_optional is None:
        return (
            "",
            "",
            "",
            "",
            "",
            "Question not found",
            *[gr.update(visible=False), gr.update(value=""), gr.update(value="")] * 5,
        )

    question = question_optional

    # Build UI updates for up to 5 answers
    updates = []
    for i in range(10):
        if i < len(answers):
            a = answers[i]
            updates.append(gr.Accordion(f"{a.config_id}", open=False, visible=True))
            updates.append(gr.Textbox(value=a.answer, lines=10, autofocus=True))
            ratings_summary = f"""
            🔎 Retrieval latency: {a.retrieval_latency_ms:.0f} ms  
            🧠 Generation latency: {a.generation_latency_ms:.0f} ms  
            🤖 LLM ratings: {len(a.llm_ratings)}  
            👤 Human ratings: {len(a.human_ratings)}
            """
            updates.append(gr.Textbox(value=ratings_summary.strip(), autofocus=True))
            config_list: list[str] = []
            rational_list: list[str] = []
            correct_list: list[str] = []
            completness_list: list[str] = []
            in_data_list: list[str] = []

            for llm_rating in a.llm_ratings:
                config_list.append(llm_rating.config_id)
                rational_list.append(llm_rating.rationale)
                correct_list.append(str(llm_rating.correctness))
                completness_list.append(
                    f"{llm_rating.completeness.count(True)}/{len(llm_rating.completeness)}"
                )
                in_data_list.append(
                    f"{llm_rating.completeness_in_data.count(True)}/{len(llm_rating.completeness_in_data)}"
                )

            for llm_rating in a.human_ratings:
                config_list.append(llm_rating.creator)
                rational_list.append(llm_rating.rationale)
                correct_list.append(str(llm_rating.correctness))
                completness_list.append(
                    f"{llm_rating.completeness.count(True)}/{len(llm_rating.completeness)}"
                )
                in_data_list.append(
                    f"{llm_rating.completeness_in_data.count(True)}/{len(llm_rating.completeness_in_data)}"
                )

            df_full = pd.DataFrame(
                {
                    "Config": config_list,
                    "Rationale": rational_list,
                    "Correct": correct_list,
                    "Complete": completness_list,
                    "In Data": in_data_list,
                }
            )
            updates.append(df_full)
        else:
            updates.append(gr.Accordion("", open=False, visible=False))
            updates.append(gr.Textbox())
            updates.append(gr.Textbox(value=""))
            df_full = pd.DataFrame(
                {
                    "Config": [],
                    "Rationale": [],
                    "Correct": [],
                    "Complete": [],
                    "In Data": [],
                }
            )
            updates.append(df_full)

    # Return all fields + updates
    return (
        question.id,
        question.question,
        question.expected_answer,
        "\n".join(question.expected_facts),
        question.expected_context,
        "",
        *updates,
    )


async def load_basic_data():
    eval_uc = EvaluationServiceUsecases.Instance()
    cfg_uc = ConfigServiceUsecases.Instance()

    errors: list[str] = []

    # datasets --------------------------------------------------------------
    datasets = [""]
    res = await eval_uc.fetch_datasets()
    datasets.extend(res.get_ok() if not res.is_error() else [])
    if res.is_error():
        errors.append(f"Datasets: {res.get_error()}")

    # system configs --------------------------------------------------------
    eval_cfgs = [("", "")]
    res = await cfg_uc.get_grading_configs()
    eval_cfgs.extend(res.get_ok() if not res.is_error() else [])
    if res.is_error():
        errors.append(f"System configs: {res.get_error()}")

    system_cfgs = [("", "")]
    res = await cfg_uc.get_system_configs()
    system_cfgs.extend(res.get_ok() if not res.is_error() else [])
    if res.is_error():
        errors.append(f"System configs: {res.get_error()}")

    err_msg = "\n\n".join(errors)
    datasets.sort()
    eval_cfgs.sort()
    system_cfgs.sort()
    return (
        gr.update(choices=datasets, value=datasets[0] if datasets else ""),
        gr.update(choices=eval_cfgs, value=eval_cfgs[0][1] if eval_cfgs else ""),
        gr.update(choices=system_cfgs, value=system_cfgs[0][1] if system_cfgs else ""),
        [dataset for dataset in datasets if dataset],
        [eval_cfg for eval_cfg in eval_cfgs if eval_cfg[1]],
        [system_cfg for system_cfg in system_cfgs if system_cfg[1]],
        err_msg,
    )
