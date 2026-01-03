# -*- coding: utf-8 -*-
import io
import pandas as pd
import matplotlib.pyplot as plt

# Load the data
df = pd.read_csv("./recall_verlauf.csv")

# Ensure correct order on the x-axis and drop accidental duplicate rows
fakten_order = ["0-5", "5-10", "10-15", "15-20", "20-25"]
df["Fakten"] = pd.Categorical(df["Fakten"], categories=fakten_order, ordered=True)
df = df.drop_duplicates()


# Helper to plot one metric across Fakten for each configuration
def plot_metric(metric_col: str, title: str, ylabel: str, marker: str):
    plt.figure(figsize=(10, 6))
    for config, sub in df.groupby("RAG-Konfiguration", sort=False):
        sub = sub.sort_values("Fakten")
        plt.plot(
            sub["Fakten"], sub[metric_col], marker=marker, linewidth=2, label=config
        )
    plt.title(title)
    plt.xlabel("Fakten")
    plt.ylabel(ylabel)
    plt.grid(True, alpha=0.3)
    plt.legend(title="RAG-Konfiguration")
    plt.tight_layout()


# 1) Antwort-Recall
plot_metric(
    "Antwort-Recall", "Antwort-Recall nach Faktenbereich", "Antwort-Recall", marker="o"
)

# 2) Kontext-Recall
plot_metric(
    "Kontext-Recall", "Kontext-Recall nach Faktenbereich", "Kontext-Recall", marker="s"
)

plt.show()
