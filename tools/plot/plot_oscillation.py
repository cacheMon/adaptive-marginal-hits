"""
Fig 5: Marginal-Hits on the stationary 5-class synthetic trace (256 slabs).
(a) tail hits per class in each window, (b) number of slabs per class.

python3 plot_oscillation.py [--out-dir DIR]   # default: exp/plotting/figures/oscillation/
"""

import argparse
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
TIMELINE = os.path.join(HERE, "../../exp/result/slab_timeline_synth.csv.gz")

# allocation size -> color, class 0 to 4
CLASS_COLORS = {256: "#636EFA", 512: "#EF553B", 1024: "#00CC96", 2048: "#FFA15A", 4096: "#AB63FA"}

rcParams = {
    "font.size": 20,
    "axes.labelsize": 20,
    "xtick.labelsize": 20,
    "ytick.labelsize": 20,
    "legend.fontsize": 15,
    "figure.dpi": 300,
    "savefig.dpi": 300,
}


def load(path):
    df = pd.read_csv(path)
    df = df[(df.strategy_label == "Marginal-Hits") & (df.slabs == 256)]
    mreq = df.groupby("snapshot").gets.sum() / 1e6
    data = {}
    for size, g in df.groupby("alloc_size"):
        if size not in CLASS_COLORS:
            continue
        g = g.sort_values("snapshot").set_index("snapshot")
        # tail_hits is cumulative, so take the difference between snapshots
        hits = g.tail_hits.diff()
        hits.iloc[0] = g.tail_hits.iloc[0]
        data[size] = pd.DataFrame({
            "mreq": mreq.reindex(g.index).values,
            "tail_hits": hits.clip(lower=0).values,
            "total_slabs": g.total_slabs.values,
        })
    return data


def average(d, k=3):
    b = np.arange(len(d)) // k
    return d.groupby(b).agg(mreq=("mreq", "last"), tail_hits=("tail_hits", "mean"),
                            total_slabs=("total_slabs", "last"))


def plot(data, column, ylabel, ystep, output_file):
    fig, ax = plt.subplots(figsize=(5.6, 3.6))
    for size, color in CLASS_COLORS.items():
        ax.plot(data[size]["mreq"], data[size][column], color=color, linewidth=1.8)
    ax.set_xlabel("Logical Time (Million Requests)")
    ax.set_ylabel(ylabel)
    ax.grid(alpha=0.3, linestyle="--")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.xaxis.set_major_locator(plt.MultipleLocator(20))
    ax.yaxis.set_major_locator(plt.MultipleLocator(ystep))

    if column == "tail_hits":
        # y range without the warm-up
        span = max(d["mreq"].max() for d in data.values())
        steady = pd.concat([d.loc[d["mreq"] > 0.02 * span, column] for d in data.values()])
        pad = 0.05 * (steady.max() - steady.min())
        ax.set_ylim(max(0, steady.min() - pad), steady.max() + pad)

    fig.savefig(output_file, bbox_inches="tight")
    plt.close(fig)


def plot_legend(output_file):
    fig = plt.figure(figsize=(8, 1))
    h = {size: plt.Line2D([0], [0], color=color, lw=2) for size, color in CLASS_COLORS.items()}
    blank = plt.Line2D([0], [0], color="none")
    # 2 rows x 3 columns; matplotlib fills the legend column by column
    handles = [blank, h[1024], h[256], h[2048], h[512], h[4096]]
    labels = ["Allocation Class", "Class 2: 1024-byte", "Class 0: 256-byte",
              "Class 3: 2048-byte", "Class 1: 512-byte", "Class 4: 4096-byte"]
    fig.legend(handles, labels, loc="center", ncol=3, frameon=True, fancybox=False,
               edgecolor="#d5d5d5", handlelength=1.6, columnspacing=1.0)
    fig.savefig(output_file, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default=os.path.join(HERE, "../../exp/plotting/figures/oscillation"))
    args = parser.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    data = load(TIMELINE)
    with plt.rc_context(rcParams):
        plot({s: average(d) for s, d in data.items()}, "tail_hits", "Tail Hits", 25,
             os.path.join(args.out_dir, "oscillation_tail_hit.pdf"))
        plot(data, "total_slabs", "Number of Slabs", 20, os.path.join(args.out_dir, "oscillation_number_of_slabs.pdf"))
        plot_legend(os.path.join(args.out_dir, "oscillation_legend.pdf"))
    print(f"Plots saved to: {args.out_dir}")
