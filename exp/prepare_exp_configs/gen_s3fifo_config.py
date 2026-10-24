#!/usr/bin/env python3
"""
Configs for the eviction policy sweep (Fig 14): S3-FIFO, SIEVE and
Adaptive-Hits-Per-Slab. Each config copies a run in
exp/result/efficiency_result_processed.csv (checked field by field) with only the
eviction policy or the strategy changed. twitter_cluster12, twitter_cluster32 and
meta_memcache_2024_kv are left out.

    python3 gen_s3fifo_config.py --out ../work_dir_s3fifo
    python3 gen_s3fifo_config.py --out ../work_dir_sieve --allocator SIEVE --skip-twitter-wsr 0.1
    python3 gen_s3fifo_config.py --out ../work_dir_hpsa --strategies adaptive-hits-per-slab --skip-twitter-wsr 0.1
    python3 gen_s3fifo_config.py --out ../work_dir_hpsa --strategies adaptive-hits-per-slab --skip-twitter-wsr 0.1 --allocator SIEVE
    python3 gen_s3fifo_config.py --out ../work_dir_hpsa_stack --strategies adaptive-hits-per-slab --wsr 0.01 --allocator LRU
    (and the same with --allocator LRU2Q, TINYLFU)

Run the work dirs with exp/master/master.py (list them in work_dirs in
exp/configs.json), with the revision CacheLib (S3-FIFO, SIEVE,
Adaptive-Hits-Per-Slab) built at the cachebench paths in exp/util.py: 4 MB slabs
for Meta and Wikimedia, 1 MB slabs for Twitter. Then summarize:

    cd exp && python3 summarize_result.py --base-dirs work_dir_s3fifo work_dir_sieve work_dir_hpsa work_dir_hpsa_stack \\
        --output-file result/eviction_policy_sweep.csv

This writes result/eviction_policy_sweep_processed.csv, read by
plotting/plot_s3fifo_bar.py. The shipped file has 163 of the 192 S3-FIFO Twitter
10% runs.
"""

import argparse
import copy
import json
import math
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
EXP = os.path.dirname(HERE)
sys.path.insert(0, EXP)
from util import TRACE_FILE_PATH, WGET_PATH, dict_hash  # noqa: E402

BASE_CONFIG = os.path.join(EXP, "prepare_exp_configs", "base_config.json")
TRACE_INFO = os.path.join(os.path.dirname(EXP), "trace_info.csv")
SHIPPED = os.path.join(EXP, "result", "efficiency_result_processed.csv")

EXCLUDE = {"twitter_cluster12", "twitter_cluster32", "meta_memcache_2024_kv"}
S3FIFO_SPEED = 0.93   # S3-FIFO / LRU throughput, only used to order the run queue

# same as gen_{meta,cdn,twitter}_config.py
LRU = {"lru2qHotPct": 100, "lru2qColdPct": 0, "allocator": "SIMPLE2Q", "rebalanceOnRecordAccess": True}
TWOQ = {"lru2qHotPct": 30, "lru2qColdPct": 30, "allocator": "LRU2Q", "rebalanceOnRecordAccess": True,
        "countColdTailHitsOnly": True}
