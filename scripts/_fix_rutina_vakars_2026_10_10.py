"""Vakara rutīna 2026-10-10, solis 2c: NEEDS_REVIEW izvērtēšana (737542, 737543,
737547, 737548), stance labojumi (737544 Kols ≤45 vārdi, 737545 Vītols laiks,
737547 Velps, 737554 Stendzenieks + stated_at), Bergholca dublikāta 737561 dzēšana.

--rollback raksta data/rollback_rutina_vakars_2026-10-10.sql, --apply izpilda.
Pēc --apply: scripts/reembed_claims.py 737544 737545 737547 737554.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import sqlite_vec

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
DB_PATH = ROOT / "data" / "atmina.db"
ROLLBACK = ROOT / "data" / "rollback_rutina_vakars_2026-10-10.sql"
MARK = "NEEDS_REVIEW: "

REVIEW = {
    737542: "Izvērtēts 2026-10-10: paša tvīts pirmajā personā (doc 130700); stance materiālu nenosauc, tāpēc konteksta trūkums to nepadara plašāku. ",
    737543: "Izvērtēts 2026-10-10: paša tvīts (doc 130729), nostāja par Trampa administrāciju izteikta tieši; jautājumi stance atstāti kā jautājumi. ",
    737547: "Izvērtēts 2026-10-10: konteksts ir Trampa 10-09 paziņotā vienošanās ar Putinu par Krievijas dīzeļdegvielas piegādēm (doc 130639, arī Kola 130666). ",
    737548: "Izvērtēts 2026-10-10: atbilde atzīmē @KasparsGorkss tajā dienā, kad apspriesta viņa virzīšana Valsts kancelejas direktora amatam (737550, 737551, 737564). ",
}

STANCE = {
    737544: "Uzskata, ka Krievijas dīzeļdegvielas jautājumā Eiropai nav jāseko Vašingtonai — ne vienas mucas, ne viena izņēmuma; apgalvo, ka šis apjoms ir mazāks par divu stundu pasaules pieprasījumu, cenu nesamazinās un ieguvēja būs tikai puse, kurai pierādīts, ka zvērības nemaksā ilgstošu cenu.",
    737545: "Uzskata, ka Francijas parāda problēmas tieši ietekmē Latviju kā eirozonas valsti: Latvijas aizņemšanās likme, ja aizņemtos tagad, palēkusies par 0,7 % jeb 7 miljoniem eiro gadā uz katru miljardu; Francija, atšķirībā no Grieķijas, ir pārāk liela, lai to izglābtu ar citu naudu.",
    737547: "Uzskata, ka Putins atkal apspēlējis Trampu: piegādes esot niecīgas pret patēriņu, un Krievija, viņaprāt, pat tās nespēs piegādāt un paziņos, ka savu vienošanās daļu nevar izpildīt Ukrainas dēļ.",
    737554: "Kritizē premjera amata kandidātu Andri Kulbergu, ko vēlēšanu nakts diskusijā raksturo kā politiķi, kurš mēģina patikt visiem, mainīgi atbild arī par viendzimuma laulību un popularitātes dēļ bieži upurē valsts pārmaiņu un reformu procesu.",
}
STATED_AT = {737554: "2026-10-03 00:00:00"}  # nra.lv vēlēšanu nakts tiešraide (vēlēšanas 2026-10-03)
DELETE_ID, DELETE_DOC = 737561, 130723  # dublē 731042 (tas pats 09-30 izteikums, doc 128429)
LEAVE = (737546, 737562)  # operatoram: apmelošanas risks / konteksts nav atrodams


def q(v):
    if v is None:
        return "NULL"
    if isinstance(v, (int, float)):
        return str(v)
    return "'" + str(v).replace("'", "''") + "'"


def main(mode: str) -> None:
    db = sqlite3.connect(DB_PATH)
    db.enable_load_extension(True)
    sqlite_vec.load(db)
    plan = []
    for cid, prefix in REVIEW.items():
        r = db.execute("SELECT reasoning FROM claims WHERE id=?", (cid,)).fetchone()[0]
        assert r.startswith(MARK), (cid, r[:40])
        rest = r[len(MARK):]
        assert "NEEDS_REVIEW" not in rest, cid
        plan.append((cid, r, prefix + "Sākotnēji: " + rest))
    for cid, s in STANCE.items():
        assert len(s.split()) <= 45, (cid, len(s.split()))
    old_stance = {cid: db.execute("SELECT stance FROM claims WHERE id=?", (cid,)).fetchone()[0]
                  for cid in STANCE}
    old_stated = {cid: db.execute("SELECT stated_at FROM claims WHERE id=?", (cid,)).fetchone()[0]
                  for cid in STATED_AT}
    cols = [c[1] for c in db.execute("PRAGMA table_info(claims)")]
    row = db.execute(f"SELECT {','.join(cols)} FROM claims WHERE id=?", (DELETE_ID,)).fetchone()
    assert row is not None and row[cols.index("document_id")] == DELETE_DOC, row
    assert db.execute("SELECT COUNT(*) FROM claims WHERE id=731042").fetchone()[0] == 1
    deps = db.execute("SELECT COUNT(*) FROM contradictions WHERE claim_old_id=? OR claim_new_id=?",
                      (DELETE_ID, DELETE_ID)).fetchone()[0]
    assert deps == 0, deps

    if mode == "--rollback":
        lines = [
            "-- Forward (2026-10-10 vakarā, rutīnas solis 2c, nekad nav deployots): scripts/_fix_rutina_vakars_2026_10_10.py",
            "--   claims 737542, 737543, 737547, 737548: reasoning NEEDS_REVIEW → «Izvērtēts 2026-10-10: … Sākotnēji: …»;",
            "--   stance labojumi 737544 (≤45 vārdi), 737545 (tagadne kā avotā), 737547 (bez konteksta piezīmes), 737554 (sākas ar verbu);",
            "--   737554 stated_at 2026-10-10 → 2026-10-03 (vēlēšanu nakts diskusija);",
            "--   737561 (Bergholcs) dzēsts: dublē 731042 (tas pats 09-30 izteikums angliski, doc 130723).",
            "-- Pēc rollback: .venv/Scripts/python.exe scripts/reembed_claims.py 737544 737545 737547 737554 737561",
            "BEGIN;",
        ]
        for cid, old, _ in plan:
            lines.append(f"UPDATE claims SET reasoning = {q(old)} WHERE id = {cid};")
        for cid, s in old_stance.items():
            lines.append(f"UPDATE claims SET stance = {q(s)} WHERE id = {cid};")
        for cid, s in old_stated.items():
            lines.append(f"UPDATE claims SET stated_at = {q(s)} WHERE id = {cid};")
        lines.append(f"INSERT INTO claims ({', '.join(cols)}) VALUES ({', '.join(q(v) for v in row)});")
        lines.append("COMMIT;")
        ROLLBACK.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print("rollback", ROLLBACK.name)
    elif mode == "--apply":
        assert ROLLBACK.exists()
        with db:
            for cid, old, new in plan:
                assert db.execute("UPDATE claims SET reasoning=? WHERE id=? AND reasoning=?",
                                  (new, cid, old)).rowcount == 1
            for cid, s in STANCE.items():
                assert db.execute("UPDATE claims SET stance=? WHERE id=?", (s, cid)).rowcount == 1
            for cid, s in STATED_AT.items():
                assert db.execute("UPDATE claims SET stated_at=? WHERE id=?", (s, cid)).rowcount == 1
            db.execute("DELETE FROM claim_vectors WHERE claim_id=?", (DELETE_ID,))
            assert db.execute("DELETE FROM claims WHERE id=?", (DELETE_ID,)).rowcount == 1
        for cid in (*REVIEW, *LEAVE):
            print(cid, db.execute("SELECT review_status FROM claims WHERE id=?", (cid,)).fetchone())
        print("deleted", DELETE_ID, db.execute("SELECT COUNT(*) FROM claims WHERE id=?", (DELETE_ID,)).fetchone()[0] == 0)
    else:
        print(len(plan), "reasoning;", len(STANCE), "stance;", "delete", DELETE_ID)
        for cid, s in STANCE.items():
            print(cid, len(s.split()), "vārdi")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "--dry")
