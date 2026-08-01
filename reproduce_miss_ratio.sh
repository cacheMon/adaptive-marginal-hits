#!/usr/bin/env bash
#
# reproduce_miss_ratio.sh — run the miss-ratio experiment end-to-end on ONE machine.
#
# Generates cachebench configs, downloads the trace(s), runs cachebench over every
# config, summarizes to a processed CSV, and (optionally) replots. This is the
# "Path B, miss-ratio only" driver — it skips the SSH/cluster scheduler and runs
# every job locally in sequence.
#
# Usage:
#   bash reproduce_miss_ratio.sh --smoke                 # fast sanity run (recommended first)
#   bash reproduce_miss_ratio.sh                         # full demo sweep (slow: ~1.5B requests)
#   bash reproduce_miss_ratio.sh --dataset meta          # a different dataset sample
#   bash reproduce_miss_ratio.sh --smoke --replot        # also drop the CSV in and replot
#
# Options:
#   --dataset demo|meta|cdn|twitter   which sample to run   (default: demo = meta_202210_kv)
#   --smoke                           tiny subset + capped numOps so it finishes in minutes
#   --numops N                        ops per job in smoke mode           (default: 20000000)
#   --wsr "0.01 0.1"                  working-set ratios to keep in smoke (default: "0.01")
#   --jobs J                          run J cachebench jobs concurrently  (default: 1)
#   --replot                          copy result into exp/result/ and run replot_results.sh
#
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${PYTHON:-python3}"

# --- defaults ------------------------------------------------------------
DATASET="demo"; SMOKE=0; NUMOPS=20000000; SMOKE_WSRS="0.01"; JOBS=1; REPLOT=0
while [ $# -gt 0 ]; do
  case "$1" in
    --dataset) DATASET="$2"; shift 2 ;;
    --smoke)   SMOKE=1; shift ;;
    --numops)  NUMOPS="$2"; shift 2 ;;
    --wsr)     SMOKE_WSRS="$2"; shift 2 ;;
    --jobs)    JOBS="$2"; shift 2 ;;
    --replot)  REPLOT=1; shift ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

# --- dataset -> generator / work dir / slab variant ----------------------
case "$DATASET" in
  demo)    GEN=gen_demo_config.py;    WORK=work_dir_demo;    VARIANT=v1 ;;
  meta)    GEN=gen_meta_config.py;    WORK=work_dir_meta;    VARIANT=v1 ;;
  cdn)     GEN=gen_cdn_config.py;     WORK=work_dir_cdn;     VARIANT=v1 ;;
  twitter) GEN=gen_twitter_config.py; WORK=work_dir_twitter; VARIANT=v2 ;;
  *) echo "ERROR: --dataset must be demo, meta, cdn, or twitter" >&2; exit 1 ;;
esac
WORK_DIR="$REPO_DIR/exp/$WORK"

USER_NAME="$(cat "$REPO_DIR/hosts/username.txt" | tr -d '[:space:]')"
BIN="/users/$USER_NAME/cachelib_${VARIANT}/opt/cachelib/bin/cachebench"
TRACE_DIR="$($PYTHON -c "import json;print(json.load(open('$REPO_DIR/exp/configs.json'))['local_trace_file_dir'])")"

echo "Dataset : $DATASET   (work dir: exp/$WORK)"
echo "Binary  : $BIN"
echo "Traces  : $TRACE_DIR"
[ "$SMOKE" = 1 ] && echo "Mode    : SMOKE  (numOps=$NUMOPS, wsr={$SMOKE_WSRS})" || echo "Mode    : FULL"
echo

if [ ! -x "$BIN" ]; then
  echo "ERROR: cachebench ($VARIANT) not found at:" >&2
  echo "    $BIN" >&2
  echo "Build it first:  bash set_up_env/build_cachelib.sh --variant $VARIANT" >&2
  exit 1
fi

# --- 1. generate configs -------------------------------------------------
echo "[1/5] Generating configs ($GEN) ..."
( cd "$REPO_DIR/exp/prepare_exp_configs" && "$PYTHON" "$GEN" >/dev/null )
echo "      $(find "$WORK_DIR" -maxdepth 1 -mindepth 1 -type d | wc -l) config dirs in exp/$WORK"

# --- 2. smoke pruning: keep a tiny subset + cap numOps -------------------
if [ "$SMOKE" = 1 ]; then
  echo "[2/5] Pruning to smoke subset ..."
  WSRS="$SMOKE_WSRS" NUMOPS="$NUMOPS" "$PYTHON" - "$WORK_DIR" <<'PY'
