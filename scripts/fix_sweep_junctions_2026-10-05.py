"""Hand fix 2026-10-05 (c) after the backlog sweep.

(1) DELETE claim 730569 (Krasta, Vēstnesis stenogram) — same 2026-08-20 Saeima speech as #703950.
(2) Every sweep claim (id >= 729966, position) whose author has no role='subject' junction on its
    document gets one (extracted_at = now); a 'mentioned' row for the same pair is removed, because
    the claim proves the person speaks there (subject = speaker, backlog/matcher.md § subject).
--write-rollback first (commit it), then --apply.
"""
import sys
import sqlite3
import sqlite_vec
from src.db import get_db, now_lv

ROLLBACK = "data/rollback_fix_sweep_junctions_2026-10-05.sql"

def q(v):
    return "NULL" if v is None else (str(v) if isinstance(v, (int, float)) else "'" + str(v).replace("'", "''") + "'")

db = get_db()
pairs = [tuple(r) for r in db.execute(
    "SELECT DISTINCT c.opponent_id, c.document_id FROM claims c WHERE c.id >= 729966 AND c.id != 730569 "
    "AND c.claim_type = 'position' AND c.document_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM document_politicians dp "
    "WHERE dp.document_id = c.document_id AND dp.politician_id = c.opponent_id AND dp.role = 'subject')")]
if "--write-rollback" in sys.argv:
    r = db.execute("SELECT * FROM claims WHERE id = 730569").fetchone()
    L = ["-- Rollback for scripts/fix_sweep_junctions_2026-10-05.py (applied 2026-10-05).",
         f"-- Forward: DELETE claim 730569 (dup of #703950); add role='subject' for {len(pairs)} (pid, doc) pairs, drop their 'mentioned' rows.",
         "-- After rollback re-embed: .venv/Scripts/python.exe scripts/reembed_claims.py 730569", "BEGIN;"]
    if r:
        cols = ", ".join(r.keys())
        vals = ", ".join(q(r[k]) for k in r.keys())
        L.append(f"INSERT INTO claims ({cols}) VALUES ({vals});")
    for pid, d in pairs:
        L.append(f"DELETE FROM document_politicians WHERE document_id={d} AND politician_id={pid} AND role='subject';")
        for m in db.execute("SELECT role, created_at, extracted_at, suspect_at FROM document_politicians "
                            "WHERE document_id=? AND politician_id=? AND role='mentioned'", (d, pid)):
            L.append("INSERT OR IGNORE INTO document_politicians (document_id, politician_id, role, created_at, extracted_at, suspect_at) "
                     f"VALUES ({d}, {pid}, 'mentioned', {q(m[1])}, {q(m[2])}, {q(m[3])});")
    L.append("COMMIT;")
    open(ROLLBACK, "w", encoding="utf-8", newline="\n").write("\n".join(L) + "\n")
    print("pairs", len(pairs), "rollback written")
if "--apply" in sys.argv:
    raw = sqlite3.connect("data/atmina.db")
    raw.enable_load_extension(True)
    sqlite_vec.load(raw)
    dv = raw.execute("DELETE FROM claim_vectors WHERE claim_id = 730569").rowcount
    dc = raw.execute("DELETE FROM claims WHERE id = 730569").rowcount
    raw.commit()
    raw.close()
    ts = now_lv()
    ins = dele = 0
    for pid, d in pairs:
        ins += db.execute("INSERT OR IGNORE INTO document_politicians (document_id, politician_id, role, extracted_at) "
                          "VALUES (?, ?, 'subject', ?)", (d, pid, ts)).rowcount
        dele += db.execute("DELETE FROM document_politicians WHERE document_id=? AND politician_id=? AND role='mentioned'",
                           (d, pid)).rowcount
    db.commit()
    print(f"claim deleted {dc} (vec {dv}); subject inserted {ins}/{len(pairs)}; mentioned removed {dele}")