TINYLFU = {"allocator": "TINYLFU"}
S3FIFO = {"allocator": "S3FIFO"}
PAPER_POLICIES = {"LRU": LRU, "LRU2Q": TWOQ, "TINYLFU": TINYLFU}
ALLOCATORS = {"S3FIFO": S3FIFO, "SIEVE": {"allocator": "SIEVE"}, **PAPER_POLICIES}
wakeup = 50_000
cache_configs = {
    "marginal-hits-old": {"wakeUpRebalancerEveryXReqs": wakeup, "mhMovingAverageParam": 0.3},
    "marginal-hits-new": {
        "wakeUpRebalancerEveryXReqs": wakeup,
        "mhMovingAverageParam": 0.3,
        "mhOnlyUpdateHitIfRebalance": True,
        "minRequestsObserved": wakeup,
        "maxDecayInterval": wakeup,
        "mhMinDiff": 2,
        "mhMinDiffRatio": 0.00,
        "emrLow": 0.5,
        "emrHigh": 0.95,
        "thresholdAI": True,
        "thresholdAD": False,
        "thresholdMI": False,
        "thresholdMD": True,
    },
    "disabled": {"wakeUpRebalancerEveryXReqs": wakeup},
    "hits": {"rebalanceDiffRatio": 0.1, "wakeUpRebalancerEveryXReqs": wakeup},
    "tail-age": {"rebalanceDiffRatio": 0.25, "wakeUpRebalancerEveryXReqs": wakeup},
    "eviction-rate": {"rebalanceDiffRatio": 0.1, "wakeUpRebalancerEveryXReqs": wakeup},
    "adaptive-hits-per-slab": {"rebalanceDiffRatio": 0.1, "wakeUpRebalancerEveryXReqs": wakeup,
                               "hpsaSignal": "ewma", "hpsaGate": "adaptive", "hpsaHoldOff": False},
}
# strategies with no shipped rows are built from the rows of this one
DERIVED = {"adaptive-hits-per-slab": "hits"}
SWEEP_STRATEGIES = ["disabled", "tail-age", "eviction-rate", "hits"]
CSV_TO_CONFIG = {"marginal-hits": "marginal-hits-old", "marginal-hits-tuned": "marginal-hits-new"}


def mismatches(cfg, row, config_cols, trace_dir):
    """Config fields that disagree with the shipped row (a NaN cell = field absent)."""
    flat = {**cfg["cache_config"], **cfg["test_config"]}
    bad = []
    for k in config_cols:
        want, got = row[k], flat.get(k)
        if k == "traceFileName":
            want, got = want.split("/oracleReuse/")[1], got.split(trace_dir.rstrip("/") + "/")[1]
        elif k == "replayGeneratorConfig":
            got = str(got)
        if pd.isna(want) if not isinstance(want, str) else False:
            if got is not None:
                bad.append((k, "absent", got))
        elif got is None or (want != got if isinstance(want, str) else float(want) != float(got)):
            bad.append((k, want, got))
    return bad


