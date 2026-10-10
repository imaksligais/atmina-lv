"""VAD resweep DRY-RUN: cik deklarāciju dzīvajā VID trūkst DB (tikai lasa).

Katram aktīvajam politiķim, kam ir vismaz viena `vad_declarations` rinda (vai
`--pids` sarakstam), palaiž `fetch_for_politician(dry_run=True)` pret dzīvo VID
ar parasto throttle (10 s starp meklēšanām) un izdrukā per-pid un kopā:
rows_found, present, new, ambiguous, duplicate_label, errors + jauno etiķešu sarakstu.

DB tiek atvērta TIKAI lasīšanai (`file:...?mode=ro`); `init_vad_tables()` NETIEK
saukts. Dry-run neielādē detaļas, tātad «new» = meklēšanas rindas, kuras
identitāte (`src.vad.fetch.declaration_identity`) neatbilst nevienai glabātai.

Usage:
    .venv/Scripts/python.exe scripts/vad_resweep_dryrun.py
    .venv/Scripts/python.exe scripts/vad_resweep_dryrun.py --pids 128,65,250
    .venv/Scripts/python.exe scripts/vad_resweep_dryrun.py --limit 5
"""

from __future__ import annotations

import argparse
import logging
import sqlite3
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from src.db import PRODUCTION_DB_PATH  # noqa: E402
from src.vad import VadClient, fetch_for_politician  # noqa: E402


def _parse_pids(value: str) -> list[int]:
    return [int(x) for x in value.replace(" ", "").split(",") if x]


def select_pids(db: sqlite3.Connection, pids: list[int] | None) -> list[tuple[int, str]]:
    if pids:
        marks = ",".join("?" * len(pids))
        return [(r["id"], r["name"]) for r in db.execute(
            f"SELECT id, name FROM tracked_politicians WHERE id IN ({marks}) ORDER BY name",
            pids)]
    # Tāds pats filtrs kā scripts/ingest_vad_declarations.py + jau ir VAD rindas.
    return [(r["id"], r["name"]) for r in db.execute(
        "SELECT id, name FROM tracked_politicians t "
        "WHERE (relationship_type IN ('tracked') OR relationship_type IS NULL) "
        "AND EXISTS (SELECT 1 FROM vad_declarations v WHERE v.opponent_id=t.id) "
        "ORDER BY name")]


def main(argv=None, *, client=None, db_path: str | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--pids", type=_parse_pids, help="komatatdalīti pid; noklusējums = visi ar VAD rindām")
    p.add_argument("--limit", type=int, help="max politiķi")
    args = p.parse_args(argv)
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")

    path = Path(db_path or (REPO_ROOT / PRODUCTION_DB_PATH)).resolve().as_posix()
    db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row

    politicians = select_pids(db, args.pids)
    if args.limit:
        politicians = politicians[: args.limit]
    print(f"[plan] {len(politicians)} politiķi, dry-run, DB tikai lasīšanai")

    keys = ("rows_found", "already_present", "new_inserted",
            "rows_ambiguous", "rows_duplicate_label", "errors")
    totals = dict.fromkeys(keys, 0)
    failed = 0
    started = time.monotonic()
    own_client = client is None
    if own_client:
        client = VadClient()
    try:
        for pid, name in politicians:
            try:
                res = fetch_for_politician(pid, db, client, dry_run=True)
            except Exception as e:
                print(f"[fail] {pid} {name}: {type(e).__name__}: {e}")
                failed += 1
                continue
            vals = {k: (len(res.errors) if k == "errors" else getattr(res, k)) for k in keys}
            for k in keys:
                totals[k] += vals[k]
            print(f"[pid {pid}] {name:<30} " + " ".join(f"{k}={v}" for k, v in vals.items()))
            for label in res.new_labels:
                print(f"    + {label}")
            for err in res.errors:
                print(f"    ! {err}")
    finally:
        if own_client:
            client.close()
        db.close()

    print(f"\n[total] politiķi={len(politicians)} fail={failed} "
          + " ".join(f"{k}={v}" for k, v in totals.items())
          + f" (~{(time.monotonic() - started) / 60:.1f} min)")
    return 0 if failed == 0 and totals["errors"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
