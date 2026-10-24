"""
Fig 3: anti-patterns of heuristic slab rebalancing (the per-class series are
from the case-study runs). Fig 12: production A/B deployment at Meta,
Marginal-Hits vs Adaptive-Marginal-Hits (../result/production_ab_*.csv).

cd exp/plotting && python3 plot_case_study_production.py
"""

import os

import matplotlib
matplotlib.use("Agg")
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator
import numpy as np
import matplotlib as mpl
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter

ANTI = "figures/anti_patterns"
PRODUCTION = "figures/production"
os.makedirs(ANTI, exist_ok=True)
os.makedirs(PRODUCTION, exist_ok=True)

# ==================================================
# Fig 12 starts from these notebook settings
# ==================================================
plt.rcParams.update({
    "font.size": 20,
    "axes.titlesize": 20,
    "axes.labelsize": 20,
    "legend.fontsize": 20,
    "lines.linewidth": 3,
    "axes.grid": False,          # control grid manually
    # "grid.alpha": 0.5,
    "grid.linestyle": "--",
})


# ==================================================
# Fig 12: production A/B deployment at Meta
# ==================================================

# Files to plot: filename → metric column name
datasets = [
    ("../result/production_ab_ram_hit_rate.csv", "Miss Rate (%)"),
    ("../result/production_ab_slab_rebalance_60.csv", "Slabs Rebalanced"),
    ("../result/production_ab_cpu.csv", "CPU Usage (%)"),
    ("../result/production_ab_nvm_insert_lat_avg.csv", "Avg NVM \nInsert Latency (us)")
]
color_map = {
    "Marginal-Hits": "#1f77b4",              # blue
    "Adaptive-Marginal-Hits": "#2ca02c"      # green
}

plt.rcParams.update({
    "font.size": 30,
    "axes.labelsize": 28,
    "legend.fontsize": 35,
    "lines.linewidth": 3,

})

# ---- create flat 1x4 layout ----
fig, axes = plt.subplots(1, 4, figsize=(45, 5), sharex=False)

fig.subplots_adjust(wspace=0.3)

for ax, (filename, metric) in zip(axes, datasets):

    df = pd.read_csv(
        filename,
        header=None,
        names=["Label", metric, "Time", "Time 2"]
    )
    # if ram hit rate, then minus by 1 i want miss rate
    if "hit_rate" in filename:
        df[metric] = 100 - df[metric]
        metric = "Miss Rate (%)"

    df["Time"] = pd.to_datetime(df["Time"])
    df["Label"] = df["Label"].apply(
        lambda x: "Adaptive-Marginal-Hits" if str(x).startswith("adaptive") else "Marginal-Hits"
    )
    # the CSVs hold only the plotted 24 h (Jan 27 14:00 to Jan 28 14:00 PST)
    df = df.sort_values("Time")
    t0 = df["Time"].min()
    df["Time_rel_hours"] = (df["Time"] - t0).dt.total_seconds() / 3600


    for label, group in df.groupby("Label"):
        ax.plot(
            group["Time_rel_hours"],
            group[metric],
            color=color_map[label],
            label=label
        )

    # Vertical phase marker
    ax.axvline(1, color="gray", linestyle="--", linewidth=2, alpha=0.8)

    ax.set_xlabel("Hours")
    if "miss" in metric.lower():
        metric = "Miss Ratio (%)"
    ax.set_ylabel(metric)
    # 90 degree turn
    # ax.tick_params(axis='x', rotation=)

    ax.xaxis.set_major_locator(MultipleLocator(1))

    # Grid: y-only, subtle
    ax.grid(axis="y", linestyle="--")
    ax.grid(axis="x", linestyle="--", alpha=0.3)
    # ax onlny 0 to 24
    ax.set_xlim(-0, 24)
    # ax ticks every 2 hours
    ax.xaxis.set_major_locator(MultipleLocator(4))

# ---- flat legend on top ----
handles = [
    plt.Line2D([0], [0], color=color, lw=4)
    for color in color_map.values()
]
labels = list(color_map.keys())

fig.legend(
    handles,
    labels,
    loc="upper center",
    ncol=2,
    frameon=False,
    handlelength=4,
    columnspacing=3,
    fontsize=30,    
    bbox_to_anchor=(0.5, 1.12)
)

# plt.tight_layout(rect=[0, 0, 1, 0.9])
# save to pdf high dpi
fig.savefig(os.path.join(PRODUCTION, "cachelib_comparison.pdf"), bbox_inches="tight", dpi=300)


# ==================================================
# Fig 3c: hits-per-slab anti-pattern (Twitter)
# ==================================================


