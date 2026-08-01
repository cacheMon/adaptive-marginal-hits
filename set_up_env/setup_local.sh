#!/usr/bin/env bash
#
# setup_local.sh — point the harness at THIS machine for a single-node run.
#
# "Path B, step 1: update some stuff." Rewrites the author-specific host/config
# files so a fresh clone runs locally as the current user. Safe to re-run.
#
#   bash set_up_env/setup_local.sh
#
# Env overrides:
#   TRACE_DIR=/path/for/traces   where to store downloaded trace files
#                                (default: $HOME/adaptive-mh-traces)
#
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
USER_NAME="$(whoami)"
TRACE_DIR="${TRACE_DIR:-$HOME/adaptive-mh-traces}"
cd "$REPO_DIR"

echo "Localizing slab-rebalance-bench for user '$USER_NAME' on this machine."
echo

# 1. Host list: one host = this machine (scheduler treats host 0 as a worker).
#    master.py / host_init.sh read the repo-root hosts/hosts.txt (exp/master/hosts.txt
#    is vestigial and read by nothing, so we don't touch it).
echo "$USER_NAME" > hosts/username.txt
echo "$USER_NAME@localhost" > hosts/hosts.txt
echo "  hosts/username.txt      -> $USER_NAME"
echo "  hosts/hosts.txt         -> $USER_NAME@localhost"

# 2. CacheLib install root. util.py resolves the binary at
#    /users/<user>/cachelib_v{1,2}/... (CloudLab home convention), so make
#    /users/<user> exist and be writable by us.
if [ ! -d "/users/$USER_NAME" ]; then
  echo "  creating /users/$USER_NAME (needs sudo)"
  sudo mkdir -p "/users/$USER_NAME"
  sudo chown "$USER_NAME":"$(id -gn)" "/users/$USER_NAME"
else
  echo "  /users/$USER_NAME already exists"
fi

# 3. Trace storage.
mkdir -p "$TRACE_DIR"
echo "  trace dir               -> $TRACE_DIR"

# 4. exp/configs.json with local paths (JSON written via python for safety).
python3 - "$REPO_DIR" "$TRACE_DIR" <<'PY'
import json, os, sys
repo, trace_dir = sys.argv[1], sys.argv[2]
cfg = {
    "work_dirs": [os.path.join(repo, "exp", "work_dir_demo")],
    "need_download_traces": True,
    "local_trace_file_dir": trace_dir,
    "wget_trace_path": "https://ftp.pdl.cmu.edu/pub/datasets/twemcacheWorkload/cacheDatasets",
    "python_path": "python3",
}
with open(os.path.join(repo, "exp", "configs.json"), "w") as f:
    json.dump(cfg, f, indent=4)
print("  exp/configs.json        -> local paths written")
PY

echo
echo "Done. Next:"
echo "  1. Build CacheLib:   bash set_up_env/build_cachelib.sh          (~30-60 min)"
echo "  2. Run miss ratio:   bash reproduce_miss_ratio.sh --smoke       (quick sanity run)"