def build(base, trace_info, strategy, wsr, alloc, trace_dir):
    """The body of the paper generators' inner loop."""
    slab_size = int(trace_info["slab_size"])
    slab_cnt = int(math.ceil(float(trace_info["wss"]) * wsr * 1024 / slab_size))
    headers = (7 * slab_cnt + slab_size * 1024 - 1) // (slab_size * 1024)
    c = copy.deepcopy(base)
    c["cache_config"]["rebalanceStrategy"] = strategy
    c["cache_config"]["cacheSizeMB"] = (slab_cnt + headers) * slab_size
    c["cache_config"]["maxAllocSize"] = slab_size * 1024 * 1024
    c["cache_config"].update(cache_configs[strategy])
    c["cache_config"].update(alloc)
    c["test_config"]["traceFileName"] = f"{trace_dir}/{trace_info['file_name']}"
    c["test_config"]["numOps"] = int(trace_info["number_of_requests"])
    return c, slab_cnt


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=os.path.join(EXP, "work_dir_s3fifo"),
                    help="sweep root to write run dirs into (default: exp/work_dir_s3fifo)")
    ap.add_argument("--trace-dir", default=TRACE_FILE_PATH,
                    help="trace folder (default: from exp/configs.json)")
    ap.add_argument("--traces", help="comma-separated trace names (default: all)")
    ap.add_argument("--strategies", help="comma-separated config strategy names (default: SWEEP_STRATEGIES)")
    ap.add_argument("--allocator", choices=sorted(ALLOCATORS), default="S3FIFO")
    ap.add_argument("--skip-twitter-wsr", type=float, action="append", default=[],
                    help="leave out Twitter cells at this wsr (repeatable), e.g. 0.1")
    ap.add_argument("--wsr", type=float, action="append", default=[],
                    help="only cells at this wsr (repeatable; default: all)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    with open(BASE_CONFIG) as f:
        base = json.load(f)
    info = pd.read_csv(TRACE_INFO).convert_dtypes()
    info = {r["trace_name"]: r for r in info.to_dict("records")}

    rows = pd.read_csv(SHIPPED)
    cols = rows.columns.tolist()
    config_cols = cols[cols.index("thresholdMD"):cols.index("repeatOpCount") + 1]
    src = a.allocator if a.allocator in PAPER_POLICIES else "LRU"
    rows = rows[rows.allocator == src].copy()
    rows["strategy"] = rows.rebalance_strategy.map(lambda s: CSV_TO_CONFIG.get(s, s))
    want = a.strategies.split(",") if a.strategies else SWEEP_STRATEGIES
    rows = pd.concat([rows[rows.strategy == DERIVED.get(s, s)].assign(source=DERIVED.get(s, s), strategy=s)
                      for s in want])
    excluded = rows[rows.trace_name.isin(EXCLUDE)]
    rows = rows[~rows.trace_name.isin(EXCLUDE)]
    if a.traces:
        rows = rows[rows.trace_name.isin(a.traces.split(","))]
    for w in a.skip_twitter_wsr:
        rows = rows[~(rows.trace_name.str.startswith("twitter_") & (rows.wsr == w))]
    if a.wsr:
        rows = rows[rows.wsr.round(6).isin([round(w, 6) for w in a.wsr])]

    new = existing = mismatched = 0
    for r in rows.itertuples(index=False):
        ti = info[r.trace_name]
        lru, slab_cnt = build(base, ti, r.source, r.wsr, PAPER_POLICIES[src], a.trace_dir)
        bad = mismatches(lru, r._asdict(), config_cols, a.trace_dir)
        if bad:
            print(f"MISMATCH {r.uuid} ({r.strategy}, wsr {r.wsr}): {bad}, skipped")
            mismatched += 1
            continue
        cfg, _ = build(base, ti, r.strategy, r.wsr, ALLOCATORS[a.allocator], a.trace_dir)
        uuid = f"{r.trace_name}-{dict_hash(cfg)}"
        meta = {
            "trace_name": r.trace_name,
            "uuid": uuid,
            "memory_requirement": cfg["cache_config"]["cacheSizeMB"] * 1.5,
            "cpu_requirement": 2.5,
            "download_path": f"{WGET_PATH}/{ti['download_path']}",
            "trace_file": cfg["test_config"]["traceFileName"],
            "slab_size": int(ti["slab_size"]),
            "purpose": "efficiency",
            "wsr": r.wsr,
            "slab_cnt": slab_cnt,
            "lru_uuid": r.uuid,
            "expected_hours": r.number_of_requests / r.throughput / 3600 / S3FIFO_SPEED,
        }
        meta.update({k: (v.item() if hasattr(v, "item") else v) for k, v in ti.items() if not pd.isna(v)})
        d = os.path.join(a.out, uuid)
        if os.path.exists(d):
            existing += 1
            continue
        new += 1
        if a.dry_run:
            continue
        os.makedirs(d)
        for name, obj in (("config.json", cfg), ("meta.json", meta)):
            with open(os.path.join(d, name + ".tmp"), "w") as f:
                json.dump(obj, f, indent=2)
            os.replace(os.path.join(d, name + ".tmp"), os.path.join(d, name))

    print(f"checked {len(config_cols)} config fields per row against the shipped CSV")
    print(f"{len(rows)} {src} rows -> {new} new, {existing} already present, {mismatched} mismatched"
          f"{' (dry run, nothing written)' if a.dry_run else ''}")
    print(f"excluded: {excluded.trace_name.nunique()} traces, {len(excluded)} rows "
          f"({', '.join(sorted(excluded.trace_name.unique()))})")


if __name__ == "__main__":
    main()
