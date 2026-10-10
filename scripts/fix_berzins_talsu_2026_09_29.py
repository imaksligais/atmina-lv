"""Vienreizējs labojums 2026-09-29 (operatora atļauja tajā pašā dienā): pid 146 Andris Bērziņš.

Talsu novada domes priekšsēdētāja «A. Bērziņš» paraksts Vēstneša saistošajos noteikumos
sasaistīts ar Saeimas deputātu (backlog/dati-db.md a9). Esošais negative_pattern
«Talsu novada domes priekšsēdētājs» neķer formu «Talsu novada PAŠVALDĪBAS domes priekšsēdētājs».

1) pievieno negative_pattern ar pilno parakstu;
2) dzēš junction rindas dokiem, kuros VISI «Bērziņ» trāpījumi ir šajā parakstā (pozitīvs
   pierādījums, T19) un pid 146 nav neviena claim.
Rollback: data/rollback_berzins_talsu_2026-09-29.sql. Palaišana: --apply (bez tā — dry-run).
"""
import json
import sys
from pathlib import Path
from src.db import get_db

PID = 146
SIG = "Talsu novada pašvaldības domes priekšsēdētājs A. Bērziņš"
PATTERN = SIG
ROLLBACK = Path("data/rollback_berzins_talsu_2026-09-29.sql")


def q(v):
    return "NULL" if v is None else "'" + str(v).replace("'", "''") + "'"


def main(apply: bool):
    db = get_db(None)
    neg_old = db.execute("SELECT negative_patterns FROM tracked_politicians WHERE id=?", (PID,)).fetchone()[0]
    neg = json.loads(neg_old) if neg_old else []
    assert PATTERN not in neg, "pattern jau ir"
    rows = db.execute(
        "SELECT dp.*, d.content FROM document_politicians dp JOIN documents d ON d.id=dp.document_id "
        "WHERE dp.politician_id=? AND d.content LIKE ?", (PID, f"%{SIG}%")).fetchall()
    victims = []
    for r in rows:
        c = r["content"]
        if c.count("Bērziņ") != c.count(SIG):
            sys.exit(f"STOP: doc {r['document_id']} satur «Bērziņ» ārpus paraksta")
        n = db.execute("SELECT COUNT(*) FROM claims WHERE opponent_id=? AND document_id=?",
                       (PID, r["document_id"])).fetchone()[0]
        if n:
            sys.exit(f"STOP: doc {r['document_id']} ir {n} claims pid {PID}")
        victims.append(r)
    print(f"pārbaudīti {len(rows)} doki, dzēšami {len(victims)} junction; pattern → {len(neg)}+1")
    if not apply:
        return
    cols = ["document_id", "politician_id", "role", "created_at", "extracted_at", "suspect_at"]
    lines = ["-- Rollback: scripts/fix_berzins_talsu_2026_09_29.py (apply 2026-09-29).",
             f"-- Atjauno pid {PID} negative_patterns un {len(victims)} dzēstās junction rindas.",
             "BEGIN;",
             f"UPDATE tracked_politicians SET negative_patterns = {q(neg_old)} WHERE id = {PID};"]
    for r in victims:
        lines.append(f"INSERT INTO document_politicians ({', '.join(cols)}) VALUES "
                     f"({', '.join(q(r[c]) for c in cols)});")
    lines.append("COMMIT;")
    ROLLBACK.write_text("\n".join(lines) + "\n", encoding="utf-8")
    with db:
        db.execute("UPDATE tracked_politicians SET negative_patterns=? WHERE id=?",
                   (json.dumps(neg + [PATTERN], ensure_ascii=False), PID))
        for r in victims:
            db.execute("DELETE FROM document_politicians WHERE document_id=? AND politician_id=? AND role=?",
                       (r["document_id"], PID, r["role"]))
    left = db.execute("SELECT COUNT(*) FROM document_politicians dp JOIN documents d ON d.id=dp.document_id "
                      "WHERE dp.politician_id=? AND d.content LIKE ?", (PID, f"%{SIG}%")).fetchone()[0]
    print(f"applied; atlikušas {left}; rollback -> {ROLLBACK}")


if __name__ == "__main__":
    main("--apply" in sys.argv)
