#!/usr/bin/env python3
"""
Summarize the EMR window runs (Fig 13) into result/emr_window_result_processed.csv,
which plotting/plot_sensitivity_six.py reads. The columns are those of
result/sensitivity_result_processed.csv.

    python3 summarize_emr_window.py [--work-dir work_dir_emr_window] [--out CSV]
"""

import argparse
import json
import os

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))


def summarize(run_dir, base_dir):
    meta = json.load(open(os.path.join(run_dir, "meta.json")))
    cfg = json.load(open(os.path.join(run_dir, "config.json")))["cache_config"]
    res = json.load(open(os.path.join(run_dir, "result_0.json")))
    moved = res.get("rebalancerNumRebalancedSlabs")
    return {
        "trace_name": meta["trace_name"],
        "number_of_requests": meta["number_of_requests"],
        "wsr": meta["wsr"],
        "slab_size": meta["slab_size"],
        "slab_cnt": meta["slab_cnt"],
        "mhMinDiff": cfg["mhMinDiff"],
        "rebalance_strategy": meta["rebalance_strategy"],
        "allocator": meta["allocator"],
        "rebalanced_slabs": moved,
        "miss_ratio": res["getMissCnt"] / res["getCnt"],
        "n_rebalanced_slabs": moved,
        "monitor_interval": meta["monitor_interval"],
        "n_alloc_failures": res.get("allocFailures"),
        "uuid": meta["uuid"],
        "mhMovingAverageParam": cfg["mhMovingAverageParam"],
        "thresholdAIADStep": cfg.get("thresholdAIADStep", 2),
        "emrLow": cfg["emrLow"],
        "emrHigh": cfg["emrHigh"],
        "base_dir": base_dir,
        "emrWindowClassMultiplier": cfg["emrWindowClassMultiplier"],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--work-dir", default=os.path.join(HERE, "work_dir_emr_window"))
    parser.add_argument("--out", default=os.path.join(HERE, "result", "emr_window_result_processed.csv"))
    args = parser.parse_args()

    base_dir = os.path.basename(os.path.normpath(args.work_dir))
    rows = []
    for name in sorted(os.listdir(args.work_dir)):
        run_dir = os.path.join(args.work_dir, name)
        if os.path.exists(os.path.join(run_dir, "done.txt")):
            rows.append(summarize(run_dir, base_dir))
    rows.sort(key=lambda r: (r["emrWindowClassMultiplier"], r["wsr"]))
    pd.DataFrame(rows).to_csv(args.out, index=False)
    print(f"{len(rows)} runs -> {args.out}")
