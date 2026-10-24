#!/usr/bin/env python3
"""
Configs for the synthetic-trace sweep behind Figs 4 and 5: every strategy on
synth_static_202 with 32 to 256 slabs of 4 MB. The drift runs of Fig 6 use the same
configs on synth_drift_600 (from tools/create_synthetic_trace/make_drift_trace.py).

python3 gen_synth_config.py --trace synth_static_202.oracleGeneral.bin --work-dir ../work_dir_synth
python3 gen_synth_config.py --trace synth_drift_600.oracleGeneral.bin --work-dir ../work_dir_drift \\
    --strategies marginal-hits-old marginal-hits-new --num-ops 160000000

Then run them with exp/run_synth_sweep.py.
"""

import argparse
import copy
import hashlib
import json
import os

SLAB_MB = 4

TRACE_REQUESTS = 80_000_000

STRATEGIES = {
    "disabled": "Disabled",
    "tail-age": "Tail-Age",
    "eviction-rate": "Eviction-Rate",
    "hits": "Hits-Per-Slab",
    "marginal-hits-old": "Marginal-Hits",
    "marginal-hits-new": "Adaptive-Marginal-Hits",
}

WAKEUP = 50_000

# same as gen_meta_config.py
AMH_PARAMS = {
    "mhMovingAverageParam": 0.3,
    "mhOnlyUpdateHitIfRebalance": True,
    "minRequestsObserved": WAKEUP,
    "maxDecayInterval": WAKEUP,
    "mhMinDiff": 2,          # theta_0
    "mhMinDiffRatio": 0.00,
    "emrLow": 0.5,           # EMR_min
    "emrHigh": 0.95,         # EMR_max
    "thresholdAI": True,
    "thresholdAD": False,
    "thresholdMI": False,
    "thresholdMD": True,
    "thresholdAIADStep": 2,  # delta_theta
}

MH_PARAMS = {
    "mhMovingAverageParam": 0.3,
}

HEURISTIC_PARAMS = {
    "hits": {"rebalanceDiffRatio": 0.1},
    "tail-age": {"rebalanceDiffRatio": 0.25},
    "eviction-rate": {"rebalanceDiffRatio": 0.1},
}

BASE = {
    "cache_config": {
        "moveOnSlabRelease": False,
        "lruRefreshSec": 0,
        "poolResizeIntervalSec": 0,
        "poolRebalanceIntervalSec": 1,
        "syncRebalance": True,
        "allocSizes": [256, 512, 1024, 2048, 4096],
        "maxAllocSize": SLAB_MB * 1024 * 1024,
        "wakeUpRebalancerEveryXReqs": WAKEUP,
        "lru2qHotPct": 100,
        "lru2qColdPct": 0,
        "allocator": "SIMPLE2Q",
        "rebalanceOnRecordAccess": True,
        "enableTailHitsTracking": True,
    },
    "test_config": {
        "generator": "oracle-general-replay",
        "replayGeneratorConfig": {"ampFactor": 1},
        "useTraceTimer": True,
        "repeatTraceReplay": False,
        "repeatOpCount": True,
        "onlySetIfMiss": False,
        "enableLookaside": True,
        "timestampFactor": 1,
        "numThreads": 1,
        "ignoreLargeReq": True,
        "prepopulateCache": True,
        "zstdTrace": True,
        "compressed": False,
    },
}


def build(trace, slabs, strategy, num_ops):
    cfg = copy.deepcopy(BASE)
    cc, tc = cfg["cache_config"], cfg["test_config"]

    # slab headers, as in the other generators
    headers = (7 * slabs + SLAB_MB * 1024 * 1024 - 1) // (SLAB_MB * 1024 * 1024)
    cc["cacheSizeMB"] = (slabs + headers) * SLAB_MB
    cc["rebalanceStrategy"] = strategy
    if strategy == "marginal-hits-new":
        cc.update(AMH_PARAMS)
    elif strategy == "marginal-hits-old":
        cc.update(MH_PARAMS)
    elif strategy in HEURISTIC_PARAMS:
        cc.update(HEURISTIC_PARAMS[strategy])

    tc["traceFileName"] = trace
    tc["numOps"] = num_ops
    return cfg


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--trace", required=True)
    ap.add_argument("--work-dir", required=True)
    ap.add_argument("--slabs", type=int, nargs="+", default=[32, 64, 128, 256],
                    help="cache sizes in slabs")
    ap.add_argument("--strategies", nargs="+", default=list(STRATEGIES),
                    choices=list(STRATEGIES))
    ap.add_argument("--num-ops", type=int, default=TRACE_REQUESTS,
                    help="requests to replay (default: the whole trace)")
    args = ap.parse_args()

    os.makedirs(args.work_dir, exist_ok=True)
    name = os.path.basename(args.trace).split(".")[0]

    n = 0
    for slabs in args.slabs:
        for strategy in args.strategies:
            cfg = build(args.trace, slabs, strategy, args.num_ops)
            tag = hashlib.md5(
                json.dumps(cfg, sort_keys=True).encode()).hexdigest()
            d = os.path.join(args.work_dir, f"{name}-{slabs}slabs-{strategy}-{tag}")
            os.makedirs(d, exist_ok=True)
            with open(os.path.join(d, "config.json"), "w") as f:
                json.dump(cfg, f, indent=2)
            with open(os.path.join(d, "meta.json"), "w") as f:
                json.dump({"trace": name, "slabs": slabs, "strategy": strategy,
                           "strategy_label": STRATEGIES[strategy],
                           "slab_size_mb": SLAB_MB,
                           "cache_size_mb": cfg["cache_config"]["cacheSizeMB"]},
                          f, indent=2)
            n += 1
    print(f"wrote {n} configs "
          f"({len(args.slabs)} cache sizes x {len(args.strategies)} strategies) "
          f"to {args.work_dir}")


if __name__ == "__main__":
    main()
