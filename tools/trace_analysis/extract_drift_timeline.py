#!/usr/bin/env python3
"""
Collect the drift runs (Fig 6, run with CACHELIB_LOG_ROUND_TAIL_HITS=1) into one
CSV: slabs and hits per class and the threshold theta for every rebalancer round.
Rounds are mapped to requests with <trace>.meta.json from make_drift_trace.py.

python3 extract_drift_timeline.py <work_dir> [-o out.csv.gz] [--trace-dir DIR]
"""
import argparse
import json
import os
import re
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_OUT = os.path.join(HERE, "..", "..", "exp", "result", "drift_timeline.csv.gz")
STRATEGIES = ("marginal-hits-old", "marginal-hits-new")
sys.path.insert(0, os.path.join(HERE, "..", "..", "exp"))
from util import TRACE_FILE_PATH  # noqa: E402

ROUND_LINE = re.compile(
    r"RoundTailHits:\s*pid:\s*(?P<pid>\d+),round:\s*(?P<round>\d+),"
    r"cid:\s*(?P<cid>\d+),allocSize:\s*(?P<alloc>\d+),"
    r"slabs:\s*(?P<slabs>\d+),tailHits:\s*(?P<tail_hits>\d+),hits:\s*(?P<hits>\d+)")
THETA_LINE = re.compile(
    r"AMH_Threshold:\s*pid:\s*\d+,round:\s*(?P<round>\d+),"
    r"thetaBefore:\s*(?P<thetaBefore>[-\d.]+),thetaAfter:\s*(?P<thetaAfter>[-\d.]+),"
    r"emr:\s*(?P<emr>[-\d.]+)")


def read_run(d):
    """(per-round per-class frame, theta frame or None, config) for one run."""
    cfg = json.load(open(os.path.join(d, "config.json")))
    rounds, thetas = [], []
    with open(os.path.join(d, "log_0.txt"), errors="ignore") as f:
        for line in f:
            m = ROUND_LINE.search(line)
            if m:
                rounds.append({k: int(v) for k, v in m.groupdict().items()})
                continue
            m = THETA_LINE.search(line)
            if m:
                thetas.append({k: float(v) for k, v in m.groupdict().items()})
    interval = cfg["cache_config"]["wakeUpRebalancerEveryXReqs"]
    df = pd.DataFrame(rounds)
    df["mreq"] = df["round"] * interval / 1e6
    df = df.sort_values(["cid", "round"])
    df["tail_delta"] = df.groupby("cid")["tail_hits"].diff()
    df = df[df["tail_delta"].notna()].copy()
    th = pd.DataFrame(thetas) if thetas else None
    if th is not None:
        th["mreq"] = th["round"] * interval / 1e6
    return df, th, cfg


def detect_drift(df, cls=1024):
    """x position (M requests) of the round where the request mix flips."""
    h = df.pivot_table(index="round", columns="alloc", values="hits").sort_index().diff()
    share = (h[cls] / h.sum(axis=1)).dropna()
    n = len(share)
    a, b = share.iloc[:n // 4].median(), share.iloc[-n // 4:].median()
    rnd = share[share > (a + b) / 2].index[0]
    return float(df.loc[df["round"] == rnd, "mreq"].iloc[0])


def to_requests(df, th, cfg, trace_dir):
    """Map the round-based x (mreq) onto millions of requests into the trace."""
    meta = json.load(open(os.path.join(trace_dir, cfg["test_config"]["traceFileName"]) + ".meta.json"))
    shift_at = meta["drift_at_request"] / 1e6
    total = meta["total_requests"] / 1e6
    s, e = detect_drift(df), df["mreq"].max()
    scale = (total - shift_at) / (e - s)
    offset = shift_at - s * scale
    fix = lambda f: None if f is None else f.assign(mreq=offset + scale * f["mreq"])
    return fix(df), fix(th)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("work_dir")
    ap.add_argument("-o", "--out", default=DEFAULT_OUT)
    ap.add_argument("--trace-dir", default=TRACE_FILE_PATH,
                    help="folder with synth_drift_600 and its .meta.json")
    args = ap.parse_args()

    parts = []
    for name in sorted(os.listdir(args.work_dir)):
        d = os.path.join(args.work_dir, name)
        mp = os.path.join(d, "meta.json")
        if not os.path.isfile(mp) or not os.path.isfile(os.path.join(d, "log_0.txt")):
            continue
        meta = json.load(open(mp))
        if meta.get("strategy") not in STRATEGIES:
            continue
        df, th, cfg = read_run(d)
        df, th = to_requests(df, th, cfg, args.trace_dir)
        key = dict(strategy=meta["strategy"], cache_slabs=meta["slabs"],
                   wakeup=cfg["cache_config"]["wakeUpRebalancerEveryXReqs"])
        parts.append(df[["round", "mreq", "alloc", "slabs", "hits"]].assign(**key, series="class"))
        if th is not None:
            parts.append(th[["round", "mreq", "thetaAfter"]].assign(**key, series="theta"))
        print(f"  {name}: {len(df)} class rows, {0 if th is None else len(th)} theta rows")

    cols = ["strategy", "cache_slabs", "wakeup", "series", "round", "mreq", "alloc", "slabs",
            "hits", "thetaAfter"]
    out = pd.concat(parts, ignore_index=True)[cols]
    for c in ("alloc", "slabs", "hits"):
        out[c] = out[c].astype("Int64")
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    out.to_csv(args.out, index=False)
    print(f"wrote {args.out}: {len(out)} rows")


if __name__ == "__main__":
    main()