import json, os, shutil, sys
work = sys.argv[1]
keep_wsrs = set(float(x) for x in os.environ["WSRS"].split())
numops = int(os.environ["NUMOPS"])
# Keep only the LRU (SIMPLE2Q) allocator's rows at the chosen WSR(s); that still
# yields a full disabled-vs-rebalance miss-ratio comparison but few jobs.
kept = 0
for d in sorted(os.listdir(work)):
    p = os.path.join(work, d)
    if not os.path.isdir(p):
        continue
    try:
        meta = json.load(open(os.path.join(p, "meta.json")))
        cfg  = json.load(open(os.path.join(p, "config.json")))
    except FileNotFoundError:
        shutil.rmtree(p); continue
    alloc = cfg["cache_config"].get("allocator")
    if float(meta.get("wsr", -1)) not in keep_wsrs or alloc != "SIMPLE2Q":
        shutil.rmtree(p); continue
    cfg["test_config"]["numOps"] = numops
    json.dump(cfg, open(os.path.join(p, "config.json"), "w"), indent=2)
    kept += 1
print(f"      kept {kept} jobs (LRU, wsr in {sorted(keep_wsrs)}, numOps={numops})")
PY
else
  echo "[2/5] Full mode — no pruning."
fi

NJOBS=$(find "$WORK_DIR" -maxdepth 1 -mindepth 1 -type d | wc -l)
[ "$NJOBS" -gt 0 ] || { echo "ERROR: no config dirs to run." >&2; exit 1; }

# --- 3. download traces referenced by the kept configs -------------------
echo "[3/5] Ensuring trace files are present ..."
"$PYTHON" - "$WORK_DIR" "$TRACE_DIR" <<'PY'
import json, os, sys, subprocess
work, trace_dir = sys.argv[1], sys.argv[2]
seen = {}
for d in os.listdir(work):
    mp = os.path.join(work, d, "meta.json")
    if os.path.isfile(mp):
        m = json.load(open(mp))
        seen[m["trace_file"]] = m["download_path"]   # local dest -> remote url
for dest, url in seen.items():
    if os.path.isfile(dest) and os.path.getsize(dest) > 0:
        print(f"      have {dest}")
        continue
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    print(f"      downloading {url}")
    subprocess.run(["wget", "-q", "-c", url, "-O", dest], check=True)
PY

# --- 4. run cachebench over every config dir -----------------------------
echo "[4/5] Running $NJOBS cachebench job(s), $JOBS at a time ..."
export PYTHONPATH="$REPO_DIR/exp"
run_one() {
  local d="$1"
  "$PYTHON" -c "from util import run_cachebench; import sys; sys.exit(run_cachebench('$d'))" \
    && echo "      ok   $(basename "$d")" || echo "      FAIL $(basename "$d") (see $d/log.txt)"
}
export -f run_one; export PYTHON REPO_DIR
find "$WORK_DIR" -maxdepth 1 -mindepth 1 -type d -print0 \
  | xargs -0 -I{} -P "$JOBS" bash -c 'run_one "$@"' _ {}

# --- 5. summarize + report ----------------------------------------------
echo "[5/5] Summarizing ..."
OUT="result/report_${DATASET}.csv"
( cd "$REPO_DIR/exp" && "$PYTHON" summarize_result.py --base-dirs "$WORK" --output-file "$OUT" >/dev/null )
PROCESSED="$REPO_DIR/exp/result/report_${DATASET}_processed.csv"
echo "      wrote exp/$OUT (processed: exp/result/report_${DATASET}_processed.csv)"
echo

echo "=== Miss ratio (LRU) ==="
"$PYTHON" - "$PROCESSED" <<'PY'
import pandas as pd, sys
df = pd.read_csv(sys.argv[1])
cols = [c for c in ["trace_name","wsr","allocator","rebalance_strategy",
                    "miss_ratio","miss_ratio_reduction_from_disabled"] if c in df.columns]
df = df[cols].sort_values([c for c in ["trace_name","wsr","rebalance_strategy"] if c in cols])
with pd.option_context("display.max_rows", None, "display.width", 160):
    print(df.to_string(index=False))
PY

if [ "$REPLOT" = 1 ]; then
  echo
  SHIPPED="$REPO_DIR/exp/result/efficiency_result_processed.csv"
  if [ "$SMOKE" = 1 ]; then
    echo "Skipping --replot: these are SMOKE numbers and would clobber the shipped"
    echo "paper CSV ($SHIPPED)."
    echo "To plot smoke output anyway, point a plot script at exp/result/report_${DATASET}_processed.csv."
  else
    [ -f "$SHIPPED" ] && cp "$SHIPPED" "$SHIPPED.bak" && echo "Backed up shipped CSV -> $SHIPPED.bak"
    echo "Copying result into $SHIPPED and replotting ..."
    cp "$PROCESSED" "$SHIPPED"
    bash "$REPO_DIR/replot_results.sh"
  fi
fi
echo
echo "Done."
