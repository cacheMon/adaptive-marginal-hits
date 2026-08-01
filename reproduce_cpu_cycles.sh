#!/usr/bin/env bash
#
# reproduce_cpu_cycles.sh — run the CPU-cycle overhead experiment (paper Fig 11)
# on ONE machine, for ONE trace, and check the result against the shipped numbers.
#
# It measures how many CPU cycles the slab rebalancer burns relative to request
# serving. The headline metric is the dimensionless ratio
#     rebalance_cycle_pct = pool_rebalancer_cycles / serving_cycles
# which is a property of the algorithm (both counts are cycles on the same CPU),
# so it should line up with the paper even on different hardware — unlike the
# absolute cycle counts.
#
# Requirements: the benchmark-tx CacheLib build and a working perf_event_open
# (the binary reads PERF_COUNT_HW_CPU_CYCLES per thread).
#
# Usage:
#   bash reproduce_cpu_cycles.sh --smoke              # LRU, wsr 0.01, capped numOps, 1 repeat
#   bash reproduce_cpu_cycles.sh                      # fuller run (slow: ~45 min per config)
#
# Options:
#   --smoke                       small numOps + few strategies + 1 repeat (recommended first)
#   --numops N                    ops per run in smoke mode              (default: 100000000)
#   --wsr "0.01"                  working-set ratio(s) to keep in smoke  (default: 0.01)
#   --strategies "a b c"          rebalance strategies to run
#                                 (default: disabled hits marginal-hits-old marginal-hits-new)
#   --repeat R                    repeats per config                     (default: 1 smoke / 3 full)
#   --turbo-off                   also try to disable turbo (needs msr-tools; best-effort)
#
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${PYTHON:-python3}"
OVH="$REPO_DIR/overhead"

SMOKE=0; NUMOPS=100000000; SMOKE_WSRS="0.01"; REPEAT=""; TURBO_OFF=0
STRATEGIES="disabled hits marginal-hits-old marginal-hits-new"
while [ $# -gt 0 ]; do
  case "$1" in
    --smoke)      SMOKE=1; shift ;;
    --numops)     NUMOPS="$2"; shift 2 ;;
    --wsr)        SMOKE_WSRS="$2"; shift 2 ;;
    --strategies) STRATEGIES="$2"; shift 2 ;;
    --repeat)     REPEAT="$2"; shift 2 ;;
    --turbo-off)  TURBO_OFF=1; shift ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done
[ -n "$REPEAT" ] || { [ "$SMOKE" = 1 ] && REPEAT=1 || REPEAT=3; }

USER_NAME="$(cat "$REPO_DIR/hosts/username.txt" | tr -d '[:space:]')"
BIN="/users/$USER_NAME/cachelib_tx/opt/cachelib/bin/cachebench"
TRACE_DIR="${TRACE_DIR:-$($PYTHON -c "import json;print(json.load(open('$REPO_DIR/exp/configs.json'))['local_trace_file_dir'])")}"
WORK_DIR="$OVH/work_dir_cycles"

echo "Experiment : CPU-cycle overhead (Fig 11)"
echo "Binary     : $BIN"
echo "Traces     : $TRACE_DIR"
[ "$SMOKE" = 1 ] && echo "Mode       : SMOKE (numOps=$NUMOPS, wsr={$SMOKE_WSRS}, repeat=$REPEAT, strategies: $STRATEGIES)" \
                 || echo "Mode       : FULL (repeat=$REPEAT)"
echo

if [ ! -x "$BIN" ]; then
  echo "ERROR: benchmark-tx cachebench not found at:" >&2
  echo "    $BIN" >&2
  echo "Build it first:  bash set_up_env/build_cachelib.sh --variant tx" >&2
  exit 1
fi

# --- perf events are mandatory (binary uses perf_event_open) --------------
echo "[0/5] Enabling perf events (perf_event_paranoid=1) ..."
sudo sh -c 'echo 1 >/proc/sys/kernel/perf_event_paranoid' || {
  echo "ERROR: could not set perf_event_paranoid; perf_event_open will fail." >&2; exit 1; }
if [ "$TURBO_OFF" = 1 ]; then
  echo "       Trying to disable turbo (best-effort) ..."
  ( cd "$OVH" && sudo ./disable_turbo.sh disable ) 2>/dev/null \
    && echo "       turbo disabled (re-enable later: sudo overhead/disable_turbo.sh enable)" \
    || echo "       (turbo control unavailable here — cycle ratios are still valid, just slightly noisier)"
