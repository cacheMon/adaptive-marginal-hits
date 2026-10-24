"""
Slab allocation over time on meta_202210_kv (864 MB), Marginal-Hits vs
Adaptive-Marginal-Hits, for the 5 classes with the highest peak slab count
under Marginal-Hits.

python3 plot_slab_timeline.py [--out-dir DIR]   # default: exp/plotting/figures/slab_timeline/
"""

import argparse
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "../../exp/result/slab_timeline_meta_compare_marginal.csv.gz")

COLORS = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"]

rcParams = {
    "font.size": 18,
    "axes.labelsize": 25,
    "axes.titlesize": 25,
    "xtick.labelsize": 18,
    "ytick.labelsize": 18,
    "legend.fontsize": 18,
    "axes.linewidth": 1.6,
    "xtick.major.width": 1.6,
    "ytick.major.width": 1.6,
    "grid.linewidth": 1.2,
    "figure.dpi": 300,
    "savefig.dpi": 300,
}


def plot_slab_timeline(df, output_file):
    peaks = df[df.strategy_label == "Marginal-Hits"].groupby("cid").total_slabs.max()
    cids = list(peaks.sort_values(ascending=False).index[:5])

    with plt.rc_context(rcParams):
        fig, axes = plt.subplots(1, 2, figsize=(13.35, 4.85), sharey=True)
        for ax, strategy, title in zip(axes, ["Marginal-Hits", "Adaptive-Marginal-Hits"],
                                       ["Marginal Hits", "Adaptive Marginal Hits"]):
            sub = df[df.strategy_label == strategy]
            for cid, color in zip(cids, COLORS):
                g = sub[sub.cid == cid].sort_values("progress")
                ax.plot(g["progress"], g["total_slabs"], color=color, linewidth=2.8, label=f"CID {cid}")
            ax.set_title(title)
            ax.set_xlabel("# Requests")
            ax.set_xlim(0, 1)
            ax.grid(alpha=0.3, linestyle="--")
            ax.set_ylabel("Total Slabs")
            ax.yaxis.set_major_locator(plt.MultipleLocator(20))

        handles, labels = axes[0].get_legend_handles_labels()
        fig.legend(handles, labels, loc="upper center", ncol=5, frameon=False, bbox_to_anchor=(0.5, 1.07))
        fig.tight_layout()
        fig.savefig(output_file, bbox_inches="tight")
        plt.close(fig)
    print(f"Plot saved to: {output_file} (classes {cids})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default=os.path.join(HERE, "../../exp/plotting/figures/slab_timeline"))
    args = parser.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    df = pd.read_csv(DATA)
    df = df[(df.trace == "202210_kv_traces_all_sort") & (df.cache_size_mb == 864)]
    plot_slab_timeline(df, os.path.join(args.out_dir, "slab_comparison_202210_metakv.pdf"))
