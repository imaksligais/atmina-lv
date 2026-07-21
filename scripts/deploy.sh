#!/usr/bin/env bash
set -euo pipefail

# Deploy output/atmina/ to Namecheap shared hosting via rsync over SSH.
# Reads credentials from .env.deploy (gitignored). Run from repo root.

cd "$(dirname "$0")/.."

if [[ ! -f .env.deploy ]]; then
  echo "ERROR: .env.deploy not found. Copy .env.deploy.example and fill in." >&2
  exit 1
fi

set -a
# shellcheck disable=SC1091
source .env.deploy
set +a

: "${DEPLOY_HOST:?missing in .env.deploy}"
: "${DEPLOY_USER:?missing in .env.deploy}"
: "${DEPLOY_PATH:?missing in .env.deploy}"
DEPLOY_PORT="${DEPLOY_PORT:-21098}"

SRC="output/atmina/"
if [[ ! -d "$SRC" ]]; then
  echo "ERROR: $SRC does not exist. Run generate_public_site() first." >&2
  exit 1
fi

DRY_RUN=""
DELETE_FLAG="--delete"
for arg in "$@"; do
  case "$arg" in
    --dry-run)
      DRY_RUN="--dry-run"
      echo ">> DRY RUN — no files will be transferred"
      ;;
    --no-delete)
      # Skip rsync --delete: files present only on the remote are PRESERVED.
      # Use when the local output/ tree is intentionally a partial/additive
      # build and a clean-sync delete would wipe legitimate remote content.
      DELETE_FLAG=""
      echo ">> --no-delete — remote-only files will be PRESERVED (no server reclaim)"
      ;;
  esac
done

echo ">> Deploying $SRC -> ${DEPLOY_USER}@${DEPLOY_HOST}:${DEPLOY_PATH} (port ${DEPLOY_PORT})"

# Pick rsync runner: prefer native rsync; fall back to WSL on Windows (Git Bash has no rsync).
if command -v rsync >/dev/null 2>&1; then
  RSYNC_CMD=(rsync)
  SRC_PATH="$SRC"
elif command -v wsl >/dev/null 2>&1 && wsl -d Hermes -- command -v rsync >/dev/null 2>&1; then
  echo ">> rsync not in PATH; using WSL (Hermes) rsync"
  # Stop Git Bash from mangling Unix paths into Windows paths when invoking wsl.exe
  export MSYS_NO_PATHCONV=1
  RSYNC_CMD=(wsl -d Hermes -- rsync)
  # Translate Windows-style cwd (/c/...) to WSL path (/mnt/c/...)
  WIN_CWD="$(pwd)"
  WSL_CWD="/mnt/${WIN_CWD:1:1}${WIN_CWD:2}"   # /c/Users/... -> /mnt/c/Users/...
  SRC_PATH="${WSL_CWD}/${SRC}"
else
  echo "ERROR: rsync not found (tried local + WSL). Install rsync or run from WSL." >&2
  exit 1
fi

"${RSYNC_CMD[@]}" -avz $DELETE_FLAG --human-readable \
  $DRY_RUN \
  -e "ssh -p ${DEPLOY_PORT} -o StrictHostKeyChecking=accept-new" \
  --exclude='.DS_Store' \
  --exclude='Thumbs.db' \
  --exclude='*.tmp' \
  --exclude='.well-known/' \
  --exclude='cgi-bin/' \
  "$SRC_PATH" \
  "${DEPLOY_USER}@${DEPLOY_HOST}:${DEPLOY_PATH}"

echo ">> Done."