def k_formatter(x, pos):
    return f"{int(x)}"

# ==================================================
# Global paper settings
# ==================================================
mpl.rcParams.update({
    "figure.figsize": (8, 5.5),
    "figure.dpi": 300,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",

    "font.size": 18,
    "axes.labelsize": 18,
    "axes.titlesize": 18,
    "legend.fontsize": 18,
    "xtick.labelsize": 18,
    "ytick.labelsize": 18,
    "axes.linewidth": 1.1,
    "axes.grid": True,
    "grid.linestyle": "--",
    "grid.alpha": 0.3,

    "lines.linewidth": 2.8,
    "lines.markersize": 8,
    "legend.frameon": False,
})

MARKER_SIZE = 160
# ==================================================
# Colors
# ==================================================
blue = "#308ed2"
green = "#ff8a36"
dash_dotted = (0, (3, 3))

# ==================================================
# Data
# ==================================================
slabs = np.array([1,2,3,4,5,6,7])

delta_miss_c0 = np.array([9231,7138,5263,4317,3894,7653,8988], dtype=float)
delta_miss_c1 = np.array([9836,2781,2265,1691,1172,976,1016], dtype=float)

miss_c0 = np.cumsum(delta_miss_c0[::-1])[::-1]
miss_c1 = np.cumsum(delta_miss_c1[::-1])[::-1]

hits_per_slab_c0 = np.array([38323,24058,17032,15116,13200,11496,10964], dtype=float)
hits_per_slab_c1 = np.array([30456,20558,14575,11530,9572,8158,7070], dtype=float)

# scale to thousands
unit = 1000
miss_c0 /= unit
miss_c1 /= unit
hits_per_slab_c0 /= unit
hits_per_slab_c1 /= unit

# ==================================================
# Policy decision
# ==================================================
victim_slab = 7
receiver_slab = 3

# ==================================================
# Marginal utility (finite difference, no interpolation)
# ==================================================
def centered_slope(arr, slab):
    i = slab - 1
    if i == 0:
        return arr[i+1] - arr[i]
    elif i == len(arr)-1:
        return arr[i] - arr[i-1]
    else:
        return (arr[i+1] - arr[i-1]) / 2

slope_c0 = centered_slope(miss_c0, victim_slab)
slope_c1 = centered_slope(miss_c1, receiver_slab)

x_tan = np.array([slabs.min(), slabs.max()])

# ==================================================
# Figure layout
# ==================================================
fig, axes = plt.subplots(1,2)
fig.subplots_adjust(wspace=0.4, top=0.78)

# ==================================================
# (a) Average Hits per Slab
# ==================================================
ax = axes[0]

ax.plot(slabs, hits_per_slab_c0, "-o", color=blue)
ax.plot(slabs, hits_per_slab_c1, "-s", color=green)

ax.set_xlabel("Cache Size (# Slabs)")
ax.set_ylabel("# Hits per Slab (k)")

ax.annotate(
    "← victim",
    xy=(victim_slab, hits_per_slab_c0[victim_slab-1]),
    xytext=(victim_slab-2.5, hits_per_slab_c0[victim_slab-1]+8),
    color="black",
    arrowprops=dict(arrowstyle="->", linewidth=1.5),
)

ax.annotate(
    "receiver →",
    xy=(receiver_slab, hits_per_slab_c1[receiver_slab-1]),
    xytext=(receiver_slab+1.35, hits_per_slab_c1[receiver_slab-1]-7),
    color="black",
    ha="right",
    arrowprops=dict(arrowstyle="->", linewidth=1.5),
)

# highlight victim
ax.scatter(
    victim_slab,
    hits_per_slab_c0[victim_slab-1],
    marker="X",
    s=MARKER_SIZE,
    zorder=2,
)

# highlight receiver
ax.scatter(
    receiver_slab,
    hits_per_slab_c1[receiver_slab-1],
    marker="X",
    s=MARKER_SIZE,
    zorder=2,
)


ax.yaxis.set_major_formatter(FuncFormatter(k_formatter))

# ==================================================
# (b) Miss Count and Marginal Utility
# ==================================================
ax = axes[1]

ax.plot(slabs, miss_c0, "-o", color=blue)
ax.plot(slabs, miss_c1, "-s", color=green)

# Tangent lines (ΔMiss)
ax.plot(
    x_tan,
    miss_c0[victim_slab-1] + slope_c0*(x_tan-victim_slab),
    linestyle=dash_dotted,
    color=blue,
    linewidth=1.8
)

ax.plot(
    x_tan,
    miss_c1[receiver_slab-1] + slope_c1*(x_tan-receiver_slab),
    linestyle=dash_dotted,
    color=green,
    linewidth=1.8
)


