import pandas as pd
import matplotlib.pyplot as plt
import numpy as np


base_path = "./prod/metric_groups_by_dataset"

datasets = [
    # "fachhochschule_erfurt",
    # "medizinischer",
    # "novel",
    "weimar",
]


def create_spider(path: str):
    recall = pd.read_csv(f"{path}/recall.csv")
    precision = pd.read_csv(f"{path}/precision.csv")
    f1 = pd.read_csv(f"{path}/f1.csv")
    correctness = pd.read_csv(f"{path}/correctness.csv")

    judges = recall["Judge-Modell"].unique()

    out_files = []
    for judge in judges:
        df_rec = recall[recall["Judge-Modell"] == judge]
        df_prec = precision[precision["Judge-Modell"] == judge]
        df_f1 = f1[f1["Judge-Modell"] == judge]
        df_corr = correctness[correctness["Judge-Modell"] == judge]

        # merge on RAG Konfig
        df = (
            df_rec[["RAG-Konfiguration", "Antwort-Recall", "Kontext-Recall"]]
            .merge(
                df_prec[["RAG-Konfiguration", "Antwort-Precision"]],
                on="RAG-Konfiguration",
                how="inner",
            )
            .merge(
                df_f1[["RAG-Konfiguration", "Antwort-F1"]],
                on="RAG-Konfiguration",
                how="inner",
            )
            .merge(
                df_corr[["RAG-Konfiguration", "Richtigkeit"]],
                on="RAG-Konfiguration",
                how="inner",
            )
        )

        df = df.sort_values("RAG-Konfiguration")

        metrics = [
            "Antwort-Recall",
            "Kontext-Recall",
            "Antwort-F1",
            "Antwort-Precision",
            "Richtigkeit",
        ]

        N = len(metrics)
        angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
        angles += angles[:1]

        plt.figure(figsize=(6, 6))
        ax = plt.subplot(111, polar=True)

        # ✅ compute global min and apply cropping
        ymin = df[metrics].min().min()
        offset = (1 - ymin) * 0.05  # crop 5% of range
        new_bottom = max(0, ymin - offset)
        ax.set_ylim(bottom=new_bottom, top=1)

        for _, row in df.iterrows():
            values = row[metrics].tolist()
            values += values[:1]
            ax.plot(angles, values, label=row["RAG-Konfiguration"])
            ax.fill(angles, values, alpha=0.1)

        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(metrics)
        ax.set_title(f"Richter: {judge}")
        ax.legend(bbox_to_anchor=(1.1, 1.1))

        fname = f"{path}/radar_{judge}.png"
        plt.savefig(fname, bbox_inches="tight")
        plt.close()
        out_files.append(fname)
        print(f"wrote {fname}")

    return out_files


def create_barchart(path: str):
    recall = pd.read_csv(f"{path}/recall.csv")
    precision = pd.read_csv(f"{path}/precision.csv")
    f1 = pd.read_csv(f"{path}/f1.csv")
    correctness = pd.read_csv(f"{path}/correctness.csv")

    judges = recall["Judge-Modell"].unique()

    out_files = []
    for judge in judges:
        df_rec = recall[recall["Judge-Modell"] == judge]
        df_prec = precision[precision["Judge-Modell"] == judge]
        df_f1 = f1[f1["Judge-Modell"] == judge]
        df_corr = correctness[correctness["Judge-Modell"] == judge]

        df = (
            df_rec[["RAG-Konfiguration", "Antwort-Recall", "Kontext-Recall"]]
            .merge(
                df_prec[["RAG-Konfiguration", "Antwort-Precision"]],
                on="RAG-Konfiguration",
                how="inner",
            )
            .merge(
                df_f1[["RAG-Konfiguration", "Antwort-F1"]],
                on="RAG-Konfiguration",
                how="inner",
            )
            .merge(
                df_corr[["RAG-Konfiguration", "Richtigkeit"]],
                on="RAG-Konfiguration",
                how="inner",
            )
        )

        df = df.sort_values("RAG-Konfiguration")

        metrics = [
            "Antwort-Recall",
            "Kontext-Recall",
            "Antwort-F1",
            "Antwort-Precision",
            "Richtigkeit",
        ]

        plt.figure(figsize=(10, 6))
        x = np.arange(len(metrics))
        width = 0.8 / len(df)

        for idx, (_, row) in enumerate(df.iterrows()):
            values = row[metrics].tolist()
            plt.bar(
                x + idx * width, values, width=width, label=row["RAG-Konfiguration"]
            )

        plt.xticks(x + width * (len(df) - 1) / 2, metrics, rotation=30, ha="right")
        plt.ylabel("Score")
        plt.title(f"Richter: {judge} – Vergleich der Metriken")
        plt.legend(bbox_to_anchor=(1.05, 1), loc="upper left")

        # ✅ Crop the lower part of the axis (dynamic)
        ymin = df[metrics].min().min()
        offset = (1 - ymin) * 0.05  # crop 5% of range

        plt.ylim(bottom=max(0, ymin - offset), top=1)

        fname = f"{path}/barchart_{judge}.png"
        plt.tight_layout()
        plt.savefig(fname, bbox_inches="tight")
        plt.close()
        out_files.append(fname)
        print(f"wrote {fname}")

    return out_files


for dataset in datasets:
    path = f"{base_path}/{dataset}"
    create_barchart(path)
    # create_spider(path)
