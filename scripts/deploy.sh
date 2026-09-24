#!/usr/bin/env bash
set -euo pipefail

# Deploy output/atmina/ uz Cloudflare Workers Static Assets (wrangler deploy).
# Konfigurācija: wrangler.json (html_handling none — publiskie URL nes .html).
# Akreditācija: .env.deploy (gitignored) — CLOUDFLARE_API_TOKEN + CLOUDFLARE_ACCOUNT_ID.
# Līdz 2026-09 šis skripts rsync-oja uz koplietoto hostingu; vēsture git logā.

cd "$(dirname "$0")/.."

DEPLOY_ENV_FILE="${DEPLOY_ENV_FILE:-.env.deploy}"
if [[ ! -f "$DEPLOY_ENV_FILE" ]]; then
  echo "ERROR: $DEPLOY_ENV_FILE not found. Copy .env.deploy.example and fill in." >&2
  exit 1
fi
set -a
# shellcheck disable=SC1090
source "$DEPLOY_ENV_FILE"
set +a

: "${CLOUDFLARE_API_TOKEN:?missing in $DEPLOY_ENV_FILE}"
: "${CLOUDFLARE_ACCOUNT_ID:?missing in $DEPLOY_ENV_FILE}"
export CLOUDFLARE_API_TOKEN CLOUDFLARE_ACCOUNT_ID
# Piesprausta versija — sk. wiki/operations/deploy.md § Cloudflare.
WRANGLER_CMD="${WRANGLER_CMD:-npx wrangler@4.132.0}"

SRC="output/atmina/"
if [[ ! -d "$SRC" ]]; then
  echo "ERROR: $SRC does not exist. Run generate_public_site() first." >&2
  exit 1
fi

DRY_RUN=""
SKIP_OUTPUT_CHECK=""
for arg in "$@"; do
  case "$arg" in
    --no-output-check)
      # Escape hatch for an urgent push when check_output.py is itself wrong.
      # Everything it flags is a reference the deploy will NOT satisfy, and
      # the full-tree deploy means it stays broken live until someone notices.
      SKIP_OUTPUT_CHECK="1"
      echo ">> --no-output-check — built-tree validation SKIPPED" >&2
      ;;
    --dry-run)
      DRY_RUN="1"
      echo ">> DRY RUN — preflight + failu skaits, wrangler netiek saukts"
      ;;
    --no-delete|--delete)
      # Cloudflare deploy vienmēr ir PILNS koks — additīvā/destruktīvā režīma vairs
      # nav. Karogi paliek pieņemti, jo katrs runbooks un dashboard tos padod.
      echo ">> $arg — no-op kopš Cloudflare migrācijas (deploy vienmēr ir pilns koks)"
      ;;
  esac
done

# Preflight: never push a tree that references files the push does not contain.
# Additive is the standard mode, so anything broken that lands here has no
# reclaim path and no detector — it just sits on the live site (2026-08-01 audit
# found two published briefs whose hero + og:image had 404'd since May).
# PY_CHECK tiek atrisināts arī ar --no-output-check — to lieto deploy log beigās.
PY_CHECK=""
for cand in .venv/Scripts/python.exe .venv/bin/python; do
  [[ -x "$cand" ]] && { PY_CHECK="$cand"; break; }
done
if [[ -z "$SKIP_OUTPUT_CHECK" ]]; then
  if [[ -n "$PY_CHECK" ]]; then
    echo ">> Preflight: scripts/check_output.py"
    if ! "$PY_CHECK" scripts/check_output.py; then
      echo "ERROR: built tree has broken references — refusing to deploy." >&2
      echo "       Fix them, or record a deliberate exception in" >&2
      echo "       scripts/output_check_allowlist.txt (with a reason)." >&2
      echo "       Genuine emergency override: --no-output-check" >&2
      exit 1
    fi
    # Publish-gate (T15, 2026-08-09): deploy aiznes visu koku, tāpēc
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

# --- transports: Cloudflare Workers Static Assets -------------------------
FILE_COUNT="$(find "$SRC" -type f | wc -l | tr -d ' ')"
BIG="$(find "$SRC" -type f -size +25M | head -5)"
echo ">> faili kokā: ${FILE_COUNT} (limits 20 000 / versija)"
if (( FILE_COUNT > 15000 )); then
  echo ">> WARNING: ${FILE_COUNT} faili — tuvojas 20 000 limitam" >&2
fi
if [[ -n "$BIG" ]]; then
  echo "ERROR: faili virs 25 MiB (Cloudflare limits):" >&2
  echo "$BIG" >&2
  exit 1
fi
if [[ ! -f "${SRC}_headers" ]]; then
  echo "ERROR: ${SRC}_headers trūkst — renderē 'static' domēnu (assets/_headers → koks)." >&2
  exit 1
fi

if [[ -n "$DRY_RUN" ]]; then
  echo ">> DRY RUN beidzas šeit — wrangler netiek saukts."
  exit 0
fi

echo ">> $WRANGLER_CMD deploy (wrangler.json → ${SRC})"
DEPLOY_OUT="$(mktemp)"
trap 'rm -f "$DEPLOY_OUT"' EXIT
# pipefail (augšā) saglabā wrangler izejas kodu arī caur tee.
# shellcheck disable=SC2086
$WRANGLER_CMD deploy 2>&1 | tee "$DEPLOY_OUT"

# Deploy pēda (2026-09-24): rutīnas solis «11. Deploy» (src/routine.py
# _check_deploy) lasa `logs.action='deploy'`. Tikai pēc ĪSTA deploy — dry-run
# izgāja augstāk. Log kļūme NEDRĪKST gāzt jau notikušu deploy: `|| echo`.
# ATMINA_DEPLOY_LOG_DB — testu DB ceļš; tukšs = noklusētā data/atmina.db.
DEPLOY_VERSION_ID="$(grep -oE 'Current Version ID: [0-9a-fA-F-]{36}' "$DEPLOY_OUT" | tail -1 | sed 's/^Current Version ID: //' || true)"
export DEPLOY_VERSION_ID FILE_COUNT SRC
export ATMINA_DEPLOY_LOG_DB="${ATMINA_DEPLOY_LOG_DB:-}"
if [[ -n "$PY_CHECK" ]]; then
  PYTHONUTF8=1 "$PY_CHECK" -c "
import os, pathlib
from src.db import get_db, log_action
db_path = os.environ['ATMINA_DEPLOY_LOG_DB'] or None
pages = {p.stem for p in pathlib.Path(os.environ['SRC'], 'blog').glob('*.html')}
db = get_db(db_path)
try:
    keys = [r[0] for r in db.execute('SELECT subject_key FROM publish_approvals')]
finally:
    db.close()
log_action('deploy', db_path=db_path, details={
    'version_id': os.environ['DEPLOY_VERSION_ID'] or None,
    'files': int(os.environ['FILE_COUNT']),
    'approved_slugs': sorted(k for k in keys if k in pages),
})
print('>> deploy log: versija', os.environ['DEPLOY_VERSION_ID'] or '—')
" || echo ">> WARNING: deploy log neizdevās" >&2
else
  echo ">> WARNING: deploy log izlaists — nav .venv python" >&2
fi
echo ">> Done."
