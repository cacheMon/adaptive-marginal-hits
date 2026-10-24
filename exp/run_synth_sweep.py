#!/usr/bin/env python3
"""
Run cachebench on every run dir under one or more work dirs, largest cache first,
starting a run only when there is enough free memory for it.

    cp -r revision_configs/synth work_dir_synth
    python3 run_synth_sweep.py --work-dir work_dir_synth --binary <4mb cachebench> \\
        --binary-1mb <1mb cachebench> --shim <libmock_time.so>
    python3 run_synth_sweep.py --work-dir ... --dry-run   # print what would run
    python3 run_synth_sweep.py --work-dir ... --status    # done / running / failed / pending
    touch <first work dir>/STOP                           # start nothing new, exit when idle

Runs with useTraceTimer get libmock_time.so through LD_PRELOAD and MOCK_TIMER_LIB_PATH.
Runs are detached, so the script can be restarted at any time.
"""

import argparse
import hashlib
import json
import os
import socket
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from util import TRACE_FILE_PATH  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
SHIM = None   # --shim: libmock_time.so built from set_up_env/hook_time/libmock_time.cpp
TRACE_DIR = None   # --trace-dir


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def read(path):
    try:
        with open(path) as f:
            return f.read()
    except OSError:
        return None


def write(path, text):
    with open(path + ".tmp", "w") as f:
        f.write(text)
    os.replace(path + ".tmp", path)


def proc_start(pid):
    """Start time of a live process (field 22 of /proc/pid/stat), or None."""
    stat = read(f"/proc/{pid}/stat")
    return stat.rsplit(")", 1)[1].split()[19] if stat else None


def meminfo_gb():
    m = {}
    for line in read("/proc/meminfo").splitlines():
        k, v = line.split(":")
        m[k] = int(v.split()[0]) / 2**20
    return m["MemTotal"], m["MemAvailable"]


