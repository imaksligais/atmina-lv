"""Aizpilda `coalition_periods` no Saeimas uzticības balsojumiem Ministru kabinetam.

Kāpēc: balsojumu lapas kartīte grupē frakcijas zem «Koalīcija»/«Opozīcija» pēc
valdības BALSOJUMA brīdī, ne pēc šodienas `parties.coalition_status` (plāns
docs/superpowers/plans/archive/2026-10-16-koalicija-balsojuma-diena.md). Tabula ir
patiesība; šis skripts ir tas, kā to aizpilda un vēlāk pārbauda.

Noteikums: katrs PIEŅEMTS balsojums `motif LIKE 'Uzticības izteikšana Ministru
kabinetam%'` sāk periodu no sava `vote_date`/`vote_time` (LV). Frakcija ir
koalīcijā, ja vairāk nekā puse tās balsojuma rindu ir «Par». Bez frakcijas
(NULL/'') nekad nav koalīcijas frakcija.

Ierobežojums: partijas iziešana no koalīcijas termiņa vidū (vai pievienošanās)
nenāk ar kabineta uzticības balsojumu — šis skripts to neredz. Tādu maiņu
pievieno ar roku rindu (`source_vote_id` NULL, `note` ar avotu) + pārī ar
`data/rollback_*.sql` (eskalācijas noteikums 8). Audit 24 brīdina, ja jaunākais
periods nesakrīt ar `parties.coalition_status`.

Lietošana:
    .venv/Scripts/python.exe scripts/seed_coalition_periods.py              # --dry-run (noklusējums), tikai lasa
    .venv/Scripts/python.exe scripts/seed_coalition_periods.py --apply      # pēc rollback commit
Rollback: data/rollback_coalition_periods_2026-10-16.sql.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.db import PRODUCTION_DB_PATH  # noqa: E402
from src.db_migrations import _apply_coalition_periods  # noqa: E402

CONFIDENCE_MOTIF = "Uzticības izteikšana Ministru kabinetam%"


def derive_periods(db: sqlite3.Connection) -> list[dict]:
    """→ [{source_vote_id, valid_from_date, valid_from_time, factions, counts}], vecākais pirmais."""
    out = []
    votes = db.execute(
        "SELECT id, vote_date, vote_time FROM saeima_votes "
        "WHERE motif LIKE ? AND result = 'Pieņemts' ORDER BY vote_date, vote_time",
        (CONFIDENCE_MOTIF,),
    ).fetchall()
    for vid, vdate, vtime in votes:
        rows = db.execute(
            """SELECT NULLIF(TRIM(faction), '') AS f,
                      SUM(vote = 'Par') AS par, COUNT(*) AS total
                 FROM saeima_individual_votes WHERE vote_id = ?
                GROUP BY NULLIF(TRIM(faction), '')""",
            (vid,),
        ).fetchall()
        counts = {f: (par, total) for f, par, total in rows if f}
        factions = sorted(f for f, (par, total) in counts.items() if par * 2 > total)
        out.append({"source_vote_id": vid, "valid_from_date": vdate,
                    "valid_from_time": vtime or "", "factions": factions, "counts": counts})
    return out


def stored_periods(db: sqlite3.Connection) -> dict[int, tuple]:
    try:
        rows = db.execute(
            "SELECT source_vote_id, valid_from_date, valid_from_time, factions "
            "FROM coalition_periods WHERE source_vote_id IS NOT NULL").fetchall()
    except sqlite3.OperationalError:
        return {}
    return {r[0]: (r[1], r[2], r[3]) for r in rows}


def _row(p: dict) -> tuple:
    return (p["valid_from_date"], p["valid_from_time"], ",".join(p["factions"]))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--db", default=PRODUCTION_DB_PATH)
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="tikai izdrukā (noklusējums)")
    mode.add_argument("--apply", action="store_true", help="ieraksta trūkstošās rindas")
    args = ap.parse_args(argv)

    uri = f"file:{Path(args.db).as_posix()}" + ("?mode=rw" if args.apply else "?mode=ro")
    db = sqlite3.connect(uri, uri=True)
    try:
        periods = derive_periods(db)
        stored = stored_periods(db)
        print(f"uzticības balsojumi (Pieņemts): {len(periods)}; jau tabulā: {len(stored)}")
        todo, conflicts = [], []
        for p in periods:
            detail = ", ".join(f"{f} {par}/{tot}" for f, (par, tot) in sorted(p["counts"].items()))
            state = ("jau ir" if stored.get(p["source_vote_id"]) == _row(p)
                     else "ATŠĶIRAS" if p["source_vote_id"] in stored else "jauns")
            print(f"  id {p['source_vote_id']} {p['valid_from_date']} {p['valid_from_time']} "
                  f"→ {', '.join(p['factions'])}  [{state}]  (Par/visi: {detail})")
            if state == "jauns":
                todo.append(p)
            elif state == "ATŠĶIRAS":
                conflicts.append(p)
        if conflicts:
            # Esošu rindu nepārraksta: atšķirība = roku labojums vai jauni dati — cilvēks izlemj.
            print(f"STOP: {len(conflicts)} rindas atšķiras no tabulas — nepārrakstu.")
            return 1
        if not periods:
            print("STOP: 0 uzticības balsojumu — motif vai dati mainījušies (T12), nevis tukšs rezultāts.")
            return 1
        if not args.apply:
            print(f"dry-run: ierakstītu {len(todo)} rindas. Ar --apply — pēc rollback commit.")
            return 0
        _apply_coalition_periods(db)
        with db:
            for p in todo:
                db.execute(
                    "INSERT INTO coalition_periods (valid_from_date, valid_from_time, factions, "
                    "source_vote_id, note) VALUES (?, ?, ?, ?, ?)",
                    (*_row(p), p["source_vote_id"],
                     "uzticības balsojums; frakcijas vairākums Par"),
                )
            after = stored_periods(db)
            missing = [p["source_vote_id"] for p in periods if after.get(p["source_vote_id"]) != _row(p)]
            if missing:
                raise RuntimeError(f"pēc ieraksta trūkst/atšķiras: {missing}")  # with → rollback
        print(f"ierakstītas {len(todo)} rindas; tabulā tagad {len(after)}.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
