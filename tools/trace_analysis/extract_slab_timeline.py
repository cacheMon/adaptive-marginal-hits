"""
Collect the per-class slab counts over time from the cachebench progress files
(runs started with --progress_stats_file) of every run in a work dir into one CSV.

python3 extract_slab_timeline.py <work_dir> [-o out.csv.gz]
"""

import argparse
import csv
import gzip
import json
import os
import re

LINE = re.compile(
    r"AC_Miss_rate:\s*pid:\s*(\d+),cid:\s*(\d+),allocSize:\s*(\d+),Gets:\s*(\d+),"
    r"missRatio:\s*([\d.]+)%,totalSlabs:\s*(\d+)"
    r"(?:,acTailAge:\s*(\d+))?(?:,acTailHits:\s*(\d+))?"
)

STRATEGY_LABELS = {
    "disabled": "Disabled",
    "hits": "Hits-Per-Slab",
    "tail-age": "Tail-Age",
    "eviction-rate": "Eviction-Rate",
    "lama": "LAMA",
    "marginal-hits-old": "Marginal-Hits",
    "marginal-hits-new": "Adaptive-Marginal-Hits",
}

FIELDS = ["trace", "cache_size_mb", "slabs", "allocator", "strategy",
          "strategy_label", "snapshot", "progress", "pid", "cid", "alloc_size",
          "gets", "miss_ratio_pct", "total_slabs", "tail_age", "tail_hits"]


def read_snapshots(path):
    snaps, cur, seen = [], [], set()
    with open(path, errors="ignore") as f:
        for line in f:
            m = LINE.search(line)
            if not m:
                continue
            # snapshots are not separated, a new one starts when a cid repeats
            cid = int(m.group(2))
            if cid in seen:
                snaps.append(cur)
                cur, seen = [], set()
            seen.add(cid)
            cur.append(m.groups())
    if cur:
        snaps.append(cur)
    return snaps


def read_run(run_dir):
    progress = sorted(f for f in os.listdir(run_dir) if f.startswith("progress_") and f.endswith(".txt"))
    if not progress or not os.path.exists(os.path.join(run_dir, "config.json")):
        return []
    snaps = read_snapshots(os.path.join(run_dir, progress[0]))
    if not snaps:
        return []

    cfg = json.load(open(os.path.join(run_dir, "config.json")))
    cache, test = cfg.get("cache_config", {}), cfg.get("test_config", {})
    meta_path = os.path.join(run_dir, "meta.json")
    meta = json.load(open(meta_path)) if os.path.exists(meta_path) else {}
    strategy = cache.get("rebalanceStrategy", "")
    base = {
        "trace": os.path.basename(test.get("traceFileName", "")).split(".")[0],
        "cache_size_mb": cache.get("cacheSizeMB", ""),
        "slabs": meta.get("slabs", ""),
        "allocator": cache.get("allocator", ""),
        "strategy": strategy,
        "strategy_label": STRATEGY_LABELS.get(strategy, strategy),
    }

    rows = []
    last = len(snaps) - 1
    for i, snap in enumerate(snaps):
        progress = i / last if last else 0.0
        for pid, cid, alloc, gets, mr, slabs, tail_age, tail_hits in snap:
            rows.append({**base,
                         "snapshot": i,
                         "progress": f"{progress:.6f}",
                         "pid": int(pid),
                         "cid": int(cid),
                         "alloc_size": int(alloc),
                         "gets": int(gets),
                         "miss_ratio_pct": float(mr),
                         "total_slabs": int(slabs),
                         "tail_age": int(tail_age or 0),
                         "tail_hits": int(tail_hits or 0)})
    return rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("work_dir")
    parser.add_argument("-o", "--output", default="slab_timeline.csv.gz")
    args = parser.parse_args()

    rows = []
    for name in sorted(os.listdir(args.work_dir)):
        run_dir = os.path.join(args.work_dir, name)
        if os.path.isdir(run_dir):
            rows += read_run(run_dir)

    opener = gzip.open if args.output.endswith(".gz") else open
    with opener(args.output, "wt", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} rows -> {args.output}")
