#!/usr/bin/env bash
#
# build_cachelib.sh — clone & build the forked CacheLib that cachebench needs.
#
# Slab size is a compile-time constant, so there are separate builds:
#   v1  = branch benchmark-4mb-slab -> /users/<user>/cachelib_v1  (Meta, Wikimedia CDN)
#   v2  = branch benchmark-1mb-slab -> /users/<user>/cachelib_v2  (Twitter)
#   tx  = branch benchmark-tx       -> /users/<user>/cachelib_tx  (CPU-cycle overhead, Fig 11)
# Miss-ratio on the demo/Meta traces only needs v1; the cycle experiment needs tx.
#
#   bash set_up_env/build_cachelib.sh            # builds v1 (default)
#   bash set_up_env/build_cachelib.sh --variant v2
#   bash set_up_env/build_cachelib.sh --variant tx
#   bash set_up_env/build_cachelib.sh --variant both
#
# Each build takes ~30-60 min and pulls in system packages via sudo.
#
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
USER_NAME="$(cat "$REPO_DIR/hosts/username.txt" 2>/dev/null | tr -d '[:space:]')"
[ -n "$USER_NAME" ] || { echo "ERROR: hosts/username.txt empty. Run setup_local.sh first." >&2; exit 1; }
INSTALL_ROOT="/users/$USER_NAME"
REPO_URL="https://github.com/eth-easl/CacheLib.git"

VARIANT="v1"
[ "${1:-}" = "--variant" ] && VARIANT="${2:-v1}"

[ -d "$INSTALL_ROOT" ] || { echo "ERROR: $INSTALL_ROOT missing. Run setup_local.sh first." >&2; exit 1; }

echo "Installing build prerequisites (sudo)..."
# Tolerate GPG/signature errors on unrelated third-party repos (github-cli,
# kitware, ...) — they don't affect the base Ubuntu packages we need.
sudo apt-get update -y >/dev/null 2>&1 || echo "  (apt update reported repo warnings; continuing)"
sudo apt-get install -y python3-pip libglib2.0-dev build-essential >/dev/null

build_one() {  # build_one <dirname> <branch>
  local dir="$1" branch="$2"
  local dest="$INSTALL_ROOT/$dir"
  echo
  echo "=== Building $dir  (branch $branch) -> $dest ==="
  if [ ! -d "$dest/.git" ]; then
    git clone "$REPO_URL" "$dest"
  fi
  git -C "$dest" fetch origin
  git -C "$dest" checkout "$branch"
  git -C "$dest" pull origin "$branch"
  # -j parallel, -T build tests off; installs into $dest/opt/cachelib
  ( cd "$dest" && sudo ./contrib/build.sh -j -T )
  local bin="$dest/opt/cachelib/bin/cachebench"
  [ -x "$bin" ] || { echo "ERROR: cachebench not produced at $bin" >&2; exit 1; }
  echo "OK: $bin"
}

case "$VARIANT" in
  v1)   build_one cachelib_v1 benchmark-4mb-slab ;;
  v2)   build_one cachelib_v2 benchmark-1mb-slab ;;
  tx)   build_one cachelib_tx benchmark-tx ;;
  both) build_one cachelib_v1 benchmark-4mb-slab; build_one cachelib_v2 benchmark-1mb-slab ;;
  *) echo "ERROR: --variant must be v1, v2, tx, or both" >&2; exit 1 ;;
esac

# libmock_time.so — enables trace-time replay (config useTraceTimer=true).
echo
echo "=== Compiling libmock_time.so ==="
g++ -shared -fPIC -o "$INSTALL_ROOT/libmock_time.so" \
    "$REPO_DIR/set_up_env/hook_time/libmock_time.cpp" -ldl
echo "OK: $INSTALL_ROOT/libmock_time.so"

echo
echo "Build complete. Now run:  bash reproduce_miss_ratio.sh --smoke"