fi

# --- 1. point overhead/configs.json at our tx binary + trace dir ---------
echo "[1/5] Writing overhead/configs.json ..."
"$PYTHON" - "$OVH" "$BIN" "$TRACE_DIR" <<'PY'
import json, os, sys
ovh, binp, trace_dir = sys.argv[1:4]
json.dump({"cachelib_path": binp, "trace_file_path": trace_dir},
          open(os.path.join(ovh, "configs.json"), "w"), indent=4)
print("      cachelib_path + trace_file_path set")
PY

# --- 2. generate configs -------------------------------------------------
echo "[2/5] Generating configs (prepare_configs_cycle.py) ..."
( cd "$OVH/gen_confs" && "$PYTHON" prepare_configs_cycle.py >/dev/null )
echo "      $(find "$WORK_DIR" -maxdepth 1 -mindepth 1 -type d | wc -l) config dirs in overhead/work_dir_cycles"

# --- 3. smoke prune: LRU only, chosen wsr/strategies, cap numOps, read .zst
if [ "$SMOKE" = 1 ]; then
  echo "[3/5] Pruning to smoke subset ..."
  WSRS="$SMOKE_WSRS" NUMOPS="$NUMOPS" STRATS="$STRATEGIES" "$PYTHON" - "$WORK_DIR" <<'PY'
import json, os, shutil, sys
work = sys.argv[1]
keep_wsrs = set(float(x) for x in os.environ["WSRS"].split())
keep_strats = set(os.environ["STRATS"].split())
numops = int(os.environ["NUMOPS"])
kept = 0
for d in sorted(os.listdir(work)):
    p = os.path.join(work, d)
    if not os.path.isdir(p): continue
    try:
        meta = json.load(open(os.path.join(p, "meta.json")))
        cfg  = json.load(open(os.path.join(p, "config.json")))
    except FileNotFoundError:
        shutil.rmtree(p); continue
    cc = cfg["cache_config"]
    if (float(meta.get("wsr", -1)) not in keep_wsrs
            or cc.get("allocator") != "SIMPLE2Q"
            or cc.get("rebalanceStrategy") not in keep_strats):
        shutil.rmtree(p); continue
    cfg["test_config"]["numOps"] = numops
    cfg["test_config"]["compressed"] = True   # read the existing .zst directly (per-thread cycles unaffected)
    json.dump(cfg, open(os.path.join(p, "config.json"), "w"), indent=2)
    kept += 1
print(f"      kept {kept} jobs (LRU, wsr in {sorted(keep_wsrs)}, strategies {sorted(keep_strats)})")
PY
else
  echo "[3/5] Full mode — setting compressed=true so runs read the .zst directly ..."
  "$PYTHON" - "$WORK_DIR" <<'PY'
import json, os, sys
work = sys.argv[1]
for d in os.listdir(work):
    cp = os.path.join(work, d, "config.json")
    if os.path.isfile(cp):
        cfg = json.load(open(cp)); cfg["test_config"]["compressed"] = True
        json.dump(cfg, open(cp, "w"), indent=2)
PY
fi

NJOBS=$(find "$WORK_DIR" -maxdepth 1 -mindepth 1 -type d | wc -l)
[ "$NJOBS" -gt 0 ] || { echo "ERROR: no config dirs to run (check --strategies/--wsr)." >&2; exit 1; }

# --- ensure trace present ------------------------------------------------
"$PYTHON" - "$WORK_DIR" <<'PY'
import json, os, sys, subprocess
work = sys.argv[1]
need = {}
for d in os.listdir(work):
    mp = os.path.join(work, d, "meta.json")
    if os.path.isfile(mp):
        m = json.load(open(mp)); need[m["trace_file"]] = m.get("download_path")
for dest, url in need.items():
    if os.path.isfile(dest) and os.path.getsize(dest) > 0:
        print(f"      have {dest}"); continue
    if not url:
        raise SystemExit(f"ERROR: trace missing and no download_path: {dest}")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    print(f"      downloading {url}")
    subprocess.run(["wget", "-q", "-c", url, "-O", dest], check=True)
PY

