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
# Additive by default (CLAUDE.md standing decision: "Deploy is additive").
# The local output/ tree is routinely a PARTIAL build — a narrow render emits
# only the touched domains — and `finanses` + `statistika` are curated remote
# directories with no local counterpart at all. Under rsync --delete both get
# reclaimed. Until 2026-08-01 the default here was "--delete" and every
# documented caller had to remember to pass --no-delete; the dashboard's
# deploy button did not, so pressing it would have wiped the curated trees.
# The safe mode is now the default and destruction is opt-in.
DELETE_FLAG=""
SKIP_OUTPUT_CHECK=""
for arg in "$@"; do
  case "$arg" in
    --no-output-check)
      # Escape hatch for an urgent push when check_output.py is itself wrong.
      # Everything it flags is a reference the deploy will NOT satisfy, and
      # additive mode means it stays broken on the server until someone notices.
      SKIP_OUTPUT_CHECK="1"
      echo ">> --no-output-check — built-tree validation SKIPPED" >&2
      ;;
    --dry-run)
      DRY_RUN="--dry-run"
      echo ">> DRY RUN — no files will be transferred"
      ;;
    --no-delete)
      # Now the default. Accepted as an explicit no-op because every runbook,
      # skill and workflow in the repo passes it; removing it would break them
      # all for no gain. Keep accepting it.
      DELETE_FLAG=""
      ;;
    --delete)
      # Opt-in destructive sync: files present only on the remote are REMOVED.
      # Only ever correct after a FULL generate_public_site(), because that is
      # the only build that carries every page — including the curated
      # `finanses` + `statistika` snapshots, which _copy_curated() overlays from
      # curated/atmina/ precisely so a --delete run preserves them. After a
      # NARROW render the tree is partial and this flag will reclaim whatever
      # that render did not emit.
      DELETE_FLAG="--delete"
      echo ">> !! --delete — remote-only files will be REMOVED from the server" >&2
      echo ">>    Only safe after a FULL render. After a narrow render this" >&2
      echo ">>    deletes every page the render did not emit. Ctrl-C if unsure." >&2
      ;;
  esac
done

# Preflight: never push a tree that references files the push does not contain.
# Additive is the standard mode, so anything broken that lands here has no
# reclaim path and no detector — it just sits on the live site (2026-08-01 audit
# found two published briefs whose hero + og:image had 404'd since May).
if [[ -z "$SKIP_OUTPUT_CHECK" ]]; then
  PY_CHECK=""
  for cand in .venv/Scripts/python.exe .venv/bin/python; do
    [[ -x "$cand" ]] && { PY_CHECK="$cand"; break; }
  done
  if [[ -n "$PY_CHECK" ]]; then
    echo ">> Preflight: scripts/check_output.py"
    if ! "$PY_CHECK" scripts/check_output.py; then
      echo "ERROR: built tree has broken references — refusing to deploy." >&2
      echo "       Fix them, or record a deliberate exception in" >&2
      echo "       scripts/output_check_allowlist.txt (with a reason)." >&2
      echo "       Genuine emergency override: --no-output-check" >&2
      exit 1
    fi
    # Publish-gate (T15, 2026-08-09): additīvais deploy rsynco visu koku, tāpēc
    # jebkurš deploy var aiznest live dienas pārskata MELNRAKSTU, ko check.sh
    # pilnais renders ir ielicis kokā. Vārti (kopš 2026-08-18 divi, UN nevis VAI):
    # brief lapai jābūt (a) approved=1 attēlam DB un (b) EKSPLICĪTAI operatora
    # publicēšanas atļaujai `publish_approvals` (scripts/approve_publish.py) —
    # attēls pierāda tikai to, ka hero ir izvēlēts, nevis ka teksts drīkst iet ārā.
    echo ">> Preflight: publish-gate (blog briefs)"
    if ! "$PY_CHECK" scripts/check_output.py --publish-gate-only; then
      echo "ERROR: kokā ir brief lapa bez publicēšanas vārtiem — deploy bloķēts." >&2
      echo "       Pabeidz vārtus: attēla apstiprinājums DB un pēc korektūras" >&2
      echo "       .venv/Scripts/python.exe scripts/approve_publish.py <YYYY-MM-DD>" >&2
      echo "       (nedēļas pārskatam: nedela-<YYYY-MM-DD>), vai izmet lapu no koka." >&2
      echo "       Apzināta apiešana: --no-output-check" >&2
      exit 1
    fi
  else
    echo ">> WARNING: no .venv python found — skipping built-tree validation" >&2
  fi
fi

echo ">> Deploying $SRC -> ${DEPLOY_USER}@${DEPLOY_HOST}:${DEPLOY_PATH} (port ${DEPLOY_PORT})"

# Pick rsync runner: prefer native rsync; fall back to WSL on Windows (Git Bash has no rsync).
#
# The WSL branch used to hardcode `wsl -d Hermes`, which tied deploy to one
# named distro that this repo does not own — uninstall it and deploy dies with a
# confusing error at publish time. Now we probe: default distro first, then any
# distro that actually has rsync. Installing a native rsync makes this whole
# branch moot (see wiki/operations/deploy.md).
WSL_DISTRO=""
if command -v rsync >/dev/null 2>&1; then
  RSYNC_CMD=(rsync)
  SRC_PATH="$SRC"
