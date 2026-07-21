"""Surgical apply: write the matcher fix's attributable diff to document_politicians.

Two-pass attribution mirrors scripts/matcher_ab_versus_master.py:

  Pass 1 (--dump-new): run CURRENT matcher on all web/web_scraper/vestnesis
    docs, save (pid, role) per doc to .scratch/apply_new.json

  Pass 2 (--dump-old): run OLD matcher (caller checks out matcher.py at the
    pre-fix commit before invoking this), same dump shape, to .scratch/
    apply_old.json

  Pass 3 (--dry):  report planned junction changes vs current DB state,
    write audit log to .scratch/apply_audit.json. NO DB writes.

  Pass 4 (--apply): SAME as --dry but executes the writes in a single
    transaction. Idempotent: re-running on already-applied state is a
    no-op (since the diff vs OLD shrinks to zero).

Safety contract:
  * Only applies the fix-attributable diff (NEW \\ OLD insertions and
    OLD \\ NEW deletions). Does NOT touch junctions that differ from
    current DB state for unrelated reasons (stale-junction housekeeping
    stays out of scope).
  * Single transaction — atomic on the SQLite level.
  * Audit log records every (doc_id, pid, action, role) for paper trail.
  * Operator MUST take a DB backup before --apply.

Required preconditions:
  - data/atmina.db.backup-<date> exists (operator-confirmed)
  - .scratch/apply_new.json + .scratch/apply_old.json have been generated

Usage:
  python scripts/apply_matcher_fix.py --dump-new
  git checkout <pre-fix-ref> -- src/matcher.py
  python scripts/apply_matcher_fix.py --dump-old
  git checkout HEAD -- src/matcher.py
  python scripts/apply_matcher_fix.py --dry      # preview
  python scripts/apply_matcher_fix.py --apply    # writes
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from src.db import get_db
from src.matcher import (
    match_politicians,
    _filter_vestnesis_strict,
    _clear_politician_cache,
)

SCRATCH = Path(".scratch")
SCRATCH.mkdir(exist_ok=True)
PATH_NEW = SCRATCH / "apply_new.json"
PATH_OLD = SCRATCH / "apply_old.json"
PATH_AUDIT = SCRATCH / "apply_audit.json"


def _dump(label: str) -> None:
    path = SCRATCH / f"apply_{label}.json"
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT id, platform, content
        FROM documents
        WHERE platform IN ('web', 'web_scraper', 'vestnesis')
          AND content IS NOT NULL
          AND length(content) > 100
        ORDER BY id
    """)
    docs = cur.fetchall()
    db.close()
    _clear_politician_cache()
    out: dict[str, list[list]] = {}
    for i, doc in enumerate(docs, 1):
        if i % 1000 == 0:
            print(f"  {label}: {i}/{len(docs)}")
        matches = match_politicians(doc["content"])
        if doc["platform"] == "vestnesis":
            matches = _filter_vestnesis_strict(matches, doc["content"])
        if matches:
            out[str(doc["id"])] = [[pid, role] for pid, role in matches]
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Wrote {path} ({len(out)} docs)")