# --- 4. run (each run sleeps 300s to warm the request queue, then serves) -
echo "[4/5] Running $NJOBS config(s) x repeat=$REPEAT ..."
echo "      NOTE: the tx binary sleeps 300s per run to preload the reader queue, so"
echo "      expect ~5-8 min per run even in smoke mode. This is by design (measurement fidelity)."
export PYTHONPATH="$OVH"
for d in "$WORK_DIR"/*/; do
  strat=$("$PYTHON" -c "import json;print(json.load(open('$d/config.json'))['cache_config']['rebalanceStrategy'])")
  echo "      -> $strat  ($(basename "$d"))"
  "$PYTHON" -c "from util import run_cachebench; run_cachebench('$d', repeat=$REPEAT)" \
    && echo "         done" || echo "         FAIL (see $d/log_*.txt)"
done

# --- 5. extract cycle ratios and compare to shipped ----------------------
echo "[5/5] Extracting cycle ratios and comparing to shipped Fig 11 data ..."
echo
"$PYTHON" - "$WORK_DIR" "$OVH/result_digested/meta_2022_overhead.csv" "$REPEAT" <<'PY'
import json, os, re, sys
import pandas as pd

work, shipped_csv, repeat = sys.argv[1], sys.argv[2], int(sys.argv[3])
SERVE = re.compile(r"CPU cycles for serving requests:\s*(\d+)")
REB   = re.compile(r"\[PeriodicWorker\] Thread name: PoolRebalancer, Total CPU cycles in work\(\):\s*(\d+)")
ALLOC = {"SIMPLE2Q": "LRU", "LRU2Q": "TwoQ", "TINYLFU": "TinyLFU", "TINYLFUTail": "TinyLFU"}
STRAT = {"marginal-hits-old": "marginal-hits", "marginal-hits-new": "marginal-hits-tuned"}

def grep_last(path, rx):
    val = None
    if os.path.isfile(path):
        for line in open(path):
            m = rx.search(line)
            if m: val = int(m.group(1))
    return val

rows = []
for d in sorted(os.listdir(work)):
    p = os.path.join(work, d)
    if not os.path.isdir(p): continue
    cfg = json.load(open(os.path.join(p, "config.json")))
    meta = json.load(open(os.path.join(p, "meta.json")))
    alloc = ALLOC.get(cfg["cache_config"]["allocator"], cfg["cache_config"]["allocator"])
    strat = STRAT.get(cfg["cache_config"]["rebalanceStrategy"], cfg["cache_config"]["rebalanceStrategy"])
    for i in range(repeat):
        log = os.path.join(p, f"log_{i}.txt")
        serve, reb = grep_last(log, SERVE), grep_last(log, REB)
        if serve and reb is not None:
            rows.append({"allocator": alloc, "rebalance_strategy": strat,
                         "wsr": float(meta["wsr"]), "serving_cycles": serve,
                         "rebalancer_cycles": reb, "rebalance_cycle_pct": reb/serve})

if not rows:
    print("No cycle numbers parsed from logs — check overhead/work_dir_cycles/*/log_*.txt")
    sys.exit(0)

ours = pd.DataFrame(rows)
mine = ours.groupby(["allocator","rebalance_strategy","wsr"])["rebalance_cycle_pct"].mean().reset_index()

ship = pd.read_csv(shipped_csv)
ship = ship.groupby(["allocator","rebalance_strategy","wsr"])["rebalance_cycle_pct"].mean().reset_index()
ship = ship.rename(columns={"rebalance_cycle_pct": "shipped_pct"})

cmp = mine.merge(ship, on=["allocator","rebalance_strategy","wsr"], how="left")
cmp = cmp.rename(columns={"rebalance_cycle_pct": "ours_pct"})
def ratio(r):
    if pd.isna(r["shipped_pct"]) or r["shipped_pct"] == 0: return float("nan")
    return r["ours_pct"] / r["shipped_pct"]
cmp["ours/shipped"] = cmp.apply(ratio, axis=1)

pd.options.display.float_format = lambda v: f"{v:.4g}"
print("=== rebalancer CPU-cycle ratio: ours (this machine) vs shipped (paper Fig 11) ===")
print(cmp.to_string(index=False))
print()
print("Note: absolute cycles differ by CPU; the RATIO column (ours/shipped) is the")
print("alignment check. ~1x means the algorithm's relative overhead reproduces; the")
print("disabled baseline should be ~0 in both. Reduced-numOps smoke may shift values.")
PY
echo
echo "Done."
