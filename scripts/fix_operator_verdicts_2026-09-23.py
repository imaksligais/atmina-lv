"""Operatora lēmumi 2026-09-23 (rīta rutīnas atradumi).

1. #717978 Stepaņenko — paturēt; NEEDS_REVIEW -> Izvērtēts (precedents #715773).
2. #717852 Rinkēvičs — dzēst (biroja balss: padomnieks Drēģeris, slēgta tikšanās; paša tvīts
   113457 apstiprina tikai vispārīgu atbalstu Ukrainai). Publicētais 22.09 pārskats netiek labots.
3. Junction (110049, 146) dzēsts — rakstā runā Kaspars Bērziņš (SM), «Andris» tekstā nav.
4. #717787 Kučinskis — confidence 0.65 -> 0.6 (bez citāta griesti) + Izvērtēts; stance nemainās.
Rollback: data/rollback_operator_verdicts_2026-09-23.sql (pēc tam reembed 717852).
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import sqlite_vec

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "atmina.db"
RB = ROOT / "data" / "rollback_operator_verdicts_2026-09-23.sql"
COLS = ["id", "opponent_id", "document_id", "topic", "stance", "quote", "confidence", "reasoning",
        "salience", "source_url", "stated_at", "created_at", "claim_type", "speaker_id", "party_id"]


def lit(v):
    if v is None:
        return "NULL"
    if isinstance(v, (int, float)):
        return repr(v)
    return "'" + str(v).replace("'", "''") + "'"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    db = sqlite3.connect(DB)
    db.enable_load_extension(True)
    sqlite_vec.load(db)
    rin = db.execute(f"SELECT {', '.join(COLS)} FROM claims WHERE id=717852").fetchone()
    ste = db.execute("SELECT reasoning FROM claims WHERE id=717978").fetchone()[0]
    kuc = db.execute("SELECT confidence, reasoning FROM claims WHERE id=717787").fetchone()
    jn = db.execute("SELECT document_id, politician_id, role, created_at, extracted_at, suspect_at "
                    "FROM document_politicians WHERE document_id=110049 AND politician_id=146").fetchone()
    assert rin and jn and ste.startswith("NEEDS_REVIEW: ") and kuc[0] == 0.65
    RB.write_text(
        "-- Rollback: scripts/fix_operator_verdicts_2026-09-23.py (piemērots 2026-09-23)\n"
        "-- PĒC TAM: .venv/Scripts/python.exe scripts/reembed_claims.py 717852\nBEGIN;\n"
        f"INSERT INTO claims ({', '.join(COLS)}) VALUES ({', '.join(lit(v) for v in rin)});\n"
        f"UPDATE claims SET reasoning={lit(ste)} WHERE id=717978;\n"
        f"UPDATE claims SET confidence={lit(kuc[0])}, reasoning={lit(kuc[1])} WHERE id=717787;\n"
        "INSERT INTO document_politicians (document_id, politician_id, role, created_at, extracted_at, suspect_at) "
        f"VALUES ({', '.join(lit(v) for v in jn)});\nCOMMIT;\n", encoding="utf-8")
    with db:
        db.execute("DELETE FROM claim_vectors WHERE claim_id=717852")
        db.execute("DELETE FROM claims WHERE id=717852")
        db.execute("UPDATE claims SET reasoning=? WHERE id=717978", (
            "Izvērtēts 2026-09-23 (operatora lēmums): paturēts — atteikums nosaukt agresoru ir publisks runas akts, "
            "tas pats paraugs kā #715773. " + ste[len("NEEDS_REVIEW: "):],))
        db.execute("UPDATE claims SET confidence=0.6, reasoning=? WHERE id=717787", (
            "Izvērtēts 2026-09-23: stance pārbaudīts pret avotu (pmo.ee/de facto) un atbilst; confidence 0,65→0,6, "
            "jo tieša citāta nav. " + kuc[1],))
        db.execute("DELETE FROM document_politicians WHERE document_id=110049 AND politician_id=146")
    print("717852 left:", db.execute("SELECT COUNT(*) FROM claims WHERE id=717852").fetchone()[0],
          "vec left:", db.execute("SELECT COUNT(*) FROM claim_vectors WHERE claim_id=717852").fetchone()[0])
    print("717978:", db.execute("SELECT review_status FROM claims WHERE id=717978").fetchone())
    print("717787:", db.execute("SELECT confidence, review_status FROM claims WHERE id=717787").fetchone())
    print("junction left:", db.execute("SELECT COUNT(*) FROM document_politicians WHERE document_id=110049 AND politician_id=146").fetchone()[0])


if __name__ == "__main__":
    main()
