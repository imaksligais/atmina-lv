#!/usr/bin/env python
"""Operatora eksplicītā publicēšanas atļauja vienam pārskatam (T15 atlikums).

Kāpēc šis eksistē. `deploy.sh` preflight sauc `check_output.py
--publish-gate-only`, un tā v1 patiesības avots bija `brief_images.approved=1`
— t.i. attēla apstiprinājums. Attēls pierāda TIKAI to, ka hero ir izvēlēts;
korektūra, quality-reviewer un CLAUDE.md § „Publish pause" atļauja tur nav.
Melnraksts ar apstiprinātu attēlu vārtus izietu. Šis CLI ieraksta to trūkstošo
faktu — un ir vienīgais `publish_approvals` rakstītājs.

Atslēga = blog lapas slugs, ne `context_notes.id`:
    dienas pārskats   2026-08-18
    nedēļas pārskats  nedela-2026-08-10
Tāpēc atļauja pārdzīvo brief pārģenerēšanu (UPSERT vai delete+insert ar jaunu
id) — tieši tā, kā to prasa BACKLOG § Deploy publish-gate.

Lietošana:
    .venv/Scripts/python.exe scripts/approve_publish.py 2026-08-18
    .venv/Scripts/python.exe scripts/approve_publish.py nedela-2026-08-10
    .venv/Scripts/python.exe scripts/approve_publish.py 2026-08-18 --revoke
    .venv/Scripts/python.exe scripts/approve_publish.py --list

Izejas kods: 0 = izdarīts, 1 = nekas netika ierakstīts/atsaukts.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from src.briefs import PUBLISH_KEY_RE  # noqa: E402
from src.db import DB_PATH, now_lv  # noqa: E402


def _connect(db_path: str | None) -> sqlite3.Connection:
    db = sqlite3.connect(db_path or DB_PATH)
    db.row_factory = sqlite3.Row
    # Vārti nedrīkst „iziet" tāpēc, ka tabulas nav — tā ir nemigrēta DB.
    exists = db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='publish_approvals'"
    ).fetchone()
    if not exists:
        db.close()
        raise SystemExit(
            "publish_approvals tabulas nav — palaid init_db() vai "
            "data/fix_publish_approvals_backfill_2026-08-18.sql"
        )
    return db


def _valid(key: str) -> bool:
    if PUBLISH_KEY_RE.match(key):
        return True
    print(
        f"nederīga atslēga: {key!r} — gaidīts 'YYYY-MM-DD' vai 'nedela-YYYY-MM-DD' "
        "(blog lapas slugs bez .html)",
        file=sys.stderr,
    )
    return False


def approve(key: str, db_path: str | None = None) -> int:
    if not _valid(key):
        return 1
    db = _connect(db_path)
    ts = now_lv()
    db.execute(
        "INSERT INTO publish_approvals (subject_key, approved_at) VALUES (?, ?)"
        " ON CONFLICT(subject_key) DO UPDATE SET approved_at = excluded.approved_at",
        (key, ts),
    )
    db.commit()
    db.close()
    print(f"apstiprināts publicēšanai: {key} ({ts})")
    return 0


def revoke(key: str, db_path: str | None = None) -> int:
    if not _valid(key):
        return 1
    db = _connect(db_path)
    cur = db.execute("DELETE FROM publish_approvals WHERE subject_key = ?", (key,))
    db.commit()
    n = cur.rowcount
    db.close()
    # Klusa veiksme ir defektu klase: „atsaukts", kad nekas netika atsaukts,
    # ir tieši tas signāls, kas liktu operatoram pārstāt skatīties.
    if n == 0:
        print(f"nav ko atsaukt: {key} nav publish_approvals", file=sys.stderr)
        return 1
    print(f"atsaukts: {key}")
    return 0


def list_recent(limit: int = 10, db_path: str | None = None) -> int:
    db = _connect(db_path)
    total = db.execute("SELECT COUNT(*) FROM publish_approvals").fetchone()[0]
    rows = db.execute(
        "SELECT subject_key, approved_at FROM publish_approvals"
        " ORDER BY approved_at DESC, subject_key DESC LIMIT ?",
        (limit,),
    ).fetchall()
    db.close()
    for r in rows:
        print(f"  {r['subject_key']:<22} {r['approved_at']}")
    print(f"publish_approvals: {total} apstiprinājumi kopā, rādīti {len(rows)}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("key", nargs="?",
                    help="blog lapas slugs: YYYY-MM-DD vai nedela-YYYY-MM-DD")
    ap.add_argument("--revoke", action="store_true", help="atsaukt apstiprinājumu")
    ap.add_argument("--list", action="store_true", help="pēdējie 10 apstiprinājumi")
    args = ap.parse_args()

    if args.list:
        return list_recent()
    if not args.key:
        ap.print_help()
        return 1
    return revoke(args.key) if args.revoke else approve(args.key)


if __name__ == "__main__":
    sys.exit(main())
