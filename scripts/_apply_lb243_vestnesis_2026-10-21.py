#!/usr/bin/env python
"""Vienreizējs: Latvijas Banka (pid 243) — Vēstneša izvēlnes saites ārā (operatora lēmums 2026-10-21).

Vēstneša kategoriju lapas («Amatu konkursu ziņas», «Darbības pārskati», …) nes
iestāžu izvēlni, kurā «Latvijas Banka» stāv kā navigācijas punkts. Matcher to
lasa kā pieminējumu. Divas izvēlnes formas (mērīts 2026-10-21, 35 doki):

* A: «Latvijas Banka\\nNoteikumi Informācija u.c.» (bankas apakšpunkti rindās) — 27 doki;
* B: «Latvijas Banka Latvijas Nacionālais arhīvs» (iestāžu saraksts vienā rindā) — 8 doki.

Abas formas ieliek `tracked_politicians.negative_patterns` pid 243 (matcher tās
pārbauda VISĀ tekstā — `p in text`, arī ALL-CAPS formā — un noraida pid visam
dokam). Kļūdainā saite = Vēstneša doks, kas piesaistīts pid 243, satur izvēlni
un ārpus izvēlnes nesatur nevienu bankas nosaukuma formu. DELETE notiek ar
`dp_suppression_mode='record'`, tāpēc trigeris ieraksta apspiešanu un saite
neatgriežas arī bez parauga.

Bez `--apply` = sausā palaide (transakcija atritināta). `--apply` prasa
`--rollback` un atsaka, ja faila (doc, role) kopa ≠ šīs palaides kopa.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

import src.db as db_mod  # noqa: E402

PID = 243
MENU_A = "Latvijas Banka\nNoteikumi Informācija u.c."
MENU_B = "Latvijas Banka Latvijas Nacionālais arhīvs"
NEW_PATTERNS = [MENU_A, MENU_B]
FORMS = ("Latvijas Bank", "LATVIJAS BANK")  # every stored form + inflections start so
_ROW_RE = re.compile(r"VALUES \((\d+), 243, '(subject|mentioned)'")


def wrong_links(db) -> list:
    rows = db.execute(
        """SELECT dp.document_id, dp.role, dp.created_at, dp.extracted_at, dp.suspect_at, d.content
           FROM document_politicians dp JOIN documents d ON d.id = dp.document_id
           WHERE dp.politician_id = ? AND d.platform = 'vestnesis' ORDER BY dp.document_id""",
        (PID,),
    ).fetchall()
    out = []
    for r in rows:
        text = r["content"] or ""
        if not any(p in text for p in NEW_PATTERNS):
            continue
        rest = text
        for p in NEW_PATTERNS:
            rest = rest.replace(p, "#")
        if not any(f in rest for f in FORMS):
            out.append(r)
    return out, len(rows)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--rollback")
    args = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")

    db = db_mod.get_db(args.db)
    db.isolation_level = None
    db.execute("BEGIN IMMEDIATE")
    try:
        old = db.execute("SELECT negative_patterns FROM tracked_politicians WHERE id = ?", (PID,)).fetchone()[0]
        if json.loads(old or "[]") != []:
            raise SystemExit(f"STOP: negative_patterns pid {PID} nav tukšs: {old!r}")
        if db.execute("SELECT mode FROM dp_suppression_mode").fetchone()[0] != "record":
            raise SystemExit("STOP: dp_suppression_mode nav 'record'")
        wrong, linked = wrong_links(db)
        q = lambda s, *p: db.execute(s, p).fetchone()[0]  # noqa: E731
        dp0 = q("SELECT COUNT(*) FROM document_politicians WHERE politician_id = ?", PID)
        sup0 = q("SELECT COUNT(*) FROM document_politician_suppressions WHERE politician_id = ? AND lifted_at IS NULL", PID)
        claims = q(
            f"SELECT COUNT(*) FROM claims WHERE opponent_id = ? AND document_id IN "
            f"({','.join(str(r['document_id']) for r in wrong) or 'NULL'})", PID)
        if claims:
            raise SystemExit(f"STOP: {claims} pid {PID} claims uz kļūdainajiem dokiem")
        db.execute("UPDATE tracked_politicians SET negative_patterns = ? WHERE id = ?",
                   (json.dumps(NEW_PATTERNS, ensure_ascii=False), PID))
        for r in wrong:
            db.execute("DELETE FROM document_politicians WHERE document_id = ? AND politician_id = ? AND role = ?",
                       (r["document_id"], PID, r["role"]))
        dp1 = q("SELECT COUNT(*) FROM document_politicians WHERE politician_id = ?", PID)
        sup1 = q("SELECT COUNT(*) FROM document_politician_suppressions WHERE politician_id = ? AND lifted_at IS NULL", PID)
        roles = {}
        for r in wrong:
            roles[r["role"]] = roles.get(r["role"], 0) + 1
        print(f"Vēstneša saites pid {PID}: {linked}; kļūdainās (tikai izvēlne): {len(wrong)} {roles}; claims uz tām: {claims}")
        print(f"pid {PID} junction rindas: {dp0} -> {dp1}; aktīvas apspiešanas: {sup0} -> {sup1}")
        print("negative_patterns:", db.execute("SELECT negative_patterns FROM tracked_politicians WHERE id = ?", (PID,)).fetchone()[0])
        if dp0 - dp1 != len(wrong) or sup1 - sup0 != len(wrong):
            raise SystemExit("STOP: dzēsto/apspiesto skaits ≠ plānotais")
        if args.apply:
            if not args.rollback:
                raise SystemExit("STOP: --apply prasa --rollback")
            planned = sorted((int(a), b) for a, b in _ROW_RE.findall(Path(args.rollback).read_text(encoding="utf-8")))
            if planned != sorted((r["document_id"], r["role"]) for r in wrong):
                raise SystemExit(f"STOP: rollback rindas ({len(planned)}) ≠ šīs palaides ({len(wrong)})")
            db.execute("COMMIT")
            print("APPLIED")
        else:
            db.execute("ROLLBACK")
            print("DRY-RUN (atritināts)")
        return 0
    except BaseException:
        if db.in_transaction:
            db.execute("ROLLBACK")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
