"""Diff NEW matcher output against OLD matcher output on same docs.

Step 1: dump new-matcher output per doc to .scratch/match_new.json
Step 2: git stash (to revert matcher.py), re-run with dump_old, then git stash pop
Step 3: diff new vs old to attribute changes to MY FIX specifically
       (vs pre-existing matcher-vs-junction drift from stale rescans)

Usage:
    PYTHONPATH=. python scripts/matcher_ab_versus_master.py new
    # then in shell: git stash
    PYTHONPATH=. python scripts/matcher_ab_versus_master.py old
    # then in shell: git stash pop
    PYTHONPATH=. python scripts/matcher_ab_versus_master.py diff
"""
import json
import sys
from collections import Counter
from pathlib import Path

from src.db import get_db
from src.matcher import match_politicians, _filter_vestnesis_strict, _clear_politician_cache

OUT_DIR = Path(".scratch")
OUT_DIR.mkdir(exist_ok=True)


def dump(label: str) -> None:
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
    out: dict[str, list[int]] = {}
    for i, doc in enumerate(docs, 1):
        if i % 1000 == 0:
            print(f"  {label}: {i}/{len(docs)}")
        matches = match_politicians(doc["content"])
        if doc["platform"] == "vestnesis":
            matches = _filter_vestnesis_strict(matches, doc["content"])
        pids = sorted({pid for pid, _ in matches})
        if pids:
            out[str(doc["id"])] = pids
    path = OUT_DIR / f"match_{label}.json"
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Wrote {path} ({len(out)} docs with matches)")


def diff() -> None:
    new = json.loads((OUT_DIR / "match_new.json").read_text(encoding="utf-8"))
    old = json.loads((OUT_DIR / "match_old.json").read_text(encoding="utf-8"))
    all_doc_ids = set(new) | set(old)
    fix_gains_by_pid: Counter = Counter()
    fix_losses_by_pid: Counter = Counter()
    docs_changed = 0
    for doc_id in all_doc_ids:
        new_set = set(new.get(doc_id, []))
        old_set = set(old.get(doc_id, []))
        if new_set == old_set:
            continue
        docs_changed += 1
        for pid in new_set - old_set:
            fix_gains_by_pid[pid] += 1
        for pid in old_set - new_set:
            fix_losses_by_pid[pid] += 1

    db = get_db()
    pname = {r["id"]: r["name"] for r in db.execute("SELECT id, name FROM tracked_politicians").fetchall()}
    db.close()

    print(f"Docs changed by MY FIX: {docs_changed}")
    print(f"\nGAINED specifically due to my fix:")
    for pid, c in fix_gains_by_pid.most_common(20):
        print(f"  +{c:>5}  id={pid:>4}  {pname.get(pid, '?')}")
    print(f"\nLOST specifically due to my fix:")
    for pid, c in fix_losses_by_pid.most_common(20):
        print(f"  -{c:>5}  id={pid:>4}  {pname.get(pid, '?')}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "diff"
    if cmd == "new":
        dump("new")
    elif cmd == "old":
        dump("old")
    elif cmd == "diff":
        diff()
    else:
        print("Usage: matcher_ab_versus_master.py [new|old|diff]")
        sys.exit(1)
