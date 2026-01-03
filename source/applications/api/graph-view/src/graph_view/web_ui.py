from __future__ import annotations

import gradio as gr

from graph_view.ratings.load_dataset_stats import load_dataset_sets
from graph_view.ratings.start_page import (
    load_basic_data,
    load_questions,
    load_metadata_attributes,
    load_question_details,
)
from graph_view.ratings.load_eval_rating import (
    calc_ratings_answer_system_from_system,
    calc_ratings_eval,
    calc_ratings_answer_system,
    load_eveything,
    load_retrival_times,
)

# ────────────────────────────────────────────────────────────────────────────
# UI builders
# ────────────────────────────────────────────────────────────────────────────


def _build_dataset_tab():
    """Root tab that wires up every other view.

    All other *_build_* helpers are **only** ever called from here so that we
    can thread the dynamically created widgets (``metadata_dd`` &
    ``metadata_value``) through to every child view.  That way each load
    callback can consume the additional filter information without having to
    look it up globally.
    """
    with gr.Tab("Datasets"):
        gr.Markdown("### Select dataset & eval system")
        error_msg = gr.Markdown("", visible=True)
        load_btn = gr.Button("Load Data")
        dataset_dd = gr.Dropdown(
            label="Dataset",
            choices=[],
            interactive=True,
            scale=2,
            allow_custom_value=True,
        )
        eval_dd = gr.Dropdown(
            label="EvalConfig",
            choices=[],
            interactive=True,
            scale=2,
            allow_custom_value=True,
        )
        system_dd = gr.Dropdown(
            label="SystemConfig",
            choices=[],
            interactive=True,
            scale=2,
            allow_custom_value=True,
        )

        eval_choices_state = gr.State([])  # type: ignore
        system_choices_state = gr.State([])  # type: ignore
        dataset_choices_state = gr.State([])  # type: ignore
        # ── Optional filter attributes ────────────────────────────────────
        with gr.Accordion("Addition Filter Attirbutes", visible=False) as filter:
            with gr.Row():
                gr.Markdown(
                    "Range of Facts in Reference Answer to Consider for Evaluation"
                )
                number_of_facts_start = gr.Number(
                    value=0,
                )
                number_of_facts_end = gr.Number(value=99)
                metadata_dd = gr.Dropdown(
                    label="Metadata Attribute",
                    choices=[],
                    interactive=True,
                    scale=2,
                    allow_custom_value=True,
                )
                metadata_value = gr.Textbox(
                    label="Metadata Attribute Value", interactive=True, scale=2
                )

        # ── Wire callbacks for the root view ──────────────────────────────
        load_btn.click(
            fn=load_basic_data,
            outputs=[
                dataset_dd,
                eval_dd,
                system_dd,
                dataset_choices_state,
                eval_choices_state,
                system_choices_state,
                error_msg,
            ],
        )
        dataset_dd.select(
            fn=load_metadata_attributes,
            inputs=[dataset_dd],
            outputs=[filter, metadata_dd],
        )

        # ── Child views – pass the new widgets along ──────────────────────
        _build_dataset_eval_tab(dataset_dd, metadata_dd, metadata_value)
        _build_eval_questions_tab(
            dataset_dd,
            metadata_dd,
            metadata_value,
        )
        _build_eval_ratings_tab(
            dataset_dd,
            eval_dd,
            number_of_facts_start,
            number_of_facts_end,
            metadata_dd,
            metadata_value,
        )
        _build_system_answer_ratings_tab(
            dataset_dd,
            system_dd,
            number_of_facts_start,
            number_of_facts_end,
            metadata_dd,
            metadata_value,
        )
        _build_system_answer_ratings_from_certain_system_tab(
            dataset_dd,
            system_dd,
            eval_dd,
            number_of_facts_start,
            number_of_facts_end,
            metadata_dd,
            metadata_value,
        )
        _build_all_views(
            dataset_choices_state,
            system_choices_state,
            eval_choices_state,
            number_of_facts_start,
            number_of_facts_end,
            metadata_dd,
            metadata_value,
        )
        _build_times_tab(
            dataset_choices_state,
            system_choices_state,
        )


