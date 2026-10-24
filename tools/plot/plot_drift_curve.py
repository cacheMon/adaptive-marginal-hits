"""
Fig 6: synthetic trace whose class mix flips at 80M requests (256 slabs).
(a) Adaptive-Marginal-Hits slabs per class, with the threshold theta on the right axis
(b) miss ratio over time, Marginal-Hits vs Adaptive-Marginal-Hits

python3 plot_drift_curve.py [--out-dir DIR]   # default: exp/plotting/figures/drift/
"""

import argparse
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.ticker import FixedLocator, NullLocator, ScalarFormatter
from matplotlib.transforms import Bbox

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "../../exp/result/drift_timeline.csv.gz")

# same class colors as Fig 5
CLASS_COLORS = {256: "#636EFA", 512: "#EF553B", 1024: "#00CC96", 2048: "#FFA15A", 4096: "#AB63FA"}
MH_COLOR = "#11C0FB"
AMH_COLOR = "#3DB472"
THETA_COLOR = "0.55"

rcParams = {
    "font.size": 20,
    "axes.labelsize": 20,
    "xtick.labelsize": 20,
    "ytick.labelsize": 20,
    "legend.fontsize": 15,
    "figure.dpi": 300,
    "savefig.dpi": 300,
}

# Fig 5 canvas and plot area in points, measured from oscillation_number_of_slabs.pdf
FIG_W, FIG_H = 395.40, 264.07
AX_LEFT, AX_BOTTOM, AX_W, AX_H = 75.72, 56.92, 312.48, 199.59
# panel (a) is 0.495\linewidth in LaTeX, panel (b) and Fig 5 are 0.48
FIG_A_W = FIG_W * 0.495 / 0.48


def new_figure(width, ax_width):
    fig = plt.figure(figsize=(width / 72, FIG_H / 72))
    ax = fig.add_axes([AX_LEFT / width, AX_BOTTOM / FIG_H, ax_width / width, AX_H / FIG_H])
    return fig, ax


def style(ax, xmax):
    ax.grid(alpha=0.3, linestyle="--")
    ax.spines["top"].set_visible(False)
    ax.xaxis.set_major_locator(plt.MultipleLocator(40))
    ax.set_xlim(-0.05 * xmax, 1.05 * xmax)
    ax.set_xlabel("Logical Time (Million Requests)")


def miss_ratio(df, wakeup):
    # miss ratio (%) per rebalancer round, then a centered mean over 20 rounds
    hits = df.groupby("round")["hits"].sum().sort_index()
    mr = (1 - hits.diff() / wakeup) * 100
    mreq = df.groupby("round")["mreq"].first().reindex(mr.index)
    out = pd.DataFrame({"mreq": mreq, "mr": mr}).dropna()
    return out["mreq"], out["mr"].rolling(20, center=True, min_periods=1).mean()


def plot_a(df, theta, xmax, ax_width):
    fig, ax = new_figure(FIG_A_W, ax_width)
    for size in sorted(CLASS_COLORS):
        g = df[df.alloc == size].sort_values("round")
        ax.plot(g["mreq"], g["slabs"], color=CLASS_COLORS[size], linewidth=1.8)
    style(ax, xmax)
    ax.set_ylabel("Number of Slabs")
    ax.yaxis.set_major_locator(plt.MultipleLocator(20))
    ax.set_ylim(0, 105)

    ax2 = ax.twinx()
    ax2.step(theta["mreq"], theta["thetaAfter"], where="post", color=THETA_COLOR, linewidth=1.4, linestyle="--")
    ax.set_zorder(ax2.get_zorder() + 1)
    ax.patch.set_visible(False)
    ax2.set_yscale("log", base=2)
    ax2.yaxis.set_major_locator(FixedLocator([2, 4, 8, 16, 32]))
    ax2.yaxis.set_minor_locator(NullLocator())
    ax2.yaxis.set_major_formatter(ScalarFormatter())
    ax2.set_ylim(1.6, 48)
    ax2.set_ylabel(r"Threshold $\theta$")
    ax2.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax2.spines["right"].set_linestyle("--")
    ax2.spines["right"].set_color(THETA_COLOR)
    ax2.tick_params(axis="y", colors="0.35")
    ax2.yaxis.label.set_color("0.35")
    ax2.set_xlim(ax.get_xlim())
    return fig