ax.set_xlabel("Cache Size (# Slabs)")
ax.set_ylabel("# Misses (k)")

ax.annotate(
    "← victim",
    xy=(victim_slab, miss_c0[victim_slab-1]),
    xytext=(victim_slab-2.5, miss_c0[victim_slab-1]+23),
    arrowprops=dict(arrowstyle="->", linewidth=1.5),
)

ax.annotate(
    "receiver →",
    xy=(receiver_slab, miss_c1[receiver_slab-1]),
    xytext=(receiver_slab+2.7, miss_c1[receiver_slab-1]+5),
    ha="right",
    arrowprops=dict(arrowstyle="->", linewidth=1.5),
)

# highlight victim
ax.scatter(
    victim_slab,
    miss_c0[victim_slab-1],
    marker="X",
    s=MARKER_SIZE,
    zorder=2,
)

# highlight receiver
ax.scatter(
    receiver_slab,
    miss_c1[receiver_slab-1],
    marker="X",
    s=MARKER_SIZE,
    zorder=2,
)


# format y axis
ax.yaxis.set_major_formatter(FuncFormatter(k_formatter))

# ==================================================
# Shared legend
# ==================================================
legend_handles = [
    Line2D([0],[0], color=blue, lw=2),
    Line2D([0],[0], color=green, lw=2),
    Line2D([0],[0], color="black", lw=1.8, linestyle=dash_dotted),
]

legend_labels = [
    "Class 0",
    "Class 1",
    "ΔMiss (Tangent)",
]

fig.legend(
    legend_handles,
    legend_labels,
    loc="upper center",
    ncol=3,
    frameon=False,
    handlelength=3,
    columnspacing=1.5,
    bbox_to_anchor=(0.5,1.0),
)


for ax in fig.axes:
    ax.xaxis.set_major_locator(MultipleLocator(1))
    
fig.savefig(os.path.join(ANTI, "hitsperslab_analysis.pdf"))


# ==================================================
# Fig 3a: eviction-count anti-pattern (Twitter)
# ==================================================

# ==================================================
# Data
# ==================================================
slabs = np.array([1, 2, 3, 4, 5, 6, 7])

# ---- Eviction rate ----
evict_c0 = np.array([99466, 67640, 58656, 55157, 52702, 50644, 48975], dtype=float)
evict_c1 = np.array([378037, 377317, 376995, 376623, 376204, 375726, 374967], dtype=float)

# ---- ΔMiss ----
dmiss_c0 = np.array([31826, 8984, 3499, 2455, 2058, 1669, 1371], dtype=float)
dmiss_c1 = np.array([720, 322, 372, 419, 478, 759, 1174], dtype=float)

# ==================================================
# Reconstruct miss curves
# ==================================================
miss_c0 = np.cumsum(dmiss_c0[::-1])[::-1]
miss_c1 = np.cumsum(dmiss_c1[::-1])[::-1]

# scale to thousands
unit = 1000
miss_c0 /= unit
miss_c1 /= unit
evict_c0 /= unit
evict_c1 /= unit

# ==================================================
# Policy decision
# ==================================================
victim_slab = 4
receiver_slab = 6

# ==================================================
# Marginal slope (finite difference)
# ==================================================
def slope(arr, slab, type=None):
    i = slab - 1
    if type == "behind":
         return arr[i] - arr[i-1] if i > 0 else arr[1] - arr[0]
    elif type == "ahead":
        return arr[i+1] - arr[i] if i < len(arr) - 1 else arr[-1] - arr[-2]
    if i == 0:
        return arr[1] - arr[0]
    elif i == len(arr) - 1:
        return arr[-1] - arr[-2]
    else:
        return (arr[i+1] - arr[i-1]) / 2

slope_c0 = slope(miss_c0, victim_slab, type="behind")
slope_c1 = slope(miss_c1, receiver_slab, type="ahead")

x_tan = np.array([slabs.min(), slabs.max()])

# ==================================================
# Figure layout
# ==================================================
fig, axes = plt.subplots(1, 2)
fig.subplots_adjust(wspace=0.4, top=0.78)

# ==================================================
# (a) Eviction Rate
# ==================================================
ax = axes[0]

ax.plot(slabs, evict_c0, "-o", color=blue)
ax.plot(slabs, evict_c1, "-s", color=green)

ax.set_xlabel("Cache Size (# Slabs)")
ax.set_ylabel("# Evictions (k)")


