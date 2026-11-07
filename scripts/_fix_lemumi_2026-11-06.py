"""Operatora lēmumi 2026-11-06: Velps 753195, pretrunas #65 konteksts, saites T1.

  --apply  izpilda forward (izpildīts 2026-11-06; atsaka, ja rollback nav commitēts)

Rollback ir data/rollback_lemumi_2026-11-06.sql (uzrakstīts pirms izpildes, commits d9054825);
tā ģenerators izņemts, jo pēc izpildes tas ierakstītu jau izmainītās vērtības.

Pēc --apply: scripts/reembed_claims.py 753195 (stance mainīts).
#65 paliek confirmed=0; publicēšana ir atsevišķs operatora lēmums.
"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8")

from src.db import get_db  # noqa: E402

RB = Path("data/rollback_lemumi_2026-11-06.sql")

VELPS_ID = 753195
VELPS_STANCE = (
    "Komentējot cita lietotāja tvītu par to, ka nav nosaukta kebabnīca, kurā konstatēta tuberkuloze, "
    "un augstskola ar A hepatītu ēdnīcā, apgalvo: «Ja nav baltais tad nav \"notikuma\"», "
    "un uzskata, ka šī tendence pārņemta no kreisajiem medijiem Rietumos."
)
VELPS_REASONING = (
    "Izvērtēts 2026-11-06: tvīts citē cita lietotāja ierakstu par nenosauktu kebabnīcu un augstskolu "
    "(pārbaudīts X publiskajos datos), tāpēc konteksts ir zināms. Paša tvīts. Tēma ir tuvākā kanoniskā: "
    "runa ir par medijiem kopumā, atsevišķas vispārīgas mediju tēmas nav. Sākotnēji: reakcija bez "
    "redzama konteksta."
)
VELPS_CONFIDENCE = 0.7

CONTRADICTION_ID = 65
SUMMARY_OLD = "Saeimā atturēšanās neļauj veidot vairākumu.]"
SUMMARY_NEW = (
    "Saeimā atturēšanās neļauj veidot vairākumu. 2026. gada 15. oktobrī par 1573/Lp14 pirmajā lasījumā "
    "«Par» balsoja visi 80 balsotāji, arī JV un ZZS frakcijas, kuras decembrī šajos balsojumos atturējās.]"
)

# (dokuments, politiķis, kāpēc): teksts nav par šo personu.
REMOVE = [
    (150010, 241, "«kontrolē» kā darbības vārds, ne Valsts kontrole"),
    (149984, 150, "hokejists Šmits"),
    (150887, 234, "Toro (Thoreau)"),
    (149979, 297, "Keiša Lansa Botomsa"),
]
# Pieminēts, bet nav raksta galvenais varonis.
DEMOTE = [
    (150034, 204, "Igaunijas NBS komandieris; Latvijas armija tikai pieminēta"),
    (150030, 229, "Dombrovskis minēts kā vēstures piemērs"),
]


def _one(cur) -> int:
    assert cur.rowcount == 1, cur.rowcount
    return 1


def apply(db) -> None:
    tracked = subprocess.run(["git", "ls-files", "--error-unmatch", str(RB)], capture_output=True)
    dirty = subprocess.run(["git", "status", "--porcelain", "--", str(RB)], capture_output=True, text=True)
    if tracked.returncode or dirty.stdout.strip():
        sys.exit(f"rollback nav commitēts: {RB}")
    summary = db.execute("SELECT summary FROM contradictions WHERE id=?", (CONTRADICTION_ID,)).fetchone()[0]
    assert summary.count(SUMMARY_OLD) == 1, summary
    n = _one(db.execute("UPDATE claims SET stance=?, reasoning=?, confidence=? WHERE id=?",
                        (VELPS_STANCE, VELPS_REASONING, VELPS_CONFIDENCE, VELPS_ID)))
    n += _one(db.execute("UPDATE contradictions SET summary=? WHERE id=? AND confirmed=0",
                         (summary.replace(SUMMARY_OLD, SUMMARY_NEW), CONTRADICTION_ID)))
    for doc, pid, _ in REMOVE:
        n += _one(db.execute("DELETE FROM document_politicians WHERE document_id=? AND politician_id=? AND role='subject'", (doc, pid)))
    for doc, pid, _ in DEMOTE:
        n += _one(db.execute("UPDATE document_politicians SET role='mentioned' WHERE document_id=? AND politician_id=? AND role='subject'", (doc, pid)))
    db.commit()
    print(f"izmainītas {n} rindas (gaidīts 8)")
    print(db.execute("SELECT review_status, confidence FROM claims WHERE id=?", (VELPS_ID,)).fetchone()[:])
    for doc, pid, _ in REMOVE + DEMOTE:
        print(doc, pid, db.execute("SELECT role FROM document_politicians WHERE document_id=? AND politician_id=?", (doc, pid)).fetchall() and
              [r[0] for r in db.execute("SELECT role FROM document_politicians WHERE document_id=? AND politician_id=?", (doc, pid))],
              [r[:] for r in db.execute("SELECT role, scope, lifted_at FROM document_politician_suppressions WHERE document_id=? AND politician_id=?", (doc, pid))])


if __name__ == "__main__":
    conn = get_db()
    if "--apply" in sys.argv:
        apply(conn)
    else:
        sys.exit(__doc__)
