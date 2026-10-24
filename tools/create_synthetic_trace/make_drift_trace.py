#!/usr/bin/env python3
"""Concatenate two static synthetic phases into one trace with an abrupt drift.

    python3 make_drift_trace.py --out <trace dir>/synth_drift_600.oracleGeneral.bin
    python3 make_drift_trace.py --out ... --disjoint-ids     # working-set swap

Configs for it: exp/prepare_exp_configs/gen_synth_config.py.
"""

import argparse
import json
import os
import struct
import sys

import numpy as np

REC = struct.Struct("<IQIq")

# The two phases of synth_dynamic_400 (tools/create_synthetic_trace/demo_config.json).
PHASE_A = [
    {"m": 1600000, "alpha": 0.25, "share": 1, "size": 214},
    {"m":  800000, "alpha": 0.85, "share": 1, "size": 470},
    {"m":  400000, "alpha": 0.25, "share": 1, "size": 982},
    {"m":  200000, "alpha": 0.85, "share": 1, "size": 2006},
    {"m":  100000, "alpha": 1.00, "share": 4, "size": 4054},
]
PHASE_B = [
    {"m": 1600000, "alpha": 0.25, "share": 1, "size": 214},
    {"m":  800000, "alpha": 0.85, "share": 1, "size": 470},
    {"m":  400000, "alpha": 0.25, "share": 4, "size": 982},
    {"m":  200000, "alpha": 0.85, "share": 1, "size": 2006},
    {"m":  100000, "alpha": 1.00, "share": 1, "size": 4054},
]

TIME_SPAN = 604800          # one week per phase, as in demo_config.json
REQUESTS_PER_PHASE = 80_000_000
CHUNK = 8_000_000           # divisible by both phases' share totals


def dist_map(m, alpha):
    """Zipf CDF over m objects, same construction as zip_gen.ZipfGenerator."""
    zeta = np.cumsum(np.power(np.arange(1, m + 1, dtype=np.float64), -alpha))
    return zeta / zeta[-1]


class Phase:
    """Same as zip_gen's MergedStaticGenerator, but draws each class in one batch."""

    def __init__(self, config, base_id):
        self.maps = []
        self.bases = []
        for c in config:
            self.maps.append(dist_map(c["m"], c["alpha"]))
            self.bases.append(base_id)
            base_id += c["m"]
        self.next_base_id = base_id
        self.sizes = np.array([c["size"] for c in config], dtype=np.uint32)
        # one cycle of the round-robin: share[0] of class 0, then share[1] of 1...
        self.pattern = np.concatenate(
            [np.full(c["share"], i, dtype=np.int8) for i, c in enumerate(config)])

    def draw(self, n):
        """(obj_ids, obj_sizes) for the next n requests of this phase."""
        if n % len(self.pattern):
            raise ValueError(f"{n} is not a multiple of the cycle length "
                             f"{len(self.pattern)}")
        cls = np.tile(self.pattern, n // len(self.pattern))
        ids = np.empty(n, dtype=np.uint64)
        for i, (dm, base) in enumerate(zip(self.maps, self.bases)):
            sel = cls == i
            k = int(sel.sum())
            if k:
                ids[sel] = np.searchsorted(dm, np.random.uniform(0, 1, k)) + base
        return ids, self.sizes[cls]


def write_phase(f, phase, n_requests, t_start, t_span, counts):
    written = 0
    while written < n_requests:
        n = min(CHUNK, n_requests - written)
        ids, sizes = phase.draw(n)
        # zip_gen's timestamps, shifted by t_start so the joined trace stays monotonic
        i = np.arange(written + 1, written + n + 1, dtype=np.int64)
        ts = (t_start + i * t_span // n_requests).astype(np.uint32)
        out = np.empty(n, dtype=[("t", "<u4"), ("o", "<u8"),
                                 ("s", "<u4"), ("v", "<i8")])
        out["t"], out["o"], out["s"], out["v"] = ts, ids, sizes, -2
        f.write(out.tobytes())
        for s, c in zip(*np.unique(sizes, return_counts=True)):
            counts[int(s)] = counts.get(int(s), 0) + int(c)
        written += n
        print(f"    {written/1e6:6.1f}M / {n_requests/1e6:.0f}M", end="\r",
              file=sys.stderr, flush=True)
    print(file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True)
    ap.add_argument("--requests-per-phase", type=int, default=REQUESTS_PER_PHASE)
    ap.add_argument("--disjoint-ids", action="store_true",
                    help="give phase B its own object IDs")
    ap.add_argument("--seed", type=int, default=202)
    args = ap.parse_args()

    if os.path.exists(args.out):
        sys.exit(f"{args.out} exists; remove it first")
    np.random.seed(args.seed)

    n = args.requests_per_phase
    a = Phase(PHASE_A, 0)
    b = Phase(PHASE_B, a.next_base_id if args.disjoint_ids else 0)

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    counts_a, counts_b = {}, {}
    print(f"phase A -> {args.out}", file=sys.stderr)
    with open(args.out, "wb") as f:
        write_phase(f, a, n, 0, TIME_SPAN, counts_a)
        print("phase B", file=sys.stderr)
        write_phase(f, b, n, TIME_SPAN, TIME_SPAN, counts_b)

    meta = {
        "requests_per_phase": n,
        "total_requests": 2 * n,
        "drift_at_request": n,
        "shared_object_ids": not args.disjoint_ids,
        "seed": args.seed,
        "time_span_per_phase": TIME_SPAN,
        "phase_a": PHASE_A,
        "phase_b": PHASE_B,
        "request_share_by_size_phase_a": counts_a,
        "request_share_by_size_phase_b": counts_b,
    }
    with open(args.out + ".meta.json", "w") as f:
        json.dump(meta, f, indent=2)

    size = os.path.getsize(args.out)
    print(f"\n{args.out}\n  {size/1e9:.2f} GB, {size//REC.size} records, "
          f"drift at request {n}")
    for label, c in (("A", counts_a), ("B", counts_b)):
        share = {k: f"{v/sum(c.values()):.1%}" for k, v in sorted(c.items())}
        print(f"  phase {label} request share by object size: {share}")


if __name__ == "__main__":
    main()
