"""Hand fix 2026-10-05 (b): Lūse foreign links, Šlesers unlinked docs, subject-role inversions.

Writes data/rollback_fix_links_2026-10-05b.sql (snapshot of every touched
(document_id, politician_id) junction row) BEFORE applying. Run with --apply.
Evidence: docs/HANDOFF-2026-10-05-15saeima-seed.md § Nākamajai sesijai A.1–A.2,
context read in-session 2026-10-05.
"""
import sys
from src.db import get_db

DELETE = [  # (doc, pid, role)
    *[(d, 206, "mentioned") for d in (25955, 26219, 47635, 67543, 42842, 45468)],
    (123749, 3, "mentioned"), (123749, 10, "subject"),
    (124250, 56, "subject"), (124168, 56, "subject"), (124209, 3, "subject"),
    (124194, 3, "mentioned"), (124194, 56, "subject"), (124194, 69, "mentioned"),
    (124191, 6, "subject"), (124191, 69, "mentioned"),
    *[(124191, p, "mentioned") for p in (72, 18, 24, 183)],
]
INSERT = [
    *[(d, 3, "mentioned") for d in (123400, 123423, 123433, 123435, 124198, 124226)],
    (124192, 3, "subject"),
    (123749, 3, "subject"), (123749, 10, "mentioned"),
    (124250, 56, "mentioned"), (124168, 56, "mentioned"), (124209, 3, "mentioned"),
    (124194, 3, "subject"), (124194, 56, "mentioned"),
    (124191, 6, "mentioned"),
    *[(124191, p, "subject") for p in (72, 18, 24, 183)],
]

def q(v):
    return "NULL" if v is None else "'" + str(v).replace("'", "''") + "'"

db = get_db()
pairs = sorted({(d, p) for d, p, _ in DELETE + INSERT})
snap = []
for d, p in pairs:
    snap += [tuple(r) for r in db.execute(
        "SELECT document_id, politician_id, role, created_at, extracted_at, suspect_at "
        "FROM document_politicians WHERE document_id=? AND politician_id=?", (d, p))]
lines = ["-- Rollback for scripts/fix_links_2026-10-05b.py (applied 2026-10-05).",
         "-- Forward: delete 6 foreign Lūse (206) links; add Ainārs Šlesers (3) links to 7 docs;",
         "-- fix subject/mentioned inversions in 123749, 124250, 124168, 124209, 124194, 124191.",
         "BEGIN;"]
for d, p in pairs:
    lines.append(f"DELETE FROM document_politicians WHERE document_id={d} AND politician_id={p};")
for r in snap:
    lines.append("INSERT INTO document_politicians (document_id, politician_id, role, created_at, extracted_at, suspect_at) "
                 f"VALUES ({r[0]}, {r[1]}, {q(r[2])}, {q(r[3])}, {q(r[4])}, {q(r[5])});")
lines.append("COMMIT;")
if "--write-rollback" in sys.argv:
    open("data/rollback_fix_links_2026-10-05b.sql", "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("rollback rows", len(snap), "pairs", len(pairs))
if "--apply" in sys.argv:
    n_del = n_ins = 0
    for d, p, role in DELETE:
        n_del += db.execute("DELETE FROM document_politicians WHERE document_id=? AND politician_id=? AND role=?", (d, p, role)).rowcount
    for d, p, role in INSERT:
        n_ins += db.execute("INSERT OR IGNORE INTO document_politicians (document_id, politician_id, role) VALUES (?,?,?)", (d, p, role)).rowcount
    db.commit()
    print(f"deleted {n_del}/{len(DELETE)} inserted {n_ins}/{len(INSERT)}")