ax.yaxis.set_major_formatter(FuncFormatter(k_formatter))
ax.annotate(
    "← victim",
    xy=(victim_slab, evict_c0[victim_slab - 1]),
    xytext=(victim_slab + 0.2, evict_c0[victim_slab - 1] + 100),
    arrowprops=dict(arrowstyle="->", linewidth=1.5),
)

ax.annotate(
    "receiver →",
    xy=(receiver_slab, evict_c1[receiver_slab - 1]),
    xytext=(receiver_slab - 0.2, evict_c1[receiver_slab - 1] - 100),
    ha="right",
    arrowprops=dict(arrowstyle="->", linewidth=1.5),
)
# highlight victim
ax.scatter(
    victim_slab,
    evict_c0[victim_slab-1],
    marker="X",
    s=MARKER_SIZE,
    zorder=2
)

# highlight receiver
ax.scatter(
    receiver_slab,
    evict_c1[receiver_slab-1],
    marker="X",
    s=MARKER_SIZE,
    zorder=2
)


# ==================================================
# (b) Miss Count + Marginal Utility
# ==================================================
ax = axes[1]

ax.plot(slabs, miss_c0, "-o", color=blue)
ax.plot(slabs, miss_c1, "-s", color=green)

# ΔMiss tangents
ax.plot(
    x_tan,
    miss_c0[victim_slab - 1] + slope_c0 * (x_tan - victim_slab),
    linestyle=dash_dotted,
    color=blue,
    linewidth=1.8,
)

ax.plot(
    x_tan,
    miss_c1[receiver_slab - 1] + slope_c1 * (x_tan - receiver_slab),
    linestyle=dash_dotted,
    color=green,
    linewidth=1.8,
)



ax.set_xlabel("Cache Size (# Slabs)")
ax.set_ylabel("# Misses (k)")

ax.annotate(
    "← victim",
    xy=(victim_slab, miss_c0[victim_slab - 1]),
    xytext=(victim_slab - 1.3, miss_c0[victim_slab - 1] + 15),
    arrowprops=dict(arrowstyle="->", linewidth=1.5),
)

ax.annotate(
    "receiver →",
    xy=(receiver_slab, miss_c1[receiver_slab - 1]),
    xytext=(receiver_slab - 0.6, miss_c1[receiver_slab - 1] - 5),
    ha="right",
    arrowprops=dict(arrowstyle="->", linewidth=1.5),
)

# highlight victim
ax.scatter(
    victim_slab,
    miss_c0[victim_slab-1],
    marker="X",
    s=MARKER_SIZE,
    zorder=2,
)

# highlight receiver
ax.scatter(
    receiver_slab,
    miss_c1[receiver_slab-1],
    marker="X",
    s=MARKER_SIZE,
    zorder=2,
)


# ==================================================
# Legend
# ==================================================
legend_handles = [
    Line2D([0], [0], color=blue, lw=2),
    Line2D([0], [0], color=green, lw=2),
    Line2D([0], [0], color="black", lw=1.8, linestyle=dash_dotted),
]

legend_labels = [
    "Class 0",
    "Class 1",
    "ΔMiss (Tangent)",
]

fig.legend(
    legend_handles,
    legend_labels,
    loc="upper center",
    ncol=3,
    frameon=False,
    handlelength=3,
    columnspacing=1.5,
    bbox_to_anchor=(0.5, 1.0),
)

ax.yaxis.set_major_formatter(FuncFormatter(k_formatter))


for ax in fig.axes:
    ax.xaxis.set_major_locator(MultipleLocator(1))
    
fig.savefig(os.path.join(ANTI, "eviction_analysis.pdf"))


# ==================================================
# Fig 3b: tail-age anti-pattern (Meta KV)
# ==================================================

# ==================================================
# Data
# ==================================================
slabs = np.array([1, 2, 3, 4, 5, 6])

# ---- Tail Age ----
tail_age_c0 = np.array([1, 2, 4, 6, 8, 10], dtype=float)
tail_age_c1 = np.array([1, 2, 2, 4, 5, 7], dtype=float)

# ---- Miss data ----
miss_c0 = np.array([134304, 95948, 71033, 36047, 31276, 26510], dtype=float)
miss_c1 = np.array([69350, 36997, 19667, 11371, 8270, 6199], dtype=float)

# scale to thousands
unit = 1000
miss_c0 /= unit
miss_c1 /= unit

# ==================================================
# Policy decision
# ==================================================
victim_slab = 4
receiver_slab = 3

