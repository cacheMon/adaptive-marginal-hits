#!/usr/bin/env python3
"""
Configs for the EMR window sweep (Fig 13): Adaptive-Marginal-Hits on
meta_202210_kv (LRU) with emrWindowClassMultiplier 1, 2, 4 and 8. Everything
else, including the cache sizes, is the same as in the published sensitivity runs.

python3 gen_emr_window_config.py      # writes exp/work_dir_emr_window/

Then run it with exp/run_synth_sweep.py and summarize it with exp/summarize_emr_window.py.
"""

import copy
import json
import math
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(HERE))
from util import dict_hash  # noqa: E402

TRACE_NAME = "meta_202210_kv"
# relative to the trace folder; run_synth_sweep.py resolves it with --trace-dir
TRACE_FILE = "metaKV/202210_kv_traces_all_sort.csv.oracleGeneral.zst"
WORK_DIR = os.path.join(os.path.dirname(HERE), "work_dir_emr_window")
TRACE_INFO = os.path.join(os.path.dirname(os.path.dirname(HERE)),
                          "trace_info.csv")

WORKING_SET_RATIOS = [0.004, 0.01, 0.02, 0.04, 0.1, 0.2, 0.4]
WINDOW_MULTIPLIERS = [1.0, 2.0, 4.0, 8.0]

ALLOCATOR = {
    "lru2qHotPct": 100,
    "lru2qColdPct": 0,
    "allocator": "SIMPLE2Q",
    "rebalanceOnRecordAccess": True,
}

REBALANCE_INTERVAL = 50_000
STRATEGY = {
    "rebalanceStrategy": "marginal-hits-new",
    "wakeUpRebalancerEveryXReqs": REBALANCE_INTERVAL,
    "mhMovingAverageParam": 0.3,
    "mhOnlyUpdateHitIfRebalance": True,
    "minRequestsObserved": REBALANCE_INTERVAL,
    "maxDecayInterval": REBALANCE_INTERVAL,
    "mhMinDiff": 2,
    "mhMinDiffRatio": 0.00,
    "emrLow": 0.5,
    "emrHigh": 0.95,
    "thresholdAI": True,
    "thresholdAD": False,
    "thresholdMI": False,
    "thresholdMD": True,
}


def main():
    info = pd.read_csv(TRACE_INFO)
    info = info[info.trace_name == TRACE_NAME].iloc[0]
    slab_size = int(info["slab_size"])          # MB
    n_requests = int(info["number_of_requests"])
    n_classes = int(info["num_slab_classes"])

    with open(os.path.join(HERE, "base_config.json")) as f:
        base = json.load(f)

    os.makedirs(WORK_DIR, exist_ok=True)
    made = 0
    for wsr in WORKING_SET_RATIOS:
        # same cache sizes as gen_meta_config.py
        slab_cnt = int(math.ceil(float(info["wss"]) * wsr * 1024 / slab_size))
        headers = (7 * slab_cnt + slab_size * 1024 - 1) // (slab_size * 1024)
        cache_size_mb = (slab_cnt + headers) * slab_size

        for mult in WINDOW_MULTIPLIERS:
            cfg = copy.deepcopy(base)
            cfg["cache_config"].update(STRATEGY)
            cfg["cache_config"].update(ALLOCATOR)
            cfg["cache_config"]["cacheSizeMB"] = cache_size_mb
            cfg["cache_config"]["maxAllocSize"] = slab_size * 1024 * 1024
            cfg["cache_config"]["emrWindowClassMultiplier"] = mult
            cfg["test_config"]["traceFileName"] = TRACE_FILE
            cfg["test_config"]["numOps"] = n_requests

            uuid = f"{TRACE_NAME}-{dict_hash(cfg)}"
            meta = {
                "trace_name": TRACE_NAME,
                "uuid": uuid,
                "wsr": wsr,
                "slab_cnt": slab_cnt,
                "slab_size": slab_size,
                "cache_size_mb": cache_size_mb,
                "emr_window_class_multiplier": mult,
                "allocator": "LRU",
                "rebalance_strategy": "marginal-hits-tuned",
                "monitor_interval": REBALANCE_INTERVAL,
                "number_of_requests": n_requests,
                "num_slab_classes": n_classes,
                "memory_requirement_mb": cache_size_mb * 1.5,
                "label": f"{int(mult)}AC  wsr={wsr}",
            }

            subdir = os.path.join(WORK_DIR, f"mult{int(mult)}-wsr{wsr}-{uuid[-8:]}")
            os.makedirs(subdir, exist_ok=True)
            with open(os.path.join(subdir, "config.json"), "w") as f:
                json.dump(cfg, f, indent=2)
            with open(os.path.join(subdir, "meta.json"), "w") as f:
                json.dump(meta, f, indent=2)
            made += 1

    print(f"{made} run directories under {WORK_DIR}")
    total_gb = sum(json.load(open(os.path.join(WORK_DIR, d, "meta.json")))
                   ["cache_size_mb"] for d in os.listdir(WORK_DIR)) / 1024
    print(f"sum of cache sizes: {total_gb:.1f} GiB "
          f"(the scheduler runs a subset at a time)")


if __name__ == "__main__":
    main()
