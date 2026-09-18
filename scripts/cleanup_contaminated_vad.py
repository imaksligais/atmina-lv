"""DELETE contaminated VAD declarations + targeted re-ingest.

Phase 1.5 F13 cleanup — 11 pidiem ielādēja sajauktu personu datus
homonīmu V+U dēļ. CASCADE no vad_declarations dzēš visas section rows.
Tālāk: ingest_vad_declarations.py --politician <each> ar svaigu disambig
filter ielādē tikai mūsu reālos politiķus.

VAD analīze sanācija (T1+) — pievienots --politician flag, lai cleanup
varētu apstrādāt arī Phase-1.5-pēc-fakta atklātus homonīmus (piem. pid=81
Mārtiņš Daģis, kur Jelgavas dome priekšsēdētāja Daģis (b. 1988) datus
sajauca ar Saeimas Daģis (b. 1976)).

Usage:
    python scripts/cleanup_contaminated_vad.py --dry-run                   # tikai count
    python scripts/cleanup_contaminated_vad.py                             # DELETE visi 11 F13 pids
    python scripts/cleanup_contaminated_vad.py --reingest                  # DELETE + sweep
    python scripts/cleanup_contaminated_vad.py --politician "Mārtiņš Daģis"  # tikai 1 pid pēc nosaukuma
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.db import get_db  # noqa: E402

CONTAMINATED_PIDS = [146, 101, 144, 104, 138, 106, 155, 92, 25, 132, 107]


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--reingest", action="store_true",
                   help="pēc DELETE palaiž ingest_vad_declarations.py per pid")
    p.add_argument("--politician",
                   help="name substring; ja norādīts, cleanup tikai 1 pid (citādi visi F13 pids)")
    args = p.parse_args()

    db = get_db()

    if args.politician:
        needle = args.politician.lower()
        rows = db.execute(
            "SELECT id, name FROM tracked_politicians WHERE LOWER(name) LIKE ?",
            (f"%{needle}%",),
        ).fetchall()
        if not rows:
            print(f"[fail] no tracked_politicians match {args.politician!r}")
            return 1
        if len(rows) > 1:
            names = ", ".join(f"{r['id']}:{r['name']}" for r in rows)
            print(f"[fail] {args.politician!r} matches {len(rows)} pids: {names}")
            return 1
        pids = [rows[0]["id"]]
        print(f"[plan] single-pid mode: pid={pids[0]} {rows[0]['name']}")
    else:
        pids = list(CONTAMINATED_PIDS)

    pids_csv = ",".join(str(p) for p in pids)
    n_before = db.execute(
        f"SELECT COUNT(*) FROM vad_declarations WHERE opponent_id IN ({pids_csv})"
    ).fetchone()[0]
    print(f"[plan] DELETE {n_before} declarations from {len(pids)} pid(s)")

    if args.dry_run:
        print("[dry-run] no changes")
        return 0

    db.execute(f"DELETE FROM vad_declarations WHERE opponent_id IN ({pids_csv})")
    db.commit()
    n_after = db.execute(
        f"SELECT COUNT(*) FROM vad_declarations WHERE opponent_id IN ({pids_csv})"
    ).fetchone()[0]
    print(f"[done] DELETE: {n_before} -> {n_after}")

    if not args.reingest:
        return 0

    print(f"\n[reingest] sweep {len(pids)} pid(s) ar disambig filter aktīvu")
    for i, pid in enumerate(pids, 1):
        row = db.execute(
            "SELECT name FROM tracked_politicians WHERE id=?", (pid,)
        ).fetchone()
        if not row:
            print(f"[skip] pid={pid} not found")
            continue
        slug_arg = row["name"]
        t0 = time.monotonic()
        print(f"\n[{i}/{len(pids)}] pid={pid} {row['name']}")
        rc = subprocess.call([
            sys.executable, str(REPO_ROOT / "scripts" / "ingest_vad_declarations.py"),
            "--politician", slug_arg,
        ])
        print(f"  exit={rc} ({time.monotonic()-t0:.1f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
