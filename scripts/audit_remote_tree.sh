#!/usr/bin/env bash
# Salīdzina servera koku ar lokālo output/atmina/ — kas ir TIKAI serverī.
# Lasīšanas režīms: neko nemaina ne serverī, ne lokāli.
#
#   bash scripts/audit_remote_tree.sh [izvades_dir]     # noklusējums: private/
#
# Izvade (neizsekota, private/ ir gitignorēts):
#   remote-tree-<datums>.txt, local-tree-<datums>.txt,
#   remote-only-<datums>.txt  — faili, kas ir serverī un nav lokāli (lēmums katram),
#   local-only-<datums>.txt   — faili, kas ir lokāli un nav serverī (info).
set -euo pipefail
cd "$(dirname "$0")/.."
set -a
# shellcheck disable=SC1091
source .env.deploy
set +a
: "${DEPLOY_HOST:?}" "${DEPLOY_USER:?}" "${DEPLOY_PATH:?}"
DEPLOY_PORT="${DEPLOY_PORT:-21098}"
OUT="${1:-private}"
mkdir -p "$OUT"
STAMP="$(date +%F)"
SSH_OPTS=(-p "$DEPLOY_PORT" -o StrictHostKeyChecking=accept-new)
[[ -n "${DEPLOY_SSH_KEY:-}" ]] && SSH_OPTS+=(-o IdentitiesOnly=yes -i "$DEPLOY_SSH_KEY")

ssh "${SSH_OPTS[@]}" "${DEPLOY_USER}@${DEPLOY_HOST}" \
  "cd '${DEPLOY_PATH}' && find . -type f ! -path './.well-known/*' ! -path './cgi-bin/*' | sort" \
  > "$OUT/remote-tree-$STAMP.txt"
( cd output/atmina && find . -type f | sort ) > "$OUT/local-tree-$STAMP.txt"
comm -23 "$OUT/remote-tree-$STAMP.txt" "$OUT/local-tree-$STAMP.txt" > "$OUT/remote-only-$STAMP.txt"
comm -13 "$OUT/remote-tree-$STAMP.txt" "$OUT/local-tree-$STAMP.txt" > "$OUT/local-only-$STAMP.txt"

echo "serverī:        $(wc -l < "$OUT/remote-tree-$STAMP.txt")"
echo "lokāli:         $(wc -l < "$OUT/local-tree-$STAMP.txt")"
echo "tikai serverī:  $(wc -l < "$OUT/remote-only-$STAMP.txt")  -> $OUT/remote-only-$STAMP.txt"
echo "tikai lokāli:   $(wc -l < "$OUT/local-only-$STAMP.txt")  -> $OUT/local-only-$STAMP.txt"
