#!/usr/bin/env bash
#
# replot_results.sh — regenerate every paper figure from the shipped result CSVs.
#
# No CacheLib, no traces, no cluster: this only reads the pre-computed CSVs in
# exp/result/ and writes PDF figures. Run it from anywhere in the repo:
#
#     bash replot_results.sh
#
# Output: exp/plotting/figures/<group>/*.pdf   (plus two demo PDFs, see below),
#         trace_heatmap/*.png (Fig 2) and overhead/plotting/*.pdf (Fig 11)
#
set -euo pipefail

# --- locate the repo and pick a python -----------------------------------
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLOT_DIR="$REPO_DIR/exp/plotting"
RESULT_DIR="$REPO_DIR/exp/result"
PYTHON="${PYTHON:-python3}"   # override with e.g. PYTHON=python if that's your interpreter

command -v "$PYTHON" >/dev/null 2>&1 || { echo "ERROR: '$PYTHON' not found. Install Python 3 or set PYTHON=..." >&2; exit 1; }

# --- deps check (friendly message instead of a stack trace) --------------
if ! "$PYTHON" -c "import pandas, matplotlib, numpy, seaborn" 2>/dev/null; then
  echo "ERROR: missing Python packages. Install them with:" >&2
  echo "    pip install pandas matplotlib numpy seaborn" >&2
  exit 1
fi

cd "$PLOT_DIR"

pass=0; fail=0; failed_scripts=""
run() {  # run <description> <script.py> [args...]
  local desc="$1"; shift
  printf '  %-46s ' "$desc"
  if "$PYTHON" "$@" >/dev/null 2>&1; then
    echo "ok"; pass=$((pass+1))
  else
    echo "FAILED"; fail=$((fail+1)); failed_scripts="$failed_scripts\n    $*"
  fi
}

echo "Replotting from CSVs in exp/result/  (python: $PYTHON)"
echo

echo "Size heatmaps, case studies and synthetic workloads (Figs 2-6):"
run "request-size heatmaps (Fig 2)"            ../../tools/plot/plot_size_heatmap.py
run "anti-patterns (Fig 3), production (Fig 12)" plot_case_study_production.py
run "distance to optimal (Fig 4)"              ../../tools/plot/plot_optimal_comparison.py
run "Marginal-Hits oscillation (Fig 5)"        ../../tools/plot/plot_oscillation.py
run "workload shift (Fig 6)"                   ../../tools/plot/plot_drift_curve.py

echo "Meta KV — miss-ratio & slab-movement curves (Fig 7):"
run "demo figure (meta_202210_kv)"            plot_demo_figure.py "$RESULT_DIR/efficiency_result_processed.csv" meta_202210_kv -o "$PLOT_DIR/figures/demo"
run "per-allocator miss-ratio curves"          plot_miss_ratio_curve.py
run "per-allocator rebalanced-slabs curves"    plot_rebalanced_slabs_curve.py

echo "Wikimedia CDN — bars (Fig 8; also the Fig 1 bars):"
run "miss-ratio bars"                           plot_miss_ratio_bar.py
run "rebalanced-slabs bars"                     plot_rebalanced_slabs_bar.py

echo "54 Twitter traces — box / worst / best case (Figs 9-10):"
run "miss-ratio boxplots"                       plot_miss_ratio_box.py
run "miss-ratio boxplots (with outliers)"       plot_miss_ratio_box_outlier.py
run "rebalanced-slabs boxplots"                 plot_rebalanced_slabs_box.py
run "worst-case bars"                           plot_worst_case.py
run "worst-case bars (separate eviction)"       plot_worst_case_separate_eviction.py
run "best-case bars"                            plot_best_case.py
run "tuned-improvement boxplots"                plot_tuned_improvement_box.py

echo "CPU overhead (Fig 11):"
cd "$REPO_DIR/overhead/plotting"
run "rebalancer CPU cycles"                     plot_rebalancer_cycle_ratio.py
cd "$PLOT_DIR"

echo "Parameter sensitivity (Fig 13):"
run "AIMD / EMR sweeps"                         plot_sensitivity_six.py
run "AIMD / EMR sweeps (four panels, not in paper)" plot_sensitivity.py

echo "S3-FIFO and SIEVE (Fig 14), Meta KV slab allocation, legends:"
run "S3-FIFO / SIEVE bars (Fig 14)"             plot_s3fifo_bar.py
run "slab allocation over time"                 ../../tools/plot/plot_slab_timeline.py
run "legends of Figs 1, 7, 9, 10-11"            plot_legends.py

echo "LAMA buffer-size study:"
run "lama buffer-size analysis"                 plot_lama_buffer_size.py

echo "Slides variants (extra, not in paper):"
run "meta KV curves for slides"                 plot_miss_ratio_curve_slides.py

echo
echo "Done: $pass ok, $fail failed."
echo "Figures are in: exp/plotting/figures/   (demo PDFs in exp/plotting/figures/demo/, Fig 2 in trace_heatmap/, Fig 11 in overhead/plotting/)"
if [ "$fail" -ne 0 ]; then
  echo -e "Failed scripts:$failed_scripts"
  exit 1
fi
