"""Operatora lēmums 2026-10-31 par trim NEEDS_REVIEW pozīcijām.

  752761 Kiršteins, 752771 Stendzenieks → NEEDS_REVIEW: → Izvērtēts (paturēt)
  752773 Krastiņa → DELETE (+ claim_vectors): nostāja nav nosakāma

  --write-rollback / --apply (atsaka bez commitēta rollback).
  Pēc rollback: scripts/reembed_claims.py 752773
"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8")

from src.db import get_db  # noqa: E402

RB = Path("data/rollback_operator_review_2026-10-31.sql")
MARK = "NEEDS_REVIEW:"
EVIDENCE = {
    752761: "operators 2026-10-31 apstiprina paturēt: paša publisks tvīts @akirstei; apgalvojums par žurnālisti ietīts «esot», citāts burtisks (operatora lēmums 2026-10-06 par asām pozīcijām)",
    752771: "operators 2026-10-31 apstiprina paturēt: paša tvīts; stance burtiski atstāsta sarakstu, autori nenosauc, faktu apgalvojumi ietīti «pēc viņa teiktā»",
}
DELETE_ID = 752773


def q(v):
    if v is None:
        return "NULL"
    if isinstance(v, (int, float)):
        return repr(v)
    return "'" + str(v).replace("'", "''") + "'"


def committed(p: Path) -> bool:
    if subprocess.run(["git", "ls-files", "--error-unmatch", str(p)], capture_output=True).returncode:
        return False
    return subprocess.run(["git", "diff", "--quiet", "HEAD", "--", str(p)]).returncode == 0


def main() -> int:
    db = get_db()
    if "--write-rollback" in sys.argv:
        out = ["-- Forward 2026-10-31 (operatora lēmums): 752761, 752771 NEEDS_REVIEW → Izvērtēts;",
               f"--   DELETE claims {DELETE_ID} (Krastiņa, doc 147552) + claim_vectors: «Jezu! Tiešām notiks brīnums?!» —",
               "--   nevar noteikt atzinību vai skepsi, nostājas nav (claim-extractor § 1). Tvīts paliek documents.",
               "BEGIN;"]
        for cid in EVIDENCE:
            r = db.execute("SELECT reasoning FROM claims WHERE id=?", (cid,)).fetchone()[0]
            assert r.startswith(MARK), cid
            out.append(f"UPDATE claims SET reasoning = {q(r)} WHERE id = {cid};")
        row = dict(db.execute("SELECT * FROM claims WHERE id=?", (DELETE_ID,)).fetchone())
        cols = ", ".join(row)
        vals = ", ".join(q(v) for v in row.values())
        out.append(f"INSERT INTO claims ({cols}) VALUES ({vals});")
        out.append("COMMIT;")
        out.append(f"-- pēc rollback: .venv/Scripts/python.exe scripts/reembed_claims.py {DELETE_ID}")
        RB.write_text("\n".join(out) + "\n", encoding="utf-8")
        print(f"rakstīts {RB}")
        return 0
    if "--apply" in sys.argv:
        if not committed(RB):
            print(f"ATSAKA: {RB} nav commitēts")
            return 1
        import sqlite_vec
        db.enable_load_extension(True)
        sqlite_vec.load(db)
        db.enable_load_extension(False)
        with db:
            for cid, ev in EVIDENCE.items():
                r = db.execute("SELECT reasoning FROM claims WHERE id=?", (cid,)).fetchone()[0]
                rest = r[len(MARK):].strip().replace("NEEDS_REVIEW", "marķieris")
                db.execute("UPDATE claims SET reasoning=? WHERE id=?",
                           (f"Izvērtēts 2026-10-31: {ev}. Sākotnēji: {rest}", cid))
            nv = db.execute("DELETE FROM claim_vectors WHERE claim_id=?", (DELETE_ID,)).rowcount
            nc = db.execute("DELETE FROM claims WHERE id=?", (DELETE_ID,)).rowcount
        st = [tuple(x) for x in db.execute("SELECT id, review_status FROM claims WHERE id IN (752761,752771,752773)")]
        print(f"dzēsts claims {nc}, claim_vectors {nv}; statuss: {st}")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