def plot_b(mh, amh, xmax):
    fig, ax = new_figure(FIG_W, AX_W)
    ax.plot(*mh, color=MH_COLOR, linewidth=1.8)
    ax.plot(*amh, color=AMH_COLOR, linewidth=1.8)
    style(ax, xmax)
    ax.spines["right"].set_visible(False)
    ax.set_ylabel("Miss Ratio (%)")
    ax.set_ylim(10, 20)
    ax.yaxis.set_major_locator(plt.MultipleLocator(2))
    return fig


def plot_legends(out_dir):
    line = lambda c: Line2D([0], [0], color=c, lw=2.5)
    kw = dict(frameon=False, handlelength=1.4, handletextpad=0.5, columnspacing=1.0,
              labelspacing=0.3, borderaxespad=0, borderpad=0.2, fontsize=15)

    fig_b = plt.figure(figsize=(8, 2))
    leg = fig_b.legend([line(MH_COLOR), line(AMH_COLOR)],
                       [r"$\mathit{Marginal\text{-}Hits}$", r"$\mathit{Adaptive\text{-}Marginal\text{-}Hits}$"],
                       ncol=1, loc="center", **kw)
    fig_b.canvas.draw()
    r = fig_b.canvas.get_renderer()
    t0, t1 = [t.get_window_extent(r) for t in leg.get_texts()]
    pitch = (t0.y0 - t1.y0) / fig_b.bbox.height

    fig_a = plt.figure(figsize=(8, 2))
    colors = list(CLASS_COLORS.values())
    for row, ids in enumerate([[0, 1, 2], [3, 4]]):
        leg = fig_a.legend([line(colors[i]) for i in ids], [f"Class {i}" for i in ids], ncol=len(ids),
                           loc="center", bbox_to_anchor=(0.5, 0.5 + pitch * (0.5 - row)), **kw)
        fig_a.add_artist(leg)

    figs = [(fig_a, "fig_drift_legend_a.pdf"), (fig_b, "fig_drift_legend_b.pdf")]
    boxes = []
    for fig, _ in figs:
        fig.canvas.draw()
        boxes.append(fig.get_tightbbox(fig.canvas.get_renderer()))
    y0 = min(b.y0 for b in boxes) - 0.03
    y1 = max(b.y1 for b in boxes) + 0.03
    for (fig, name), b in zip(figs, boxes):
        fig.savefig(os.path.join(out_dir, name), bbox_inches=Bbox([[b.x0 - 0.03, y0], [b.x1 + 0.03, y1]]))
        plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default=os.path.join(HERE, "../../exp/plotting/figures/drift"))
    args = parser.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    data = pd.read_csv(DATA, float_precision="round_trip")
    data = data[data.cache_slabs == 256]
    cls = data[data.series == "class"]
    amh = cls[cls.strategy == "marginal-hits-new"]
    mh = cls[cls.strategy == "marginal-hits-old"]
    theta = data[(data.series == "theta") & (data.strategy == "marginal-hits-new")]
    wakeup = int(amh.wakeup.iloc[0])
    xmax = round(amh.mreq.max())

    with plt.rc_context(rcParams):
        # make room for the theta axis labels
        fig = plot_a(amh, theta, xmax, AX_W)
        fig.canvas.draw()
        overhang = fig.get_tightbbox(fig.canvas.get_renderer()).x1 * 72 - (AX_LEFT + AX_W)
        plt.close(fig)
        fig = plot_a(amh, theta, xmax, FIG_A_W - AX_LEFT - overhang - 2.0)
        fig.savefig(os.path.join(args.out_dir, "fig_drift_a.pdf"))
        plt.close(fig)

        fig = plot_b(miss_ratio(mh, wakeup), miss_ratio(amh, wakeup), xmax)
        fig.savefig(os.path.join(args.out_dir, "fig_drift_b.pdf"))
        plt.close(fig)

        plot_legends(args.out_dir)
    print(f"Plots saved to: {args.out_dir}")
