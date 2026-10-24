"""Fig 13: sensitivity of Adaptive-Marginal-Hits (LRU, meta_202210_kv) to six
parameters, cache sizes up to 10% WSS.

    cd exp/plotting && python3 plot_sensitivity_six.py [--xmax 10] [--out-dir DIR]

The window k comes from ../result/emr_window_result_processed.csv, the other
five from ../result/sensitivity_result_processed.csv (one factor at a time).
"""

import argparse
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from const import rcParams

SENS = "../result/sensitivity_result_processed.csv"
EMRW = "../result/emr_window_result_processed.csv"
OUT = "figures/sensitivity_six"

DEFAULTS = {"monitor_interval": 50000, "mhMovingAverageParam": 0.3,
            "mhMinDiff": 2, "thresholdAIADStep": 2, "emrLow": 0.5,
            "emrHigh": 0.95}
# (output name, column, values, legend format)
PANELS = [
    ("emrLow", "emrLow", [0.3, 0.4, 0.5], "{:g}"),
    ("emrHigh", "emrHigh", [0.85, 0.9, 0.95], "{:g}"),
    ("mhMinDiff", "mhMinDiff", [1, 2, 4, 8], "{:g}"),
    ("thresholdAIADStep", "thresholdAIADStep", [1, 2, 4, 8], "{:g}"),
    ("mhMovingAverageParam", "mhMovingAverageParam", [0.1, 0.3, 0.5], "{:g}"),
    ("emrWindow", "emrWindowClassMultiplier", [1, 2, 4, 8], "{:g}×"),
]
K_DEFAULT = 2

SYMBOLS = {
    "emrLow": r"$\mathrm{EMR}_{\min}$",
    "emrHigh": r"$\mathrm{EMR}_{\max}$",
    "mhMinDiff": "Initial\n" + r"threshold ($\theta_0$)",
    "thresholdAIADStep": r"Step ($\Delta\theta$)",
    "mhMovingAverageParam": r"Smoothing ($\alpha$)",
    "emrWindow": r"Window ($k$)",
}

COLORS = ['#E74C3C', '#3498DB', '#2ECC71', '#F39C12']
MARKERS = ['o', 's', '^', 'D']
LINESTYLES = ['-', '--', '-.', ':']

FONT = 38
LEGEND_FONT = 30
FIGSIZE = (8.3, 8)   # six fit across \textwidth


def ofat(df, param):
    for p, v in DEFAULTS.items():
        if p != param:
            df = df[np.isclose(df[p], v)]
    return df


def curves(name, col, values, xmax):
    """{value: Series(miss ratio indexed by cache size in % WSS)}."""
    if col == "emrWindowClassMultiplier":
        df = pd.read_csv(EMRW)
        df = df[df.allocator == "LRU"]
    else:
        df = pd.read_csv(SENS)
        df = ofat(df[(df.trace_name == "meta_202210_kv") & (df.allocator == "LRU")], col)
    df = df.assign(wsr_percent=df.wsr * 100)
    df = df[df.wsr_percent <= xmax + 1e-9]
    g = df.groupby([col, "wsr_percent"]).miss_ratio.mean()
    return {v: g.loc[v].sort_index() for v in values if v in g.index.get_level_values(0)}


def panel(name, col, values, fmt, xmax, out_dir):
    default = K_DEFAULT if col == "emrWindowClassMultiplier" else DEFAULTS[col]
    data = curves(name, col, values, xmax)
    rc = dict(rcParams)
    rc.update({"axes.labelsize": FONT, "xtick.labelsize": FONT,
               "ytick.labelsize": FONT, "legend.fontsize": LEGEND_FONT})
    with plt.rc_context(rc):
        fig, ax = plt.subplots(figsize=FIGSIZE)
        for i, v in enumerate(values):
            if v not in data:
                continue
            s = data[v]
            lab = fmt.format(v) + ("*" if np.isclose(v, default) else "")
            ax.plot(s.index, s.values, color=COLORS[i], linestyle=LINESTYLES[i],
                    marker=MARKERS[i], markersize=18, linewidth=2.5,
                    markerfacecolor=COLORS[i], markeredgecolor="white",
                    markeredgewidth=1, label=lab)
        ax.set_xlabel("Cache Size (% WSS)")
        ax.set_ylabel("Miss Ratio")
        ax.grid(True, alpha=0.3)
        ax.set_xlim(0, xmax * 1.04)
        ax.xaxis.set_major_locator(plt.MultipleLocator(5 if xmax > 10 else 2))
        ax.legend(loc="upper right", frameon=True, fancybox=True, shadow=True,
                  markerscale=0.7, handlelength=1.6, borderpad=0.4,
                  labelspacing=0.3, title=SYMBOLS[name],
                  title_fontsize=LEGEND_FONT)
        fig.tight_layout()
        out = os.path.join(out_dir, f"sensitivity_{name}_LRU.pdf")
        fig.savefig(out, bbox_inches="tight")
        plt.close(fig)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--xmax", type=float, default=10)
    ap.add_argument("--out-dir", default=OUT)
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)
    for name, col, values, fmt in PANELS:
        print("  " + panel(name, col, values, fmt, args.xmax, args.out_dir))


if __name__ == "__main__":
    main()
