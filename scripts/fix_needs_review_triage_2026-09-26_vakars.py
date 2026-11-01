"""Vakara gājiens 2026-09-26: 2 NEEDS_REVIEW claims → Izvērtēts; konteksta piezīmes #647
labojums tajā pašā rutīnas dienā pirms publicēšanas (CLAUDE.md #8 otrais izņēmums).
Raksta rollback PIRMS piemērošanas. Palaid ar --apply, lai rakstītu DB."""
import sqlite3
import sys

DB = "data/atmina.db"
ROLLBACK = "data/rollback_needs_review_triage_2026-09-26_vakars.sql"
TAG = "Izvērtēts 2026-09-26:"

# id -> operatora piezīme (confidence nemainās)
DECISIONS = {
    724944: "avots Bražei skaidri piedēvē pievienošanos («Viņas teiktajam pievienojas arī Baiba Braže») un raķešu pieminējumu; divdomīgā rindkopa stance nav iekļauta. Pārskatā pasniegt kā pievienošanos Strubergas vērtējumam, ne kā pašas analīzi; 0.6 paliek, jo nostāja ir pārstāstīta, ne citēta.",
    724945: "pirmās personas tvīts; stance atkārto trīs tēzes, nepaplašinot saturu — pozīcija derīga, pārskatā neizvērst tālāk par tēzēm.",
}

NOTE_ID = 647
NOTE_OLD = ("vēl nav sanākusi; par draudiem koalīcijas darbam neviens nerunā. ")
NOTE_NEW = ("vēl nav sanākusi. Kleinbergs par koalīcijas stabilitāti ir pārliecināts. ")


def q(v):
    if v is None:
        return "NULL"
    if isinstance(v, (int, float)):
        return repr(v)
    return "'" + str(v).replace("'", "''") + "'"


db = sqlite3.connect(DB)
db.row_factory = sqlite3.Row
rows = {r["id"]: r for r in db.execute(
    f"SELECT id, reasoning, review_status FROM claims WHERE id IN ({','.join('?' * len(DECISIONS))})",
    list(DECISIONS),
)}
assert len(rows) == len(DECISIONS), f"atrasti {len(rows)} no {len(DECISIONS)}"
for cid, r in rows.items():
    assert r["review_status"] == "needs_review", (cid, r["review_status"])
    assert r["reasoning"].startswith("NEEDS_REVIEW:"), cid
    assert r["reasoning"].count("NEEDS_REVIEW") == 1, cid

note = db.execute("SELECT content, created_at FROM context_notes WHERE id = ? AND note_type = 'context'",
                  (NOTE_ID,)).fetchone()
assert note is not None
assert note["created_at"].startswith("2026-09-26"), note["created_at"]
assert note["content"].count(NOTE_OLD) == 1, "piezīmes teksts neatbilst gaidītajam"

with open(ROLLBACK, "w", encoding="utf-8") as f:
    f.write("-- Rollback: vakara NEEDS_REVIEW triāža 2026-09-26 (724944, 724945 → «Izvērtēts 2026-09-26:»)\n")
    f.write("-- + konteksta piezīmes #647 labojums pirms publicēšanas.\n")
    f.write("-- Forward: scripts/fix_needs_review_triage_2026-09-26_vakars.py, piemērots 2026-09-26.\n")
    f.write("-- review_status atvasina trigeris no reasoning — to ar roku NErakstām.\n")
    f.write("BEGIN;\n")
    for cid, r in sorted(rows.items()):
        f.write(f"UPDATE claims SET reasoning = {q(r['reasoning'])} WHERE id = {cid};\n")
    f.write(f"UPDATE context_notes SET content = {q(note['content'])} WHERE id = {NOTE_ID};\n")
    f.write("COMMIT;\n")
print("rollback uzrakstīts:", ROLLBACK)

if "--apply" in sys.argv:
    with db:
        for cid, note_text in DECISIONS.items():
            orig = rows[cid]["reasoning"][len("NEEDS_REVIEW:"):].strip()
            new = f"{TAG} {note_text} Sākotnējās šaubas: {orig}"
            assert "NEEDS_REVIEW" not in new
            db.execute("UPDATE claims SET reasoning = ? WHERE id = ?", (new, cid))
        db.execute("UPDATE context_notes SET content = ? WHERE id = ?",
                   (note["content"].replace(NOTE_OLD, NOTE_NEW), NOTE_ID))
    after = db.execute(
        f"SELECT id, review_status FROM claims WHERE id IN ({','.join('?' * len(DECISIONS))}) ORDER BY id",
        list(DECISIONS),
    ).fetchall()
    for a in after:
        print(tuple(a))
    ok = sum(1 for a in after if a["review_status"] == "reviewed")
    print(f"reviewed: {ok} no {len(DECISIONS)}")
    print("piezīme #647:", db.execute("SELECT content FROM context_notes WHERE id = ?", (NOTE_ID,)).fetchone()[0])
