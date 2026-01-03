from typing import Literal, Optional
from pandas import DataFrame
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import pandas as pd

PlotType = Literal["Boxplot", "Scatterplot"]


def build_bar_plot(df: pd.DataFrame, col: str, title: str, ylabel: str) -> Figure:
    """Simple bar plot of df[col] by df['source']"""
    fig: Figure = plt.figure(figsize=(8, 5))  # type: ignore
    ax = fig.add_subplot(1, 1, 1)  # type: ignore
    ax.bar(df["source"], df[col], color="skyblue", edgecolor="black")  # type: ignore
    ax.set_title(title)  # type: ignore
    ax.set_xlabel("Source")  # type: ignore
    ax.set_ylabel(ylabel)  # type: ignore
    ax.grid(axis="y", linestyle="--", alpha=0.4)  # type: ignore
    fig.tight_layout()
    return fig


def empty_fig(title: str) -> Figure:
    """Return an empty matplotlib figure with a title."""
    fig: Figure = plt.figure(figsize=(6, 4))  # type: ignore
    ax = fig.add_subplot(1, 1, 1)  # type: ignore
    ax.text(  # type: ignore
        0.5,
        0.5,
        title,
        horizontalalignment="center",
        verticalalignment="center",
        fontsize=12,
    )
    ax.set_axis_off()
    fig.tight_layout()
    return fig


def scatter_plot(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    title: str,
    y_label: str,
    parameter_name: Optional[str] = None,
) -> Figure:
    """Generic scatter-plot helper with optional grouping by a parameter."""
    fig: Figure = plt.figure(figsize=(8, 5))
    ax = fig.add_subplot(1, 1, 1)

    if parameter_name is None:
        # Simple scatter without grouping
        ax.scatter(df[x_col], df[y_col], alpha=0.6)
    else:
        # Group by parameter_name and assign a different color per group automatically
        groups = df.groupby(parameter_name)
        for name, group in groups:
            ax.scatter(
                group[x_col],
                group[y_col],
                alpha=0.6,
                label=str(name),  # legend label per group
            )
        ax.legend(title=parameter_name, frameon=False)

    ax.set_title(title)
    ax.set_xlabel("Number of facts in rating")
    ax.set_ylabel(y_label)
    ax.set_ylim(0, 1)
    ax.grid(linestyle="--", alpha=0.4)
    fig.tight_layout()
    return fig


def boxplot(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    title: str,
    y_label: str,
    parameter_name: str | None = None,
) -> Figure:
    """Generic scatter-plot helper with optional grouping by a parameter."""
    fig: Figure = plt.figure(figsize=(8, 5))
    ax = fig.add_subplot(1, 1, 1)

    if parameter_name is None:
        # Single boxplot for the y_col distribution
        ax.boxplot(df[y_col].dropna(), vert=True)
        ax.set_xticks([1])
        ax.set_xticklabels([y_col])
    else:
        # Boxplots grouped by parameter_name
        grouped = [g[y_col].dropna().values for _, g in df.groupby(parameter_name)]
        labels = [str(name) for name, _ in df.groupby(parameter_name)]

        ax.boxplot(grouped, labels=labels, vert=True)
        ax.set_xticklabels(labels, rotation=30, ha="right")

    ax.set_title(title)
    ax.set_xlabel(parameter_name if parameter_name else "")
    ax.set_ylabel(y_label)
    ax.set_ylim(0, 1)
    ax.grid(linestyle="--", alpha=0.4)
    fig.tight_layout()
    return fig


def plot_relativ_correctness_to_fact_count(
    df_ratings: DataFrame,
    plot_type: PlotType = "Scatterplot",
    parameter_name: str | None = None,
) -> Figure:
    if plot_type == "Boxplot":
        return boxplot(
            df_ratings,
            x_col="element_count",
            y_col="correctness",
            title="Correctness vs. Number of Facts",
            y_label="Correctness",
            parameter_name=parameter_name,
        )
    else:
        return scatter_plot(
            df_ratings,
            x_col="element_count",
            y_col="correctness",
            title="Correctness vs. Number of Facts",
            y_label="Correctness",
            parameter_name=parameter_name,
        )


def hist_correctness(df: DataFrame, n_intervals: int) -> Figure:
    """Histogram of correctness with *n_intervals* bins between 0 and 1."""
    fig: Figure = plt.figure(figsize=(8, 5))
    ax = fig.add_subplot(1, 1, 1)
    bins = [i / n_intervals for i in range(n_intervals + 1)]
    df["correctness"].plot.hist(bins=bins, ax=ax, edgecolor="black")
    ax.set_title("Distribution of Correctness Scores")
    ax.set_xlabel("Correctness")
    ax.set_ylabel("Count")
    ax.set_xticks(bins)
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    fig.tight_layout()
    return fig


def plot_relativ_completeness_answer_to_fact_count(
    df_ratings: DataFrame,
    plot_type: PlotType = "Scatterplot",
    parameter_name: str | None = None,
) -> Figure:
    if plot_type == "Boxplot":
        return boxplot(
            df_ratings,
            x_col="element_count",
            y_col="completeness_answer",
            title="Completeness (Answer) vs. Number of Facts",
            y_label="Completeness (Answer)",
            parameter_name=parameter_name,
        )
    else:
        return scatter_plot(
            df_ratings,
            x_col="element_count",
            y_col="completeness_answer",
            title="Completeness (Answer) vs. Number of Facts",
            y_label="Completeness (Answer)",
            parameter_name=parameter_name,
        )


def plot_relativ_completeness_context_to_fact_count(
    df_ratings: DataFrame,
    plot_type: PlotType = "Scatterplot",
    parameter_name: str | None = None,
) -> Figure:
    if plot_type == "Boxplot":
        return boxplot(
            df_ratings,
            x_col="element_count",
            y_col="completeness_context",
            title="Completeness (Context) vs. Number of Facts",
            y_label="Completeness (Context)",
            parameter_name=parameter_name,
        )
    else:
        return scatter_plot(
            df_ratings,
            x_col="element_count",
            y_col="completeness_context",
            title="Completeness (Context) vs. Number of Facts",
            y_label="Completeness (Context)",
            parameter_name=parameter_name,
        )