# ────────────────────────────────────────────────────────────────────────────
# Simple dataset‑stats tab
# ────────────────────────────────────────────────────────────────────────────


def _build_dataset_eval_tab(
    dataset_dd: gr.Dropdown, metadata_dd: gr.Dropdown, metadata_value: gr.Textbox
):
    with gr.Tab("Dataset"):
        gr.Markdown("### Dataset")
        load_btn = gr.Button("Load Ratings", variant="primary")
        err_md = gr.Markdown("", visible=False)
        fig_distribution = gr.Plot(label="Distribution of Facts in questions")
        load_btn.click(
            fn=load_dataset_sets,
            inputs=[dataset_dd, metadata_dd, metadata_value],
            outputs=[fig_distribution, err_md],
        )


def _build_times_tab(dataset_dd: gr.State, system_config_dd: gr.State):
    with gr.Tab("Retrival times"):
        gr.Markdown("### Retrival times")
        load_btn = gr.Button("Load Times", variant="primary")
        err_md = gr.Markdown("", visible=False)
        summary_df = gr.Dataframe(
            headers=[
                "config_system",
                "retrival_time_mean",
                "retrival_time_median",
                "retrival_time_up_q",
                "retrival_time_lower_q",
                "generation_time_mean",
                "generation_time_median",
                "generation_time_up_q",
                "generation_time_lower_q",
            ],
            interactive=False,
            wrap=True,
        )
        load_btn.click(
            fn=load_retrival_times,
            inputs=[dataset_dd, system_config_dd],
            outputs=[summary_df, err_md],
        )


# ────────────────────────────────────────────────────────────────────────────
# Tabs that visualise ratings (3 variants)
# ────────────────────────────────────────────────────────────────────────────


def _build_all_views(
    dataset_choices: gr.State,
    system_choices: gr.State,
    eval_choices: gr.State,
    number_of_facts_start: gr.Number,
    number_of_facts_end: gr.Number,
    metadata_dd: gr.Dropdown,
    metadata_value: gr.Textbox,
):
    with gr.Tab("All Data"):
        gr.Markdown("### All Data")
        load_btn = gr.Button("Load Ratings", variant="primary")
        err_md = gr.Markdown("", visible=False)

        summary_df = gr.Dataframe(
            headers=[
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
            ],
            label="Summary (weighted)",
            interactive=False,
            wrap=True,
        )
        # print(eval_dd.choices)
        # print(system_dd.choices)
        # print(dataset_dd.choices)

        load_btn.click(
            fn=load_eveything,
            inputs=[
                eval_choices,  # type: ignore
                system_choices,  # type: ignore
                dataset_choices,  # type: ignore
                number_of_facts_start,
                number_of_facts_end,
                metadata_dd,
                metadata_value,
            ],
            outputs=[summary_df, err_md],
        )