class Run:
    def __init__(self, d):
        self.d = d
        self.meta = json.load(open(os.path.join(d, "meta.json")))
        self.cfg = json.load(open(os.path.join(d, "config.json")))
        self.cache_gb = self.cfg["cache_config"]["cacheSizeMB"] / 1024
        self.book_gb = self.cache_gb * 1.02 + 0.5   # peak RSS ~ cache + 0.25 GB
        self.timer = bool(self.cfg["test_config"].get("useTraceTimer"))
        self.name = f"{os.path.basename(os.path.dirname(d))}/{os.path.basename(d)}"
        self.trace = os.path.join(TRACE_DIR, self.cfg["test_config"]["traceFileName"])

    def binary(self, binary_4mb, binary_1mb):
        return binary_1mb if int(self.meta.get("slab_size", 4)) == 1 else binary_4mb

    def state(self):
        if os.path.exists(os.path.join(self.d, "done.txt")):
            return "done"
        if os.path.exists(os.path.join(self.d, "failed.txt")):
            return "failed"
        pid = read(os.path.join(self.d, "pid.txt"))
        if pid:
            p, start = pid.split()[:2]
            if os.path.exists(os.path.join(self.d, "rc.txt")):
                return "exited"
            return "running" if proc_start(p) == start else "exited"
        return "pending"

    def launch(self, binary, progress_secs, round_tail_hits=False):
        d = self.d
        env = f"LD_PRELOAD={SHIM} MOCK_TIMER_LIB_PATH={SHIM} " if self.timer else ""
        if round_tail_hits:
            env += "CACHELIB_LOG_ROUND_TAIL_HITS=1 "
        cfg_path = os.path.join(d, "config.json")
        if not os.path.isabs(self.cfg["test_config"]["traceFileName"]):
            cfg = json.loads(json.dumps(self.cfg))
            cfg["test_config"]["traceFileName"] = self.trace
            cfg_path = os.path.join(d, "config_resolved.json")
            write(cfg_path, json.dumps(cfg, indent=2) + "\n")
        cmd = (f"cd {d} && env {env}{binary} --json_test_config {cfg_path} "
               f"--progress {progress_secs} --progress_stats_file {d}/progress_0.txt "
               f"--dump_result_json_file {d}/result_0.json > log_0.txt 2>&1; "
               f"echo $? > rc.tmp; mv rc.tmp rc.txt")
        bin_sha = sha256(binary)
        write(os.path.join(d, "binary.txt"), f"{binary}\n{bin_sha}\n")
        prov = {
            "host": socket.gethostname(),
            "binary": binary, "binary_sha256": bin_sha,
            "shim": SHIM, "shim_sha256": sha256(SHIM),
            "timer_mode": "trace" if self.timer else "real-clock",
            "LD_PRELOAD": SHIM if self.timer else None,
            "MOCK_TIMER_LIB_PATH": SHIM if self.timer else None,
            "LD_LIBRARY_PATH": os.environ.get("LD_LIBRARY_PATH"),
            "syncRebalance": self.cfg["cache_config"].get("syncRebalance"),
            "CACHELIB_LOG_ROUND_TAIL_HITS": "1" if round_tail_hits else None,
            "command": cmd,
            "start": time.strftime("%FT%T%z"),
        }
        write(os.path.join(d, "provenance.json"), json.dumps(prov, indent=2) + "\n")
        p = subprocess.Popen(["bash", "-c", cmd], start_new_session=True,
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
        start = None
        while start is None:
            start = proc_start(p.pid)
        write(os.path.join(d, "pid.txt"), f"{p.pid} {start} {time.time():.0f}\n")

    def finish(self):
        d = self.d
        rc = (read(os.path.join(d, "rc.txt")) or "none").strip()
        t0 = float(read(os.path.join(d, "pid.txt")).split()[2])
        t1 = os.path.getmtime(os.path.join(d, "rc.txt")) if rc != "none" else time.time()
        prov_path = os.path.join(d, "provenance.json")
        prov = json.load(open(prov_path))
        prov.update({"end": time.strftime("%FT%T%z", time.localtime(t1)), "rc": rc,
                     "elapsed_s": round(t1 - t0, 1)})
        write(prov_path, json.dumps(prov, indent=2) + "\n")
        if rc == "0" and os.path.exists(os.path.join(d, "result_0.json")):
            write(os.path.join(d, "done.txt"), f"ok {t1 - t0:.1f}s\n")
            return f"ok in {(t1 - t0) / 60:.1f} min"
        write(os.path.join(d, "failed.txt"), f"rc={rc} after {t1 - t0:.1f}s (see log_0.txt)\n")
        return f"FAILED rc={rc} after {(t1 - t0) / 60:.1f} min"


def load(work_dirs):
    runs = []
    for wd in work_dirs:
        wd = wd if os.path.isabs(wd) else os.path.join(HERE, wd)
        dirs = sorted(os.path.join(wd, n) for n in os.listdir(wd)
                      if os.path.exists(os.path.join(wd, n, "config.json")))
        if not dirs:
            sys.exit(f"no run directories under {wd}")
        rs = [Run(d) for d in dirs]
        runs += sorted(rs, key=lambda r: -r.cache_gb)
    return runs


def log(path, msg):
    line = f"{time.strftime('%F %T')} {msg}"
    print(line, flush=True)
    with open(path, "a") as f:
        f.write(line + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--work-dir", nargs="+", required=True, help="run first, in this order")
    ap.add_argument("--binary", help="cachebench, 4 MB slab build (required to run)")
    ap.add_argument("--binary-1mb",
                    help="cachebench, 1 MB slab build, for runs whose meta.json says slab_size == 1")
    ap.add_argument("--shim", help="libmock_time.so, the trace-timer shim (required to run)")
    ap.add_argument("--trace-dir", default=TRACE_FILE_PATH,
                    help="folder that relative traceFileName entries are resolved against "
                         "(default: local_trace_file_dir in exp/configs.json)")
    ap.add_argument("--jobs", type=int, default=os.cpu_count(), help="max concurrent runs (default: CPU count)")
    ap.add_argument("--reserve-gb", type=float, default=12,
                    help="MemTotal minus this is the budget for booked caches")
    ap.add_argument("--headroom-gb", type=float, default=20,
                    help="MemAvailable must exceed a run's cache by this much")
    ap.add_argument("--launch-gap", type=float, default=30,
                    help="seconds after any launch before a run with a cache of 4 GB or more "
                         "may start (smaller runs wait 2 s)")
    ap.add_argument("--progress-secs", type=int, default=300,
                    help="seconds between progress snapshots (trace seconds under the trace timer)")
    ap.add_argument("--log-round-tail-hits", action="store_true",
                    help="set CACHELIB_LOG_ROUND_TAIL_HITS, which makes cachebench log one "
                         "RoundTailHits line per class per rebalancer wake-up (needed by the "
                         "drift runs: tools/trace_analysis/extract_drift_timeline.py; logging only)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--status", action="store_true")
    args = ap.parse_args()
    global SHIM, TRACE_DIR
    SHIM, TRACE_DIR = args.shim, args.trace_dir

    runs = load(args.work_dir)
    first = args.work_dir[0] if os.path.isabs(args.work_dir[0]) else os.path.join(HERE, args.work_dir[0])
    stop_file, log_file = os.path.join(first, "STOP"), os.path.join(first, "runner.log")

    if args.status:
        by = {}
        for r in runs:
            by.setdefault(r.state(), []).append(r)
        for s in ("done", "running", "exited", "failed", "pending"):
            print(f"{s:8} {len(by.get(s, []))}")
        for r in by.get("running", []) + by.get("failed", []):
            print(f"  {r.state():8} {r.name}")
        return 0

    if not args.dry_run:
        need = [("--binary", args.binary), ("--shim", SHIM)]
        if any(int(r.meta.get("slab_size", 4)) == 1 for r in runs):
            need.append(("--binary-1mb", args.binary_1mb))
        for name, p in need:
            if not p or not os.path.exists(p):
                sys.exit(f"{name}: missing {p}")
    missing = sorted({r.trace for r in runs if not os.path.exists(r.trace)})
    for t in missing:
        print(f"trace not found: {t}")
    if missing and not args.dry_run:
        sys.exit(1)

    if args.dry_run:
        for i, r in enumerate(runs, 1):
            print(f"{i:3} {r.cache_gb:7.2f} GB  "
                  f"{'1MB' if int(r.meta.get('slab_size', 4)) == 1 else '4MB'}  "
                  f"timer={'trace' if r.timer else 'real'}  "
                  f"sync={r.cfg['cache_config'].get('syncRebalance')}  {r.state():8} {r.name}")
        return 0

    total_gb = meminfo_gb()[0]
    budget = total_gb - args.reserve_gb
    log(log_file, f"start: {len(runs)} runs, jobs {args.jobs}, "
                  f"cache budget {budget:.0f} GB of {total_gb:.0f}")
    last_launch = 0.0
    failed = 0
    while True:
        try:
            while os.waitpid(-1, os.WNOHANG)[0]:   # reap our own wrappers
                pass
        except ChildProcessError:
            pass
        states = {r.d: r.state() for r in runs}
        for r in runs:
            if states[r.d] == "exited":
                status = r.finish()
                failed += "FAILED" in status
                log(log_file, f"END   {r.name}: {status}")
                states[r.d] = r.state()
        active = [r for r in runs if states[r.d] == "running"]
        pending = [r for r in runs if states[r.d] == "pending"]
        stopping = os.path.exists(stop_file)
        if not active and (stopping or not pending):
            log(log_file, f"{'STOP file' if stopping else 'queue empty'}: exiting, "
                          f"{failed} failed this session")
            return 1 if failed else 0

        if not stopping and len(active) < args.jobs:
            booked = sum(r.book_gb for r in active)
            avail = meminfo_gb()[1]
            since = time.time() - last_launch
            for r in pending:
                if since < (args.launch_gap if r.cache_gb >= 4 else 2):
                    continue
                if booked + r.book_gb <= budget and avail >= r.cache_gb + args.headroom_gb:
                    r.launch(r.binary(args.binary, args.binary_1mb), args.progress_secs,
                             args.log_round_tail_hits)
                    last_launch = time.time()
                    log(log_file, f"START {r.name} ({r.cache_gb:.2f} GB, booked "
                                  f"{booked + r.book_gb:.0f}/{budget:.0f} GB, avail {avail:.0f} GB)")
                    break
        time.sleep(5)


if __name__ == "__main__":
    sys.exit(main())
