"""
Fig 4: how far each strategy's final slab allocation is from the optimal one (a),
and how much higher its miss ratio is because of that (b).

The optimal allocation and the per-class miss ratio curves come from
../trace_analysis/synth_static_202_optimal_allocation_dp.csv.

python3 plot_optimal_comparison.py [--out-dir DIR]   # default: exp/plotting/figures/optimal/
"""

import argparse
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
OPTIMAL = os.path.join(HERE, "../trace_analysis/synth_static_202_optimal_allocation_dp.csv")
TIMELINE = os.path.join(HERE, "../../exp/result/slab_timeline_synth.csv.gz")

CLASSES = ["256", "512", "1024", "2048", "4096"]
STRATEGIES = ["Disabled", "Tail-Age", "Eviction-Rate", "Hits-Per-Slab",
              "Marginal-Hits", "Adaptive-Marginal-Hits"]
COLORS = {
    "Disabled": "#D0D5DE",
    "Tail-Age": "#FFDB99",
    "Eviction-Rate": "#FFBF47",
    "Hits-Per-Slab": "#CC8500",
    "Marginal-Hits": "#11C0FB",
    "Adaptive-Marginal-Hits": "#3DB472",
}
HATCHES = {
    "Disabled": "",
    "Tail-Age": "/",
    "Eviction-Rate": "\\",
    "Hits-Per-Slab": "x",
    "Marginal-Hits": "+",
    "Adaptive-Marginal-Hits": ".",
}

rcParams = {
    "font.size": 38,
    "axes.labelsize": 38,
    "xtick.labelsize": 38,
    "ytick.labelsize": 38,
    "legend.fontsize": 38,
    "hatch.linewidth": 1.0,
    "figure.dpi": 300,
    "savefig.dpi": 300,
}


def load_optimal(path):
    d = pd.read_csv(path)
    mrc = {}
    for c in CLASSES:
        pts = d[[c, c + "_miss_ratio"]].drop_duplicates().sort_values(c).to_numpy(dtype=float)
        mrc[c] = (pts[:, 0], pts[:, 1])
    freq = {c: float(d[c + "_access_freq"].iloc[0]) for c in CLASSES}
    best = d.loc[d.groupby("total_slab_cnt").total_miss_ratio.idxmin()].set_index("total_slab_cnt")
    return mrc, freq, best


def miss_ratio(alloc, mrc, freq):
    total = 0.0
    for c in CLASSES:
        xs, ys = mrc[c]
        total += freq[c] * float(np.interp(alloc.get(c, 0), xs, ys))
    return total / sum(freq.values())


def final_allocations(path):
    df = pd.read_csv(path)
    allocs = {}
    for (slabs, strategy), g in df.groupby(["slabs", "strategy_label"]):
        last = g[g.snapshot == g.snapshot.max()]
        alloc = {}
        for size, n in zip(last.alloc_size, last.total_slabs):
            c = str(int(size))
            if c in CLASSES:
                alloc[c] = alloc.get(c, 0) + int(n)
        allocs[(int(slabs), strategy)] = alloc
    return allocs


def plot_bars(values, sizes, ylabel, output_file):
    fig, ax = plt.subplots(figsize=(11.3, 7.53))
    x = np.arange(len(sizes))
    w = 0.8 / len(STRATEGIES)
    for i, s in enumerate(STRATEGIES):
        ax.bar(x + i * w - 0.4 + w / 2, [values[(n, s)] for n in sizes], width=w,
               color=COLORS[s], hatch=HATCHES[s], edgecolor="#444444", linewidth=1.0)
    ax.set_xticks(x)
    ax.set_xticklabels(sizes)
    ax.set_xlabel("Total Number of Slabs")
    ax.set_ylabel(ylabel)
    ax.grid(alpha=0.3, axis="y")
    ax.set_axisbelow(True)
    fig.savefig(output_file, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default=os.path.join(HERE, "../../exp/plotting/figures/optimal"))
    args = parser.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    mrc, freq, best = load_optimal(OPTIMAL)
    allocs = final_allocations(TIMELINE)
    sizes = sorted({n for n, _ in allocs})

    dist, gap = {}, {}
    for (n, s), alloc in allocs.items():
        opt = {c: int(best.loc[n, c]) for c in CLASSES}
        dist[(n, s)] = sum(abs(alloc.get(c, 0) - opt[c]) for c in CLASSES) / 2
        gap[(n, s)] = miss_ratio(alloc, mrc, freq) - float(best.loc[n, "total_miss_ratio"])
        print(f"{n:>5} {s:24s} distance {dist[(n, s)]:4.0f}  miss ratio gap {gap[(n, s)]:.4f}")

    with plt.rc_context(rcParams):
        plot_bars(dist, sizes, "Distance to\nOptimal Allocation", os.path.join(args.out_dir, "fig04a.pdf"))
        plot_bars(gap, sizes, "Miss Ratio Increase\nfrom the Optimal", os.path.join(args.out_dir, "fig04b.pdf"))

        fig = plt.figure(figsize=(16, 2))
        handles = [plt.Rectangle((0, 0), 1, 1, facecolor=COLORS[s], hatch=HATCHES[s], edgecolor="#444444")
                   for s in STRATEGIES]
        labels = [r"$\mathit{" + s.replace("-", r"\text{-}") + "}$" for s in STRATEGIES]
        fig.legend(handles, labels, loc="center", ncol=3, frameon=True,
                   fancybox=True, shadow=True, framealpha=0.9, edgecolor="black")
        fig.savefig(os.path.join(args.out_dir, "fig04_legend.pdf"), bbox_inches="tight")
        plt.close(fig)
    print(f"Plots saved to: {args.out_dir}")
