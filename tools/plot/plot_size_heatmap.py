"""
Fig 2: request size heatmaps of Twitter cluster50 (a) and cluster2 (b).
The input tables in trace_heatmap/data/ come from libCacheSim's traceAnalyzer.

python3 plot_size_heatmap.py [--out-dir DIR]   # default: trace_heatmap/
"""

import argparse
import os
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import FuncFormatter

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "../../trace_heatmap/data")

rcParams = {
    "axes.grid": False,
    "font.size": 18,
    "axes.labelsize": 24,
    "xtick.labelsize": 20,
    "ytick.labelsize": 20,
    "figure.dpi": 300,
    "savefig.dpi": 300,
}


def load(path):
    with open(path) as f:
        f.readline()
        header = f.readline()
        rows = [line.strip("\n,").split(",") for line in f if line.strip()]
    tw, log_base, size_base = re.search(
        r"time window (\d+), log_base ([\d.]+), size_base (\d+)", header).groups()

    data = np.zeros((len(rows), max(len(r) for r in rows)))
    for i, r in enumerate(rows):
        v = np.array(r, dtype=float)
        if v.sum() > 0:
            v = v / v.sum()
        data[i, :len(v)] = v
    return data.T, int(tw), float(log_base), int(size_base)


def plot(name, output_file):
    data, tw, log_base, size_base = load(os.path.join(DATA, name + "_req"))

    with plt.rc_context(rcParams):
        plt.figure(figsize=(7, 6))
        img = plt.imshow(data, origin="lower", cmap="jet", aspect="auto")
        plt.colorbar(img)
        ax = plt.gca()
        ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x * tw / 3600:.0f}"))
        ax.yaxis.set_major_formatter(FuncFormatter(lambda y, _: f"{log_base ** y * size_base:.0f}"))
        plt.xlabel("Time (hour)")
        plt.ylabel("Request size (Byte)")
        plt.savefig(output_file, bbox_inches="tight")
        plt.close()
    print(f"Plot saved to: {output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default=os.path.join(HERE, "../../trace_heatmap"))
    args = parser.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    plot("cluster50.oracleGeneral.sample10.zst.sizeWindow_w2400", os.path.join(args.out_dir, "cluster50_w2400_size_heatmap_req.png"))
    plot("cluster2.oracleGeneral.sample10.zst.sizeWindow_w1500", os.path.join(args.out_dir, "cluster2_w1500_size_heatmap_req.png"))
