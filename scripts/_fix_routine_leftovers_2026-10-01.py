"""Rutīnas atlikumu 09-16…09-25 triāža (verdikts D8, 2026-10-01): tikai tas, kas dzīvs vietnē un skaidri nepareizs.

1. Junction (110020, 116, 'subject') DZĒST — pmo.ee «Rudzu Rīga» runā par komiķi Emīlu Gati Liepiņu, ne
   pid=116 Gati Liepiņu; doks bija 1. vietā pid=116 profila ziņās (T1). 0 claims.
2. Junction (110109, 181) 'subject' → 'mentioned' — jauns.lv raksts par Jozānu; Bartaševičs tikai pieminēts kā
   saraksta līderis (CHANGELOG 2026-09-07 (7): `subject` prasa runātāju). 0 claims.
3. #717893 Judins — «darba dalībnieks» → «priekšsēdētājs» (verificēts: doc 81491, 72466 — Saeimas Juridiskās
   komisijas priekšsēdētājs Andrejs Judins).
4. #717850 Krastiņa — trūkstošais prievārds: «… urnām «nekāda jēga»» → «no … urnām «nekāda jēga»».
#704185 (Valsts kontrole) NEdzēš: claim reasoning to lasa kā apņemšanos ar tvērumu un termiņu
(`sloti.md` to atļauj) — divdomīgs, ne skaidri nepareizs.

Sausā palaide pēc noklusējuma; `--apply` raksta. Rollback: data/rollback_routine_leftovers_2026-10-01.sql
(jābūt uz diska PIRMS --apply). Pēc --apply: scripts/reembed_claims.py 717893 717850.
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.db import get_db  # noqa: E402

ROLLBACK = ROOT / "data/rollback_routine_leftovers_2026-10-01.sql"

STANCE_FIXES = {
    717893: (
        "Kā Saeimas Juridiskās komisijas darba dalībnieks atbalsta",
        "Kā Saeimas Juridiskās komisijas priekšsēdētājs atbalsta",
    ),
    717850: (
        "Uzskata, ka Latvijas Valsts ceļu izvietotajām atvērta tipa urnām",
        "Uzskata, ka no Latvijas Valsts ceļu izvietotajām atvērta tipa urnām",
    ),
}


def main(apply: bool) -> None:
    db = get_db(None)
    import sqlite_vec
    db.enable_load_extension(True)
    sqlite_vec.load(db)
    db.enable_load_extension(False)

    problems = []
    j1 = db.execute(
        "SELECT count(*) FROM document_politicians WHERE document_id=110020 AND politician_id=116 AND role='subject'"
    ).fetchone()[0]
    j2 = db.execute(
        "SELECT count(*) FROM document_politicians WHERE document_id=110109 AND politician_id=181 AND role='subject'"
    ).fetchone()[0]
    j2m = db.execute(
        "SELECT count(*) FROM document_politicians WHERE document_id=110109 AND politician_id=181 AND role='mentioned'"
    ).fetchone()[0]
    c_j = db.execute(
        "SELECT count(*) FROM claims WHERE (opponent_id=116 AND document_id=110020) OR (opponent_id=181 AND document_id=110109)"
    ).fetchone()[0]
    print(f"junction 110020/116 subject: {j1} (gaida 1); 110109/181 subject: {j2} (gaida 1), mentioned: {j2m} (gaida 0); claims uz tiem: {c_j} (gaida 0)")
    if (j1, j2, j2m, c_j) != (1, 1, 0, 0):
        problems.append("junction stāvoklis neatbilst")

    for cid, (old, new) in STANCE_FIXES.items():
        stance = db.execute("SELECT stance FROM claims WHERE id=?", (cid,)).fetchone()
        ok = stance is not None and stance[0].count(old) == 1
        print(f"#{cid}: vecā frāze {'atrasta 1x' if ok else 'NAV / nav unikāla'}")
        if not ok:
            problems.append(f"#{cid} stance")


    if problems:
        sys.exit("STOP: " + "; ".join(problems))
    if not apply:
        print("Sausā palaide — nekas nav rakstīts. Lieto --apply.")
        return
    if not ROLLBACK.exists():
        sys.exit(f"STOP: rollback {ROLLBACK} nav uz diska")

    with db:
        n = db.execute(
            "DELETE FROM document_politicians WHERE document_id=110020 AND politician_id=116 AND role='subject'"
        ).rowcount
        n += db.execute(
            "UPDATE document_politicians SET role='mentioned' WHERE document_id=110109 AND politician_id=181 AND role='subject'"
        ).rowcount
        for cid, (old, new) in STANCE_FIXES.items():
            n += db.execute("UPDATE claims SET stance=replace(stance, ?, ?) WHERE id=?", (old, new, cid)).rowcount
    expected = 1 + 1 + len(STANCE_FIXES)
    print(f"Rakstītas rindas: {n} (gaidīts {expected})")
    if n != expected:
        sys.exit("BRĪDINĀJUMS: rindu skaits nesakrīt — pārbaudi un, ja vajag, palaid rollback")
    print("Tālāk: .venv/Scripts/python.exe scripts/reembed_claims.py 717893 717850")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    main(ap.parse_args().apply)
