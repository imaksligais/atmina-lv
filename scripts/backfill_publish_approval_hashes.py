#!/usr/bin/env python
"""Vienreizējs backfill: `publish_approvals.content_sha256` esošajām rindām (audits A1).

Kāpēc (2026-11-03). Kopš A1 apstiprinājums attiecas uz konkrētu saturu: deploy
preflight bloķē rindu bez heša. Rindas, kas ierakstītas pirms A1, heša nav, tāpēc
bez šī backfill katrs jau publicētais pārskats un Atradums bloķētu deploy.
Backfill ieraksta PAŠREIZĒJĀ satura hešu (`src.briefs.publish_content_hash`) —
tas ir saturs, kas jau ir live.

Raksta TIKAI rindām ar `content_sha256 IS NULL`. Rindas bez atrodama satura
paliek NULL un tiek uzskaitītas (orfāni vai lapas, kuru nav kokā) — neko nedzēš.

Rollback: data/rollback_publish_approval_hashes_2026-11-03.sql

Lietošana:
    .venv/Scripts/python.exe scripts/backfill_publish_approval_hashes.py            # --dry-run
    .venv/Scripts/python.exe scripts/backfill_publish_approval_hashes.py --apply
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from src.briefs import publish_content_hash  # noqa: E402
from src.db import DB_PATH  # noqa: E402


def backfill(db_path: str | Path, apply: bool, content_dir: Path | None = None) -> int:
    db = sqlite3.connect(db_path)
    cols = {r[1] for r in db.execute("PRAGMA table_info(publish_approvals)")}
    if "content_sha256" not in cols:
        db.close()
        print("publish_approvals.content_sha256 kolonnas nav — vispirms palaid init_db()",
              file=sys.stderr)
        return 1
    rows = db.execute(
        "SELECT subject_key FROM publish_approvals WHERE content_sha256 IS NULL"
        " ORDER BY subject_key").fetchall()
    total = db.execute("SELECT COUNT(*) FROM publish_approvals").fetchone()[0]
    filled: list[tuple[str, str]] = []
    without: list[str] = []
    for (key,) in rows:
        digest = publish_content_hash(db, key, content_dir=content_dir)
        if digest is None:
            without.append(key)
        else:
            filled.append((digest, key))
    if apply:
        cur = db.executemany(
            "UPDATE publish_approvals SET content_sha256 = ?"
            " WHERE subject_key = ? AND content_sha256 IS NULL", filled)
        db.commit()
        # Klusa veiksme ir defektu klase: rakstīto skaitu salīdzina ar nodomāto.
        if cur.rowcount != len(filled):
            print(f"KĻŪDA: atjaunotas {cur.rowcount} rindas, gaidītas {len(filled)}",
                  file=sys.stderr)
            db.close()
            return 1
    db.close()
    verb = "aizpildītas" if apply else "tiktu aizpildītas (--dry-run)"
    print(f"{total} rindas, {len(rows)} bez heša; {len(filled)} {verb}, "
          f"{len(without)} bez satura (atslēgas: {', '.join(without) or '—'})")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="ierakstīt (noklusējums: --dry-run)")
    ap.add_argument("--dry-run", action="store_true", help="tikai saskaitīt (noklusējums)")
    ap.add_argument("--db", default=None, help="DB ceļš (noklusējums: data/atmina.db)")
    args = ap.parse_args()
    return backfill(args.db or DB_PATH, apply=args.apply and not args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
