"""Recreate the manuscript figures from the frozen result tables."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "figures"
OUT.mkdir(exist_ok=True)

BAL = ROOT / "results/balanced/analysis"
HLD = ROOT / "results/challenge/analysis"
ALGS = ["AF-FDD-v0.2.2", "Bai-2021", "Yeh-2024"]
LABELS = {"AF-FDD-v0.2.2": "AF-FDD", "Bai-2021": "Bai et al.", "Yeh-2024": "Yeh"}
COLORS = {"AF-FDD-v0.2.2": "#1f5a94", "Bai-2021": "#c76d1d", "Yeh-2024": "#5b8f55"}


def style() -> None:
    plt.rcParams.update({
        "font.family": "serif",
        "font.size": 9,
        "axes.labelsize": 9,
        "axes.titlesize": 10,
        "legend.fontsize": 8,
        "figure.dpi": 160,
    })


def performance_profiles() -> None:
    style()
    fig, axes = plt.subplots(1, 2, figsize=(7.1, 2.65), constrained_layout=True)
    for ax, folder, title in zip(
        axes,
        [BAL, HLD],
        ["Balanced corpus", "Conditionally selected challenge corpus"],
    ):
        data = pd.read_csv(folder / "performance_profile.csv")
        for alg in ALGS:
            g = data[data.algorithm == alg]
            ax.plot(g.tau, g.fraction, marker="o", ms=2.7, lw=1.4,
                    label=LABELS[alg], color=COLORS[alg])
        ax.set_xscale("log", base=2)
        ax.set_ylim(0, 1.02)
        ax.grid(True, which="both", lw=0.35, alpha=0.45)
        ax.set_title(title)
        ax.set_xlabel(r"Performance factor $\tau$")
        ax.set_ylabel("Fraction solved within factor")
    axes[0].legend(loc="lower right", frameon=False)
    fig.savefig(OUT / "performance_profiles.pdf", bbox_inches="tight")
    fig.savefig(OUT / "performance_profiles.png", bbox_inches="tight")
    plt.close(fig)


def output_regime() -> None:
    style()
    data = pd.read_csv(BAL / "structural_data.csv")
    bins = [-1, 10, 100, 1_000, 10_000, 100_000, 1_000_000, np.inf]
    labels = [r"$\leq10$", "11--100", "101--1k", "1k--10k", "10k--100k", "100k--1M", ">1M"]
    fig, ax = plt.subplots(figsize=(7.1, 2.75), constrained_layout=True)
    x = np.arange(len(labels))
    width = 0.36
    for offset, base in [(-width / 2, "Bai-2021"), (width / 2, "Yeh-2024")]:
        common = data[(data["AF-FDD-v0.2.2_complete_solved"] == 1) &
                      (data[f"{base}_complete_solved"] == 1)].copy()
        common["output_bin"] = pd.cut(common.outputs, bins=bins, labels=labels)
        values = []
        for label in labels:
            group = common[common.output_bin == label]
            ratio = group[f"{base}_median_seconds"] / group["AF-FDD-v0.2.2_median_seconds"]
            values.append(float(np.exp(np.log(ratio).mean())) if len(ratio) else np.nan)
        ax.bar(x + offset, values, width, label=LABELS[base], color=COLORS[base])
    ax.axhline(1.0, color="black", lw=0.8)
    ax.set_yscale("log")
    ax.set_xticks(x, labels)
    ax.set_ylabel("Geometric mean of baseline / AF-FDD time")
    ax.set_xlabel("Number of all-level outputs")
    ax.grid(True, axis="y", which="both", lw=0.35, alpha=0.45)
    ax.legend(frameon=False, ncol=2, loc="upper left")
    fig.savefig(OUT / "output_regime_speedup.pdf", bbox_inches="tight")
    fig.savefig(OUT / "output_regime_speedup.png", bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    performance_profiles()
    output_regime()
