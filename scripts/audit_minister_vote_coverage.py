"""Audit: ministri bez balsojumu seguma — `/audit-integrity` 9. pārbaudes saucējs.

Operatora verdikts 42 (2026-09-06).

KLASE. 9. pārbaude (partija ↔ Saeimas frakcijas ieraksts) grupē pēc
`saeima_individual_votes.faction`. Politiķis, kuram nav NEVIENA frakcijas
etiķetēta balsojuma, tajā GROUP BY neparādās vispār — ne kā atradums, ne kā
pārbaudīta rinda. Tātad pārbaude par viņu klusē, un klusēšana lasās kā "tīrs".

Ministri, kas nav deputāti, ir tieši šī klase: viņu `party` nav ar ko
salīdzināt, tāpēc T6 (novecojis partijas lauks) tur netiek atklāts nekad. Tā
pid=224 R. Meļņa nepareizā partija izdzīvoja divus mēnešus un 26 publicētus
pārskatus, kamēr 9. pārbaude katru reizi ziņoja tīru rezultātu.

Šis skripts NEATROD jaunu defektu — tas nosauc AKLO ZONU ar skaitli un
sarakstu: «N no M aktīvajiem ar `ministr` amatā nav frakcijas etiķetēta
balsojuma — partija automātiski neverificējama». Verifikācija paliek manuāla
(CVK, ministrijas lapa, ziņu avots); vārts tikai neļauj rindai pazust.

`checked=0` NAV tīrs rezultāts — tas ir salauzts saucējs (izejas kods 2).

Lietošana (no repo saknes, VIENMĒR .venv interpretators):
  .venv/Scripts/python.exe scripts/audit_minister_vote_coverage.py
  .venv/Scripts/python.exe scripts/audit_minister_vote_coverage.py --db data/atmina.db

Izejas kods: 0 tīrs · 1 ir rindas bez seguma · 2 salauzts saucējs.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO))

# Amata substring. Ar nolūku plašs: `role` ir brīva teksta kolonna, un formas
# svārstās ("Ministru prezidente (demisionējusi)", "Iekšlietu ministrijas
# parlamentārais sekretārs"). Plašāks saucējs ir pareizā puse — aklā zona,
# kas nav sarakstā, ir tieši tā, kas maksāja divus mēnešus.
_ROLE_NEEDLE = "ministr"

# Aktivitātes filtrs ar `COALESCE`, nevis kails `!=`, kā 9. pārbaudē: SQL
# `NULL != 'inactive'` ir NULL, tāpēc kails salīdzinājums izmestu politiķi ar
# `relationship_type IS NULL`. Šodien tādu nav (mērīts 2026-09-07: inactive 28,
# journalist 7, neutral 7, organization 16, tracked 169), bet saucējs, kas kādu
# klusi izmet, ir tieši tas, ko šis skripts pastāv, lai neatkārtotu.


def audit_minister_coverage(db: sqlite3.Connection, needle: str = _ROLE_NEEDLE) -> dict:
    """Aktīvie politiķi, kuru `role` satur `needle`, pret balsojumu segumu.

    Atgriež ``checked`` (saucējs), ``flagged`` (bez frakcijas etiķetēta
    balsojuma) un ``rows`` — pilnas rindas ar ``id``, ``name``, ``party``,
    ``role``, ``ballots``, ``labelled``.
    """
    rows = db.execute(
        """
        SELECT tp.id, tp.name, tp.party, tp.role,
               (SELECT COUNT(*) FROM saeima_individual_votes iv
                 WHERE iv.politician_id = tp.id) AS ballots,
               (SELECT COUNT(*) FROM saeima_individual_votes iv
                 WHERE iv.politician_id = tp.id AND iv.faction IS NOT NULL) AS labelled
        FROM tracked_politicians tp
        WHERE COALESCE(tp.relationship_type, '') != 'inactive'
          AND LOWER(COALESCE(tp.role, '')) LIKE '%' || ? || '%'
        ORDER BY tp.id
        """,
        (needle.lower(),),
    ).fetchall()
    flagged = [r for r in rows if r["labelled"] == 0]
    return {"checked": len(rows), "flagged": len(flagged), "rows": flagged}


def run_audit(db_path: str) -> int:
    db = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    try:
        res = audit_minister_coverage(db)
    finally:
        db.close()

    print(
        f"ministri bez balsojumu seguma: checked={res['checked']} "
        f"flagged={res['flagged']} — partija automātiski neverificējama"
    )
    for r in res["rows"]:
        print(
            f"  pid={r['id']} {r['name']} | party={r['party']!r} | role={r['role']!r} "
            f"| balsojumi={r['ballots']} (ar frakciju {r['labelled']})"
        )

    if res["checked"] == 0:
        print(
            "SALAUZTI VĀRTI: 0 aktīvu politiķu ar 'ministr' amatā — "
            "saucējs tukšs, rezultāts nav pierādījums."
        )
        return 2
    return 1 if res["flagged"] else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--db", default=str(_REPO / "data" / "atmina.db"))
    args = ap.parse_args()
    return run_audit(args.db)


if __name__ == "__main__":
    raise SystemExit(main())