def _build_system_answer_ratings_from_certain_system_tab(
    dataset_dd: gr.Dropdown,
    system_dd: gr.Dropdown,
    eval_dd: gr.Dropdown,
    number_of_facts_start: gr.Number,
    number_of_facts_end: gr.Number,
    metadata_dd: gr.Dropdown,
    metadata_value: gr.Textbox,
):
    with gr.Tab("System Answer Eval form a Certain System"):
        gr.Markdown("### Ratings (System Answer from Certain Eval)")
        load_btn = gr.Button("Load Ratings", variant="primary")
        err_md = gr.Markdown("", visible=False)

        # ── Plots ────────────────────────────────────────────────
        with gr.Row():
            fig_corr = gr.Plot(label="Plot Relativ Correctness to fact count")
            fig_corr_hist = gr.Plot(label="Histogramm of Correctnes")
        with gr.Row():
            fig_comp = gr.Plot(label="Plot Relative Completness to fact count")
            fig_comp_context = gr.Plot(
                label="Plot Relative Completness in Context to fact count"
            )

        # ── Dataframes ───────────────────────────────────────────
        summary_df = gr.Dataframe(
            headers=[
                "config_system",
                "config_eval",
                "dataset",
                "correctness",
                "element_count",
                "recall_answer",
                "recall_context",
                "percision_answer",
                "percision_context",
                "f1_answer",
                "f1_context",
                "completeness_answer",
                "completeness_context",
                "completeness_strict_answer",
                "completeness_strict_context",
            ],
            label="Summary (weighted)",
            interactive=False,
            wrap=True,
        )

        load_btn.click(
            fn=calc_ratings_answer_system_from_system,
            inputs=[
                dataset_dd,
                system_dd,
                eval_dd,
                number_of_facts_start,
                number_of_facts_end,
                metadata_dd,
                metadata_value,
            ],
            outputs=[
                summary_df,
                fig_corr,
                fig_comp,
                fig_comp_context,
                fig_corr_hist,
                err_md,
            ],
        )


def _build_system_answer_ratings_tab(
    dataset_dd: gr.Dropdown,
    system_dd: gr.Dropdown,
    number_of_facts_start: gr.Number,
    number_of_facts_end: gr.Number,
    metadata_dd: gr.Dropdown,
    metadata_value: gr.Textbox,
):
    with gr.Tab("System Answer Eval"):
        gr.Markdown("### Ratings (System Answer Eval)")
        load_btn = gr.Button("Load Ratings", variant="primary")
        err_md = gr.Markdown("", visible=False)

        # ── Plots ────────────────────────────────────────────────
        with gr.Row():
            fig_corr = gr.Plot(label="Plot Relativ Correctness to fact count")
            fig_corr_hist = gr.Plot(label="Histogramm of Correctnes")
        with gr.Row():
            fig_comp = gr.Plot(label="Plot Relative Completness to fact count")
            fig_comp_context = gr.Plot(
                label="Plot Relative Completness in Context to fact count"
            )

        summary_df = gr.Dataframe(
            headers=[
                "config_system",
                "config_eval",
                "dataset",
                "correctness",
                "element_count",
                "recall_answer",
                "recall_context",
                "percision_answer",
                "percision_context",
                "f1_answer",
                "f1_context",
                "completeness_answer",
                "completeness_context",
                "completeness_strict_answer",
                "completeness_strict_context",
            ],
            label="Summary (weighted)",
            interactive=False,
            wrap=True,
        )

        load_btn.click(
            fn=calc_ratings_answer_system,
            inputs=[
                dataset_dd,
                system_dd,
                number_of_facts_start,
                number_of_facts_end,
                metadata_dd,
                metadata_value,
            ],
            outputs=[
                summary_df,
                fig_corr,
                fig_comp,
                fig_comp_context,
                fig_corr_hist,
                err_md,
            ],
        )


