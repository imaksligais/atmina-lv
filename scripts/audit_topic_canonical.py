"""Audit: ne-kanoniskās `claim_type='position'` tēmas pret `src/topic_map.py`.

`/audit-integrity` 18. pārbaudes izpildāmā forma (operatora verdikts 24,
2026-09-06).

KĀPĒC ŠĪS FORMAS VĀRTS, NE KODA LABOJUMS. `src/tools.py::store_claim`
normalizē `topic` caur `normalize_topic()`, `src/db.py::store_claim` ne. Abi
raksta to pašu tabulu, un `topic` ir daļa no idempotences atslēgas
`(opponent_id, source_url, topic)`. Atslēgas normalizācijas ieslēgšana bez
sausā palaidiena ir tieši tā pati klase, kas 2026-08-02 saražoja 4 087
dublikātus (CLAUDE.md § Escalation 8: `UPDATE claims SET topic` var RAŽOT
dublikātus). Tāpēc kods paliek nemainīts, un tā vietā stāv skaitāms vārts:
ja ne-normalizētais ceļš kādreiz ielaiž jaunu tēmas formu, tā parādās šeit kā
viena rinda, nevis pēc gada kā tēmu lapa, ko neviens neatrod.

`checked=0` NAV tīrs rezultāts. Vārts, kas nevar krist, nav pierādījums
(CLAUDE.md § "A gate that cannot fail") — tāpēc tukšs saucējs ir izejas kods 2.

Lietošana (no repo saknes, VIENMĒR .venv interpretators):
  .venv/Scripts/python.exe scripts/audit_topic_canonical.py
  .venv/Scripts/python.exe scripts/audit_topic_canonical.py --db data/atmina.db

Izejas kods: 0 tīrs · 1 atrastas ne-kanoniskas tēmas · 2 salauzts saucējs.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO))

from src.topic_map import get_all_group_names  # noqa: E402


def canonical_topics() -> set[str]:
    """33 kanoniskās grupas no `src/topic_map.py` — vienīgais patiesības avots."""
    return set(get_all_group_names())


def audit_topics(db: sqlite3.Connection, canonical: set[str]) -> dict:
    """Saskaita `position` claims un to tēmas pret kanonisko kopu.

    Atgriež: ``checked`` (position claims skaits — saucējs), ``distinct``
    (distinktās tēmas), ``canonical`` (kanonisko grupu skaits), ``flagged``
    (ne-kanonisko tēmu skaits) un ``rows`` — ``(tēma, skaits, mazākais id)``.
    """
    rows = db.execute(
        """
        SELECT topic, COUNT(*) AS n, MIN(id) AS sample_id
        FROM claims
        WHERE claim_type = 'position'
        GROUP BY topic
        ORDER BY n DESC, topic
        """
    ).fetchall()
    checked = sum(r[1] for r in rows)
    flagged = [(r[0], r[1], r[2]) for r in rows if r[0] not in canonical]
    return {
        "checked": checked,
        "distinct": len(rows),
        "canonical": len(canonical),
        "flagged": len(flagged),
        "rows": flagged,
    }


def run_audit(db_path: str, canonical: set[str] | None = None) -> int:
    canonical = canonical_topics() if canonical is None else canonical
    db = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    try:
        res = audit_topics(db, canonical)
    finally:
        db.close()

    print(
        f"checked={res['checked']} distinct={res['distinct']}/{res['canonical']} "
        f"flagged={res['flagged']}"
    )
    for topic, n, sample_id in res["rows"]:
        print(f"  {topic!r}: {n} claims, piem. #{sample_id}")

    if res["checked"] == 0:
        print("SALAUZTI VĀRTI: 0 `position` claims — saucējs tukšs, rezultāts nav pierādījums.")
        return 2
    return 1 if res["flagged"] else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--db", default=str(_REPO / "data" / "atmina.db"))
    args = ap.parse_args()
    return run_audit(args.db)


if __name__ == "__main__":
    raise SystemExit(main())
