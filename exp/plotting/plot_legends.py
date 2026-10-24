"""Strategy legends drawn once per figure group (the panels have none).

    python3 plot_legends.py [out_dir]   # default: figures/legends

rebalance_vs_eviction_legend.pdf (Fig 1), miss_ratio_curve_legend.pdf (Fig 7),
policy_legend.pdf (Fig 9), legend_one_row_no_disabled_without_hatches.pdf (Figs 10-11).
"""

import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
from matplotlib.transforms import Bbox

from const import (strategy_order, strategy_labels, strategy_colors,
                   strategy_colors_muted, strategy_colors_hatched,
                   strategy_hatches, strategy_linestyles, strategy_markers)

OUT_DIR = "figures/legends"


def _save(handles, labels, path, ncol, fontsize, height_pt=None, **frame):
    """Legend-only PDF cropped to the legend + 0.1in; height_pt pads it to the
    height the LaTeX layout expects."""
    with plt.rc_context({"legend.fontsize": fontsize, "hatch.linewidth": 1.0}):
        fig = plt.figure(figsize=(30, 3))
        leg = fig.legend(handles, labels, loc="center", ncol=ncol,
                         frameon=True, **frame)
        fig.canvas.draw()
        box = leg.get_window_extent().transformed(fig.dpi_scale_trans.inverted())
        box = box.padded(0.1)
        if height_pt:
            extra = max(0.0, height_pt / 72 - box.height) / 2
            box = Bbox([[box.x0, box.y0 - extra], [box.x1, box.y1 + extra]])
        fig.savefig(path, bbox_inches=box)
        plt.close(fig)
    print(f"Saved {path}")


def patches(strategies, colors, hatches=None, edge="#444444", lw=1.0):
    return [Rectangle((0, 0), 1, 1, facecolor=colors[s],
                      hatch=(hatches or {}).get(s, ""), edgecolor=edge,
                      linewidth=lw) for s in strategies]


def main():
    global OUT_DIR
    if len(sys.argv) > 1:
        OUT_DIR = sys.argv[1]
    os.makedirs(OUT_DIR, exist_ok=True)
    every = list(strategy_order)
    labels = [strategy_labels[s] for s in every]
    shadowed = dict(fancybox=True, shadow=True, framealpha=0.9,
                    edgecolor="black")

    # Fig 1
    _save(patches(every, strategy_colors_hatched, strategy_hatches), labels,
          os.path.join(OUT_DIR, "rebalance_vs_eviction_legend.pdf"),
          ncol=-(-len(every) // 2), fontsize=27, height_pt=125, **shadowed)

    # Fig 7
    lines = [Line2D([0], [0], color=strategy_colors_muted[s], linewidth=5,
                    linestyle=strategy_linestyles[s], marker=strategy_markers[s],
                    markersize=20, markerfacecolor=strategy_colors_muted[s],
                    markeredgecolor=strategy_colors_muted[s])
             for s in every]
    _save(lines, labels, os.path.join(OUT_DIR, "miss_ratio_curve_legend.pdf"),
          ncol=len(every), fontsize=30, height_pt=125, fancybox=True, shadow=True,
          edgecolor="#d5d5d5")

    # Fig 9
    _save(patches(every, strategy_colors, edge="black", lw=0.8), labels,
          os.path.join(OUT_DIR, "policy_legend.pdf"),
          ncol=4, fontsize=17, height_pt=81, fancybox=True, shadow=False,
          edgecolor="black", facecolor="#f7f7f7", framealpha=1.0)

    # Figs 10-11: no Disabled
    moved = [s for s in every if s != "disabled"]
    _save(patches(moved, strategy_colors, edge="#555555"),
          [strategy_labels[s] for s in moved],
          os.path.join(OUT_DIR, "legend_one_row_no_disabled_without_hatches.pdf"),
          ncol=len(moved), fontsize=30, height_pt=125, **shadowed)


if __name__ == "__main__":
    main()
