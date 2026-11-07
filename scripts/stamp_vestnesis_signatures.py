#!/usr/bin/env python
"""Vēstneša paraksta-pāru zīmogs (`src/vestnesis_stamp.py`) — rutīnas solis pirms ekstrakcijas plāna.

Noklusējums: dry-run (tikai lasa DB, izdrukā skaitus). Kārtība (CLAUDE.md
escalation 8 — rollback commitē PIRMS izmaiņas):

    .venv/Scripts/python.exe scripts/stamp_vestnesis_signatures.py                  # 1. dry-run
    .venv/Scripts/python.exe scripts/stamp_vestnesis_signatures.py --write-rollback # 2. raksta rollback
    git commit data/rollback_vestnesis_stamp_<datums>.sql                           # 3. commit
    .venv/Scripts/python.exe scripts/stamp_vestnesis_signatures.py --apply          # 4. apply

`--apply` atsaka, ja rollback faila nav vai ja tā pāru kopa atšķiras no
pašreizējās (pāri starp dry-run un apply mainās; novecojis rollback nav rollback).
Zīmogs raksta tikai `document_politicians.extracted_at`, nekad `documents.reviewed_at`.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from src.briefs import current_routine_day  # noqa: E402
from src.db import get_db  # noqa: E402
from src.vestnesis_stamp import stamp_signature_only_pairs  # noqa: E402

_PAIR_LINE = re.compile(r"document_id = (\d+) AND politician_id = (\d+)")


def rollback_path(day: str) -> Path:
    return REPO / "data" / f"rollback_vestnesis_stamp_{day}.sql"


def rollback_sql(pairs: list[dict], day: str) -> str:
    lines = [
        f"-- Rollback: Vēstneša paraksta-pāru zīmogs {day} (scripts/stamp_vestnesis_signatures.py).",
        f"-- Forward: UPDATE document_politicians SET extracted_at = <now_lv> tieši šiem {len(pairs)} "
        "(doc, pid) subject pāriem; documents.reviewed_at netiek aiztikts.",
        f"-- Apply date: {day}. Atjauno extracted_at = NULL tikai šiem pāriem.",
        "BEGIN;",
    ]
    for p in pairs:
        lines.append(
            "UPDATE document_politicians SET extracted_at = NULL WHERE role = 'subject' "
            f"AND document_id = {int(p['doc_id'])} AND politician_id = {int(p['pid'])};"
        )
    lines.append("COMMIT;")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    ap = argparse.ArgumentParser(description="Vēstneša paraksta-pāru zīmogs (noklusējums dry-run).")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--write-rollback", action="store_true",
                   help="dry-run + uzraksta data/rollback_vestnesis_stamp_<datums>.sql")
    g.add_argument("--apply", action="store_true",
                   help="raksta extracted_at (prasa commitētu rollback ar to pašu pāru kopu)")
    ap.add_argument("--since", default=None, help="tikai doki ar scraped_at >= SINCE (LV laiks)")
    ap.add_argument("--list", action="store_true", help="izdrukāt visus pārus")
    args = ap.parse_args(argv)

    # Rutīnas diena (05:00 LV robeža), ne kalendārā: vakara rutīna bieži beidzas pēc
    # pusnakts, un rollback faila vārdam starp --write-rollback un --apply jāsakrīt.
    day = current_routine_day()
    rb = rollback_path(day)

    db = get_db()
    try:
        res = stamp_signature_only_pairs(db, dry_run=True, since=args.since)
        print(f"Vēstneša pāri bez ekstrakcijas un bez claim: {res['examined']}; "
              f"paraksta-pāri rutīnas aktos: {res['stamped']}")
        if args.list:
            for p in res["pairs"]:
                print(f"  • doc {p['doc_id']} — {p['name']} (pid {p['pid']}) — {p['title']}")

        if args.write_rollback:
            if not res["pairs"]:
                print("Nav ko atzīmēt — rollback fails netiek rakstīts.")
                return 0
            rb.parent.mkdir(parents=True, exist_ok=True)
            rb.write_text(rollback_sql(res["pairs"], day), encoding="utf-8")
            print(f"Rollback uzrakstīts: {rb}")
            print("Commitē to PIRMS --apply (CLAUDE.md escalation 8).")
            return 0

        if not args.apply:
            print("Dry-run — nekas nav rakstīts. Nākamais solis: --write-rollback.")
            return 0

        if not res["pairs"]:
            print("Nav ko atzīmēt.")
            return 0
        if not rb.exists():
            print(f"ATSAKU: nav rollback faila {rb}. Vispirms --write-rollback un commit.")
            return 2
        import subprocess
        tracked = subprocess.run(
            ["git", "ls-files", "--error-unmatch", rb.relative_to(REPO).as_posix()],
            cwd=REPO, capture_output=True,
        ).returncode == 0
        if not tracked:
            print(f"ATSAKU: {rb.name} nav commitēts (git ls-files). Commitē to PIRMS --apply.")
            return 2
        planned = {(int(d), int(p)) for d, p in _PAIR_LINE.findall(rb.read_text(encoding="utf-8"))}
        current = {(int(p["doc_id"]), int(p["pid"])) for p in res["pairs"]}
        if planned != current:
            print(f"ATSAKU: rollback pāru kopa ({len(planned)}) nesakrīt ar pašreizējo "
                  f"({len(current)}). Pārraksti ar --write-rollback un commitē vēlreiz.")
            return 2

        done = stamp_signature_only_pairs(db, dry_run=False, since=args.since)
        print(f"Atzīmēti pāri: {done['stamped']} no {done['examined']}. Rollback: {rb}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