def _build_eval_questions_tab(
    dataset_dd: gr.Dropdown,
    metadata_dd: gr.Dropdown,
    metadata_value: gr.Textbox,
):
    with gr.Tab("Questions Dataset"):
        answer_groups: list[
            tuple[gr.Accordion, gr.Textbox, gr.Textbox, gr.Dataframe]
        ] = []
        gr.Markdown("### Questions Dataset")
        load_btn = gr.Button("Load Ratings", variant="primary")
        err_md = gr.Markdown("", visible=False)
        with gr.Row():
            from_number = gr.Number(value=0, label="From")
            to_number = gr.Number(value=10, label="To")

        summary_df = gr.Dataframe(
            headers=[
                "#",
                "id",
                "Question",
                "Metadata",
            ],
            label="Questions in Dataset",
            interactive=False,
            wrap=True,
        )

        with gr.Accordion("Question Details", open=False):
            question_id_display = gr.Textbox(label="ID", interactive=False)
            full_question_display = gr.Textbox(
                label="Full Question", interactive=True, lines=10, autofocus=True
            )
            expected_answer_display = gr.Textbox(
                label="Expected Answer", interactive=True, lines=10, autofocus=True
            )
            expected_facts_display = gr.Textbox(
                label="Expected Facts", interactive=True, lines=10, autofocus=True
            )
            expected_context_display = gr.Textbox(
                label="Expected Context", interactive=True, lines=10, autofocus=True
            )
            with gr.Column():
                for i in range(10):
                    with gr.Accordion(
                        f"Answer {i + 1}", open=False, visible=False
                    ) as grp:
                        answer_text = gr.Textbox(
                            label="Answer", interactive=False, autofocus=True
                        )
                        rating_text = gr.Textbox(
                            label="Rating", interactive=False, autofocus=True
                        )
                        rating_table = gr.Dataframe(
                            headers=[
                                "Config",
                                "Rationale",
                                "Correct",
                                "Complete",
                                "In Data",
                            ],
                            label="Questions in Dataset",
                            interactive=False,
                            wrap=True,
                        )

                        answer_groups.append(
                            (grp, answer_text, rating_text, rating_table)
                        )

        # Handle DataFrame row selection
        summary_df.select(
            fn=load_question_details,
            inputs=[summary_df],
            outputs=[  # type: ignore
                question_id_display,
                full_question_display,
                expected_answer_display,
                expected_facts_display,
                expected_context_display,
                err_md,
                *(item for group in answer_groups for item in group),
            ],
        )

        # Handle Next/Previous button clicks
        load_btn.click(
            fn=load_questions,
            inputs=[
                dataset_dd,
                from_number,
                to_number,
                metadata_dd,
                metadata_value,
            ],
            outputs=[
                summary_df,
                err_md,
            ],
        )


def _build_eval_ratings_tab(
    dataset_dd: gr.Dropdown,
    eval_dd: gr.Dropdown,
    number_of_facts_start: gr.Number,
    number_of_facts_end: gr.Number,
    metadata_dd: gr.Dropdown,
    metadata_value: gr.Textbox,
):
    with gr.Tab("Ratings Eval System"):
        gr.Markdown("### Ratings (Eval System)")
        load_btn = gr.Button("Load Ratings", variant="primary")
        err_md = gr.Markdown("", visible=False)

        with gr.Row():
            fig_corr = gr.Plot(label="Plot Relativ Correctness to fact count")
            fig_corr_hist = gr.Plot(label="Histogramm of Correctnes")
        with gr.Row():
            fig_comp = gr.Plot(label="Plot Relative Completness to fact count")
            fig_comp_context = gr.Plot(
                label="Plot Relative Completness in Context to fact count"
            )

        summary_df = gr.Dataframe(
            headers=[
                "config_system",
                "config_eval",
                "dataset",
                "correctness",
                "element_count",
                "recall_answer",
                "recall_context",
                "percision_answer",
                "percision_context",
                "f1_answer",
                "f1_context",
                "completeness_answer",
                "completeness_context",
                "completeness_strict_answer",
                "completeness_strict_context",
            ],
            label="Summary (weighted)",
            interactive=False,
            wrap=True,
        )

        load_btn.click(
            fn=calc_ratings_eval,
            inputs=[
                dataset_dd,
                eval_dd,
                number_of_facts_start,
                number_of_facts_end,
                metadata_dd,
                metadata_value,
            ],
            outputs=[
                summary_df,
                fig_corr,
                fig_comp,
                fig_comp_context,
                fig_corr_hist,
                err_md,
            ],
        )


# ────────────────────────────────────────────────────────────────────────────
# Entry point
# ────────────────────────────────────────────────────────────────────────────


def get_web_ui() -> gr.Blocks:
    with gr.Blocks() as demo:
        _build_dataset_tab()

    return demo
