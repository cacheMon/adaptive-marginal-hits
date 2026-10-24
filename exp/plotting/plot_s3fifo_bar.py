"""Fig 14: miss ratio on Wikimedia 2016 and 2019 upload (1% WSS) under TinyLFU,
S3-FIFO and SIEVE.

    cd exp/plotting && python3 plot_s3fifo_bar.py [--out-dir DIR]

TinyLFU rows come from ../result/efficiency_result_processed.csv, S3-FIFO, SIEVE
and Adaptive-Hits-Per-Slab from ../result/eviction_policy_sweep_processed.csv
(configs: ../prepare_exp_configs/gen_s3fifo_config.py).
"""

import argparse
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Rectangle
from matplotlib.transforms import Bbox

import const

SHIPPED = "../result/efficiency_result_processed.csv"
SWEEP = "../result/eviction_policy_sweep_processed.csv"
OUT = "figures/s3fifo"
WSR = 0.01
TRACES = ["wiki_2016u", "wiki_2019u"]
ALLOCS = ["TINYLFU", "S3FIFO", "SIEVE"]
ALLOC_LABELS = {"TINYLFU": "TinyLFU", "S3FIFO": "S3-FIFO", "SIEVE": "SIEVE"}

V3 = "adaptive-hits-per-slab"
STRATEGIES = const.strategy_order + [V3]
COLORS = {**const.strategy_colors_hatched, V3: "#9467BD"}
HATCHES = {**const.strategy_hatches, V3: "||"}  # doubled: visible in narrow bars
EDGE = "#444444"
LABELS = {**const.strategy_labels,
          V3: r"$\mathit{Adaptive\text{-}Hits\text{-}Per\text{-}Slab}$"}

STYLE = {
    "font.size": 20, "axes.labelsize": 20,
    "xtick.labelsize": 20, "ytick.labelsize": 18,
    "figure.dpi": 300, "savefig.dpi": 300,
}
FIGSIZE = (5.6, 4.0)


def load():
    ship = pd.read_csv(SHIPPED, low_memory=False)
    ship = ship[ship.allocator == "TINYLFU"]
    sweep = pd.read_csv(SWEEP, low_memory=False)
    df = pd.concat([ship, sweep], ignore_index=True)
    df["wsr"] = df.wsr.round(6)
    return df[(df.wsr == WSR) & df.allocator.isin(ALLOCS)]


def panel(d, out):
    with plt.rc_context({**STYLE, "hatch.linewidth": 1.0}):
        fig, ax = plt.subplots(figsize=FIGSIZE)
        x = np.arange(len(ALLOCS))
        group = 0.84
        # same bar width in every group; smaller groups are centred
        counts = [len([s for s in STRATEGIES if s in set(d[d.allocator == al].rebalance_strategy)])
                  for al in ALLOCS]
        w = group / max(counts)
        for j, alloc in enumerate(ALLOCS):
            a = d[d.allocator == alloc]
            present = [s for s in STRATEGIES if s in set(a.rebalance_strategy)]
            for k, s in enumerate(present):
                ax.bar(x[j] + (k - (len(present) - 1) / 2) * w,
                       a[a.rebalance_strategy == s].miss_ratio.mean(), w,
                       color=COLORS[s], hatch=HATCHES.get(s, ""), edgecolor=EDGE, linewidth=1)
        ax.set_xticks(x)
        ax.set_xticklabels([ALLOC_LABELS[a] for a in ALLOCS])
        ax.set_xlim(-0.5, len(ALLOCS) - 0.5)
        ax.set_ylabel("Miss Ratio")
        ax.grid(True, alpha=0.3, axis="y")
        ax.set_axisbelow(True)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        fig.savefig(out, bbox_inches="tight")
        plt.close(fig)


def legend(path):
    handles = [Rectangle((0, 0), 1, 1, facecolor=COLORS[s], hatch=HATCHES.get(s, ""),
                         edgecolor=EDGE, linewidth=1.0) for s in STRATEGIES]
    with plt.rc_context({"legend.fontsize": 17, "hatch.linewidth": 1.0}):
        fig = plt.figure(figsize=(14, 2))
        leg = fig.legend(handles, [LABELS[s] for s in STRATEGIES], loc="center", ncol=4,
                         frameon=True, fancybox=True, shadow=True, edgecolor="black",
                         framealpha=0.9)
        fig.canvas.draw()
        box = leg.get_window_extent().transformed(fig.dpi_scale_trans.inverted())
        fig.savefig(path, bbox_inches=Bbox(box.padded(0.1).get_points()))
        plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out-dir", default=OUT)
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)
    df = load()
    for t in TRACES:
        out = os.path.join(args.out_dir, f"fig_s3fifo_{t}_col.pdf")
        panel(df[df.trace_name == t], out)
        print(f"  {out}")
    leg = os.path.join(args.out_dir, "legend_s3fifo_wiki.pdf")
    legend(leg)
    print(f"  {leg}")


if __name__ == "__main__":
    main()