# ==================================================
# Marginal slope (finite difference)
# ==================================================
def slope(arr, slab, type=None):
    i = slab - 1
    if type == "behind":
         return arr[i] - arr[i-1] if i > 0 else arr[1] - arr[0]
    elif type == "ahead":
        return arr[i+1] - arr[i] if i < len(arr) - 1 else arr[-1] - arr[-2]
    if i == 0:
        return arr[1] - arr[0]
    elif i == len(arr) - 1:
        return arr[-1] - arr[-2]
    else:
        return (arr[i+1] - arr[i-1]) / 2

slope_c0 = slope(miss_c0, victim_slab, type="behind")
slope_c1 = slope(miss_c1, receiver_slab, type="ahead")

x_tan = np.array([slabs.min(), slabs.max()])

# ==================================================
# Figure layout
# ==================================================
fig, axes = plt.subplots(1, 2)
fig.subplots_adjust(wspace=0.4, top=0.78)

# ==================================================
# (a) Tail Age vs Cache Size
# ==================================================
ax = axes[0]

ax.plot(slabs, tail_age_c0, "-o", color=blue)
ax.plot(slabs, tail_age_c1, "-s", color=green)

ax.set_xlabel("Cache Size (# Slabs)")
ax.set_ylabel("Tail Age (s)")

ax.annotate(
    "← victim",
    xy=(victim_slab, tail_age_c0[victim_slab-1]),
    xytext=(victim_slab-2, tail_age_c0[victim_slab-1]+1.2),
    arrowprops=dict(arrowstyle="->", linewidth=1.5),
)

ax.annotate(
    "receiver →",
    xy=(receiver_slab, tail_age_c1[receiver_slab-1]),
    xytext=(receiver_slab+3, tail_age_c1[receiver_slab-1]-0.95),
    ha="right",
    arrowprops=dict(arrowstyle="->", linewidth=1.5),
)

# highlight victim
ax.scatter(
    victim_slab,
    tail_age_c0[victim_slab-1],
    marker="X",
    s=MARKER_SIZE,
    zorder=2,
)

# highlight receiver
ax.scatter(
    receiver_slab,
    tail_age_c1[receiver_slab-1],
    marker="X",
    s=MARKER_SIZE,
    zorder=2
)


# ==================================================
# (b) Miss Count + Marginal Utility
# ==================================================
ax = axes[1]

ax.plot(slabs, miss_c0, "-o", color=blue)
ax.plot(slabs, miss_c1, "-s", color=green)

# ΔMiss tangents
ax.plot(
    x_tan,
    miss_c0[victim_slab-1] + slope_c0*(x_tan-victim_slab),
    linestyle=dash_dotted,
    color=blue,
    linewidth=1.8,
)

ax.plot(
    x_tan,
    miss_c1[receiver_slab-1] + slope_c1*(x_tan-receiver_slab),
    linestyle=dash_dotted,
    color=green,
    linewidth=1.8,
)

ax.set_xlabel("Cache Size (# Slabs)")
ax.set_ylabel("# Misses")

# y axis formatter
ax.yaxis.set_major_formatter(FuncFormatter(k_formatter))
ax.annotate(
    "← victim",
    xy=(victim_slab, miss_c0[victim_slab-1]),
    xytext=(victim_slab-0.3, miss_c0[victim_slab-1]+30),
    arrowprops=dict(arrowstyle="->", linewidth=1.5),
)

ax.annotate(
    "receiver →",
    xy=(receiver_slab, miss_c1[receiver_slab-1]),
    xytext=(receiver_slab+1.2, miss_c1[receiver_slab-1]-28),
    ha="right",
    arrowprops=dict(arrowstyle="->", linewidth=1.5),
)
# highlight victim
ax.scatter(
    victim_slab,
    miss_c0[victim_slab-1],
    marker="X",
    s=MARKER_SIZE,
    zorder=2
)

# highlight receiver
ax.scatter(
    receiver_slab,
    miss_c1[receiver_slab-1],
    marker="X",
    s=MARKER_SIZE,
    zorder=2
)

# ==================================================
# Shared legend
# ==================================================
legend_handles = [
    Line2D([0], [0], color=blue, lw=2),
    Line2D([0], [0], color=green, lw=2),
    Line2D([0], [0], color="black", lw=1.8, linestyle=dash_dotted),
]

legend_labels = [
    "Class 0",
    "Class 1",
    "ΔMiss (Tangent)",
]

fig.legend(
    legend_handles,
    legend_labels,
    loc="upper center",
    ncol=3,
    frameon=False,
    handlelength=3,
    columnspacing=1.5,
    bbox_to_anchor=(0.5, 1.0),
)
# min y is 0
plt.ylim(bottom=-20)


for ax in fig.axes:
    ax.xaxis.set_major_locator(MultipleLocator(1))
    
fig.savefig(os.path.join(ANTI, "tailage_analysis.pdf"))
