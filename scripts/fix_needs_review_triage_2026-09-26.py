"""NEEDS_REVIEW triāža 2026-09-26: 10 claims → Izvērtēts; 3 confidence korekcijas.
Raksta rollback PIRMS piemērošanas. Palaid ar --apply, lai rakstītu DB."""
import sqlite3
import sys

DB = "data/atmina.db"
ROLLBACK = "data/rollback_needs_review_triage_2026-09-26.sql"
TAG = "Izvērtēts 2026-09-26:"

# id -> (jaunais confidence vai None, operatora piezīme)
DECISIONS = {
    724921: (0.7, "konteksts apstiprināts — Veselības ministrija 25.09. atsauca Kutkēviču no RAKUS padomes (doc 116822), «Hossam» ir ministrs Abu Meri; confidence 0.6→0.7."),
    724927: (None, "atbildes adresāts nav zināms, bet teksts ir paša un pilns; tēma Valsts pārvalde paliek."),
    724928: (None, "tēma NVO un pilsoniskā sabiedrība paliek (pilsoniskā līdzdalība); līdzīgais #709234 zem Vēlēšanas — sīka nesaskaņa, nemainīta."),
    724929: (None, "svētku runa bez konkrēta instrumenta — apstiprināts kā vāja pozīcija, pārskatā neizcelt."),
    724934: (None, "vārdi ir paša; sarunas pavediens DB (doc 117493, 117494) apstiprina datumu; tēma Imigrācija paliek."),
    724935: (0.65, "skaidrs atribuēts atstāsts (LTV: «sacīja iekšlietu ministrs»); confidence 0.6→0.65."),
    724938: (None, "izlaidumu [..] ielicis pats LTV — citāts atbilst avotam burtiski, paliek."),
    724941: (None, "formulējums atbilst LTV tvītam; avots nenosauc budžeta gadu, LSM raksta virsraksts: «sistēma pretojas tēriņu mazināšanai». Nepasniegt kā atkāpšanos no maija solījuma — @devils-advocate pretrunu 20393→724941 noraidīja."),
    724942: (0.7, "LSM raksts (26.09.) izteikumu apstiprina gandrīz burtiski; confidence 0.6→0.7."),
    724943: (None, "LSM raksts apstiprina citātu; stated_at 25.09. pamatots."),
}


def q(v):
    if v is None:
        return "NULL"
    if isinstance(v, (int, float)):
        return repr(v)
    return "'" + str(v).replace("'", "''") + "'"


db = sqlite3.connect(DB)
db.row_factory = sqlite3.Row
rows = {r["id"]: r for r in db.execute(
    f"SELECT id, reasoning, confidence, review_status FROM claims WHERE id IN ({','.join('?' * len(DECISIONS))})",
    list(DECISIONS),
)}
assert len(rows) == len(DECISIONS), f"atrasti {len(rows)} no {len(DECISIONS)}"
for cid, r in rows.items():
    assert r["review_status"] == "needs_review", (cid, r["review_status"])
    assert r["reasoning"].startswith("NEEDS_REVIEW:"), cid
    assert r["reasoning"].count("NEEDS_REVIEW") == 1, cid

with open(ROLLBACK, "w", encoding="utf-8") as f:
    f.write("-- Rollback: NEEDS_REVIEW triāža 2026-09-26 (10 claims → «Izvērtēts 2026-09-26:»,\n")
    f.write("-- confidence 724921→0.7, 724935→0.65, 724942→0.7). Forward: scripts/fix_needs_review_triage_2026-09-26.py, piemērots 2026-09-26.\n")
    f.write("-- review_status atvasina trigeris no reasoning — to ar roku NErakstām.\n")
    f.write("BEGIN;\n")
    for cid, r in sorted(rows.items()):
        f.write(f"UPDATE claims SET reasoning = {q(r['reasoning'])}, confidence = {q(r['confidence'])} WHERE id = {cid};\n")
    f.write("COMMIT;\n")
print("rollback uzrakstīts:", ROLLBACK)

if "--apply" in sys.argv:
    with db:
        for cid, (conf, note) in DECISIONS.items():
            orig = rows[cid]["reasoning"][len("NEEDS_REVIEW:"):].strip()
            new = f"{TAG} {note} Sākotnējās šaubas: {orig}"
            assert "NEEDS_REVIEW" not in new
            db.execute("UPDATE claims SET reasoning = ?, confidence = COALESCE(?, confidence) WHERE id = ?",
                       (new, conf, cid))
    after = db.execute(
        f"SELECT id, review_status, confidence FROM claims WHERE id IN ({','.join('?' * len(DECISIONS))}) ORDER BY id",
        list(DECISIONS),
    ).fetchall()
    for a in after:
        print(tuple(a))
    ok = sum(1 for a in after if a["review_status"] == "reviewed")
    print(f"reviewed: {ok} no {len(DECISIONS)}")
    print("atvērtā rinda:", db.execute("SELECT COUNT(*) FROM claims WHERE review_status='needs_review'").fetchone()[0])
