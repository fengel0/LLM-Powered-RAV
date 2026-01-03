import seaborn as sns
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import pandas as pd


def build_boxplot(
    df: pd.DataFrame,
    eval_config_id: str,
    eval_config_id_map: dict[str, str],
    system_config_id_map: dict[str, str],
    dataset: str,
) -> Figure:
    filtered = df[df["config_eval"] == eval_config_id]
    if filtered.empty:
        raise Exception(f"No rows found for config {eval_config_id}")

    # Map IDs to readable names
    filtered["config_eval"] = filtered["config_system"].map(eval_config_id_map)
    filtered["config_system"] = filtered["config_system"].map(system_config_id_map)

    # Prepare long-format DataFrame
    long_df = filtered.melt(
        id_vars=["config_system"],
        value_vars=["recall_answer", "recall_context"],
        var_name="metric",
        value_name="value",
    )

    # Define consistent ordering for system configurations
    hue_order = list(system_config_id_map.values())

    fig, ax = plt.subplots(figsize=(12, 6))

    # Boxplot
    sns.boxplot(
        data=long_df,
        x="metric",
        y="value",
        hue="config_system",
        hue_order=hue_order,
        ax=ax,
    )

    # Titles & labels
    ax.set_title(
        f"Recall {dataset} — Antwort vs. Kontext (Auswertungskonfiguration = {eval_config_id_map[eval_config_id]})"
    )
    ax.set_ylabel("Recall-Wert")
    ax.set_xlabel("Metrik")

    ax.legend(
        title="Systemkonfiguration",
        bbox_to_anchor=(1.02, 1),
        loc="upper left",
        borderaxespad=0,
    )

    plt.tight_layout()

    return fig