def _compute_diff() -> tuple[list[dict], Counter, Counter, dict]:
    """Return (operations, gained_by_pid, lost_by_pid, doc_meta).
    Each op is {doc_id, action: insert|delete, pid, role}."""
    if not PATH_NEW.exists() or not PATH_OLD.exists():
        raise SystemExit(
            f"Missing dumps. Run --dump-new and --dump-old first.\n"
            f"  Looked for {PATH_NEW} and {PATH_OLD}"
        )
    new_dump = json.loads(PATH_NEW.read_text(encoding="utf-8"))
    old_dump = json.loads(PATH_OLD.read_text(encoding="utf-8"))

    db = get_db()
    cur = db.cursor()
    junctions_by_doc: dict[int, set[int]] = defaultdict(set)
    junctions_with_role: dict[tuple[int, int], str] = {}
    cur.execute("SELECT document_id, politician_id, role FROM document_politicians")
    for r in cur.fetchall():
        junctions_by_doc[r["document_id"]].add(r["politician_id"])
        junctions_with_role[(r["document_id"], r["politician_id"])] = r["role"]
    pname = {
        r["id"]: r["name"]
        for r in cur.execute("SELECT id, name FROM tracked_politicians").fetchall()
    }
    db.close()

    operations: list[dict] = []
    gained_pids: Counter = Counter()
    lost_pids: Counter = Counter()

    all_doc_ids = set(new_dump) | set(old_dump)
    for doc_id_str in all_doc_ids:
        doc_id = int(doc_id_str)
        new_pairs = new_dump.get(doc_id_str, [])
        old_pairs = old_dump.get(doc_id_str, [])
        new_roles = {pid: role for pid, role in new_pairs}
        old_pids_set = {pid for pid, _ in old_pairs}
        new_pids_set = set(new_roles)
        gained = new_pids_set - old_pids_set
        lost = old_pids_set - new_pids_set
        if not gained and not lost:
            continue
        current_junction = junctions_by_doc.get(doc_id, set())
        # INSERT fix-gained pids that aren't already in junction.
        for pid in sorted(gained):
            if pid not in current_junction:
                operations.append({
                    "doc_id": doc_id,
                    "action": "insert",
                    "pid": pid,
                    "politician_name": pname.get(pid, f"???{pid}"),
                    "role": new_roles[pid],
                })
                gained_pids[pid] += 1
        # DELETE fix-lost pids that ARE currently in junction.
        for pid in sorted(lost):
            if pid in current_junction:
                operations.append({
                    "doc_id": doc_id,
                    "action": "delete",
                    "pid": pid,
                    "politician_name": pname.get(pid, f"???{pid}"),
                    "role": junctions_with_role.get((doc_id, pid), "?"),
                })
                lost_pids[pid] += 1
    return operations, gained_pids, lost_pids, pname


def _report(operations, gained, lost, pname) -> None:
    print()
    print("=" * 70)
    print(f"Fix-attributable junction changes vs current DB:")
    inserts = [op for op in operations if op["action"] == "insert"]
    deletes = [op for op in operations if op["action"] == "delete"]
    docs_touched = len({op["doc_id"] for op in operations})
    print(f"  Docs touched: {docs_touched}")
    print(f"  INSERTs:      {len(inserts)}")
    print(f"  DELETEs:      {len(deletes)}")
    print()
    print("Top 15 politicians GAINED:")
    for pid, c in gained.most_common(15):
        print(f"  +{c:>4}  id={pid:>4}  {pname.get(pid, '?')}")
    print()
    print("Top 15 politicians LOST:")
    for pid, c in lost.most_common(15):
        print(f"  -{c:>4}  id={pid:>4}  {pname.get(pid, '?')}")


def _audit(operations) -> None:
    PATH_AUDIT.write_text(
        json.dumps({
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "operations": operations,
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\nAudit log → {PATH_AUDIT}")


def _apply(operations) -> None:
    db = get_db()
    cur = db.cursor()
    try:
        cur.execute("BEGIN")
        for op in operations:
            if op["action"] == "insert":
                cur.execute(
                    "INSERT OR IGNORE INTO document_politicians "
                    "(document_id, politician_id, role) VALUES (?, ?, ?)",
                    (op["doc_id"], op["pid"], op["role"]),
                )
            elif op["action"] == "delete":
                cur.execute(
                    "DELETE FROM document_politicians "
                    "WHERE document_id = ? AND politician_id = ?",
                    (op["doc_id"], op["pid"]),
                )
        cur.execute("COMMIT")
        print(f"\nApplied {len(operations)} operations in one transaction.")
    except Exception:
        cur.execute("ROLLBACK")
        raise
    finally:
        db.close()


def main() -> int:
    p = argparse.ArgumentParser()
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--dump-new", action="store_true")
    g.add_argument("--dump-old", action="store_true")
    g.add_argument("--dry", action="store_true")
    g.add_argument("--apply", action="store_true")
    args = p.parse_args()

    if args.dump_new:
        _dump("new")
        return 0
    if args.dump_old:
        _dump("old")
        return 0

    operations, gained, lost, pname = _compute_diff()
    _report(operations, gained, lost, pname)
    _audit(operations)

    if args.apply:
        if not operations:
            print("\nNo changes to apply.")
            return 0
        _apply(operations)
    else:
        print("\n[DRY RUN] Re-run with --apply to commit these changes to DB.")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