elif command -v wsl >/dev/null 2>&1; then
  if wsl -- command -v rsync >/dev/null 2>&1; then
    WSL_DISTRO="(default)"
    WSL_RUN=(wsl --)
  else
    # `wsl -l -q` emits UTF-16LE on Windows; strip NULs before matching.
    while read -r d; do
      [ -z "$d" ] && continue
      if wsl -d "$d" -- command -v rsync >/dev/null 2>&1; then
        WSL_DISTRO="$d"
        WSL_RUN=(wsl -d "$d" --)
        break
      fi
    done < <(wsl -l -q 2>/dev/null | tr -d '\0\r')
  fi

  if [ -z "$WSL_DISTRO" ]; then
    echo "ERROR: rsync not found natively, and no WSL distro provides it." >&2
    echo "       Install rsync on Windows (see wiki/operations/deploy.md) — deploy.sh" >&2
    echo "       prefers a native rsync and needs no WSL at all once it is on PATH." >&2
    exit 1
  fi

  echo ">> rsync not in PATH; using WSL rsync from distro: ${WSL_DISTRO}"
  # Stop Git Bash from mangling Unix paths into Windows paths when invoking wsl.exe
  export MSYS_NO_PATHCONV=1
  RSYNC_CMD=("${WSL_RUN[@]}" rsync)
  # Translate Windows-style cwd (/c/...) to WSL path (/mnt/c/...)
  WIN_CWD="$(pwd)"
  WSL_CWD="/mnt/${WIN_CWD:1:1}${WIN_CWD:2}"   # /c/Users/... -> /mnt/c/Users/...
  SRC_PATH="${WSL_CWD}/${SRC}"
else
  echo "ERROR: rsync not found and WSL unavailable. Install rsync — see" >&2
  echo "       wiki/operations/deploy.md." >&2
  exit 1
fi

# Pick the SSH transport. rsync spawns ssh itself, so the two must come from the
# SAME runtime: an MSYS2 rsync driving Git Bash's ssh dies with
# `dup() in/out/err failed` the moment stdio is not a tty (i.e. any automated
# run), and driving Windows' native OpenSSH breaks the protocol stream with
# `safe_read failed / connection reset`. Both were reproduced on 2026-07-25.
# Rule: prefer an ssh sitting next to the rsync we resolved.
#
# Second trap: such an ssh resolves `~` through its own /etc/passwd, NOT the
# inherited $HOME — MSYS2 ssh looks in /home/<user>/.ssh and silently finds no
# key ("Permission denied (publickey)"). So when we deliberately pick a
# non-PATH ssh we also point it at the real key, known_hosts, and nothing else.
#
# Third trap: rsync splits the -e value on whitespace, so a home containing a
# space (C:\Users\<first last>\) would shred the command. cygpath -d gives the
# 8.3 short form, which never has spaces.
SSH_BIN="ssh"
SSH_EXTRA=()
if [ -z "$WSL_DISTRO" ] && command -v cygpath >/dev/null 2>&1; then
  RSYNC_BIN="$(command -v rsync)"
  SIBLING_SSH="$(dirname "$RSYNC_BIN")/ssh"
  PATH_SSH="$(command -v ssh || true)"
  if { [ -x "$SIBLING_SSH" ] || [ -x "${SIBLING_SSH}.exe" ]; } \
     && [ "$SIBLING_SSH" != "$PATH_SSH" ]; then
    SSH_BIN="$SIBLING_SSH"
    SSH_HOME="$(cygpath -u "$(cygpath -d "$HOME" 2>/dev/null)" 2>/dev/null || echo "$HOME")"
    DEPLOY_SSH_KEY="${DEPLOY_SSH_KEY:-${SSH_HOME}/.ssh/id_ed25519}"
    if [ ! -f "$DEPLOY_SSH_KEY" ]; then
      echo "ERROR: SSH key not found: $DEPLOY_SSH_KEY" >&2
      echo "       Set DEPLOY_SSH_KEY in .env.deploy — ${SSH_BIN} cannot read" >&2
      echo "       \$HOME/.ssh itself (see wiki/operations/deploy.md)." >&2
      exit 1
    fi
    case "$DEPLOY_SSH_KEY$SSH_HOME" in
      *" "*)
        echo "ERROR: SSH key or home path contains a space; rsync -e would split it:" >&2
        echo "       $DEPLOY_SSH_KEY" >&2
        exit 1
        ;;
    esac
    SSH_EXTRA=(-o IdentitiesOnly=yes -i "$DEPLOY_SSH_KEY"
               -o "UserKnownHostsFile=${SSH_HOME}/.ssh/known_hosts")
    echo ">> ssh transport: ${SSH_BIN} (runtime-matched to rsync)"
  fi
fi

"${RSYNC_CMD[@]}" -avz $DELETE_FLAG --human-readable \
  $DRY_RUN \
  -e "${SSH_BIN} -p ${DEPLOY_PORT} -o StrictHostKeyChecking=accept-new ${SSH_EXTRA[*]-}" \
  --exclude='.DS_Store' \
  --exclude='Thumbs.db' \
  --exclude='*.tmp' \
  --exclude='.well-known/' \
  --exclude='cgi-bin/' \
  "$SRC_PATH" \
  "${DEPLOY_USER}@${DEPLOY_HOST}:${DEPLOY_PATH}"

echo ">> Done."
