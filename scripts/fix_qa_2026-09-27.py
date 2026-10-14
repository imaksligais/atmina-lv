"""@quality-reviewer § H labojumi rutīnas dienai 2026-09-27 (pirms publicēšanas).

- 4 pozīciju stance (#724962, #724969, #724990, #724952) → pēc --apply OBLIGĀTI
  `scripts/reembed_claims.py 724962 724969 724990 724952`
- #724990 confidence 0,65 → 0,6 (runātājs no partijas paraksta, saturs no automātiska atšifrējuma)
- konteksta piezīme #651 virsraksts (tā pati diena, nav deployota — inv. #8 otrais izņēmums)
- pārskats #652 + wiki/dailies/2026-09-27.md: tās pašas šūnas + 9 prozas labojumi

Lietojums: .venv/Scripts/python.exe scripts/fix_qa_2026-09-27.py [--apply]
Rollback: data/rollback_qa_2026-09-27.sql (raksta --apply pirms izmaiņām)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.db import get_db  # noqa: E402

ROLLBACK = Path("data/rollback_qa_2026-09-27.sql")
WIKI = Path("wiki/dailies/2026-09-27.md")

# (claim_id, vecais fragments, jaunais fragments) — tas pats fragments arī pārskata tabulas šūnā
CLAIM_FIXES = [
    (724962, "ģimenes vērtības viņaprāt ir pirmajā vietā", "ģimenes vērtības, viņaprāt, ir pirmajā vietā"),
    (724969, "nevajadzīgiem tēriņiem, tas jāpārtrauc, lai", "nevajadzīgiem tēriņiem un ka tas jāpārtrauc, lai"),
    (724990, "Kritizē valdību par «pusdarītiem darbiem» degvielas cenu jomā",
     "Kritizē valdību par pusdarītiem darbiem degvielas cenu jomā"),
    (724990, "lielāko izmaksu pieaugumu redz mājokļu izmaksās", "lielāko sadārdzinājumu redz mājokļu izmaksās"),
    (724952, "saka, ka tas bija «pilnīgi politizēts pasākums», kas sagaidīja priekšvēlēšanu laiku,",
     "saka, ka Senāts «sagaidīja priekšvēlēšanu laiku» un tas bija «pilnīgi politizēts pasākums»,"),
]

NOTE_651 = ("premjera nodokļu rezidenta «abonements» atdzīvina zelta vīzu strīdu",
            "premjera ideja par nodokļu rezidenta «abonementu» atdzīvina zelta vīzu strīdu")

BRIEF_FIXES = [
    ("**Nodokļu rezidenta «abonements» «de facto»:**", "**Nodokļu rezidenta «abonements» raidījumā «de facto»:**"),
    ("Saeimas sarukšanu no 100 uz 70 deputātiem", "deputātu skaita samazināšanu no 100 uz 70"),
    ("ka 20 centu degvielas cenas samazinājums paliek neatrisināts",
     "ka jautājums par degvielas cenas samazināšanu par 20 centiem paliek neatrisināts"),
    ("**Premjera nodokļu rezidenta «abonements» atdzīvina zelta vīzu strīdu**",
     "**Premjera ideja par nodokļu rezidenta «abonementu» atdzīvina zelta vīzu strīdu**"),
    ("Šlesers (LPV) saistībā ar «Riga Waterfront» ārvalstu investoriem atbildību par riskantiem investoriem liek dienestiem, ne attīstītājiem.",
     "Šlesers (LPV), runājot par «Riga Waterfront» projektu, atbildību par riskantiem ārvalstu investoriem liek dienestiem, ne attīstītājiem."),
    ("un sasaista neizpildīto degvielas solījumu ar Satversmes grozījumu atbalstu; premjera vai AS atbilde dienas pozīcijās nav fiksēta.",
     "un neatrisināto degvielas cenas jautājumu pretstata Satversmes grozījumu atbalstam. Premjera vai AS atbilde dienas pozīcijās nav fiksēta."),
    ("Mežals (LPV) tēmu pievērš ģimenes vērtībām", "Mežals (LPV) pievēršas ģimenes vērtībām"),
    ("Vītols (AS) budžeta izvēli rāmē kā nodokļu celšanu vai izdevumu mazināšanu un priekšroku dod otrajai",
     "Vītols (AS) budžetam redz divus ceļus — nodokļu celšanu vai izdevumu mazināšanu — un priekšroku dod otrajam"),
    ("Imigrācijā premjera ideju kritizē vai piesardzīgi vērtē koalīcijas partneru JV un NA pārstāvji, bet opozīcijas pārstāvis Šlesers (LPV) investoru vēlmi vērtē pozitīvi; koalīcijas iekšējo spriedzi papildina Siliņas (JV) aicinājums AS uz sarunu.",
     "Imigrācijā premjera ideju kritizē vai piesardzīgi vērtē koalīcijas partneri JV un NA, bet ZZS norobežojas. Opozīcijā Šuvajevs (PRO) apšauba ieguvumus budžetam, bet Šlesers (LPV) investoru vēlmi vērtē pozitīvi; koalīcijas iekšējo spriedzi papildina Siliņas (JV) aicinājums AS uz sarunu."),
]


def q(s):
    return "'" + s.replace("'", "''") + "'"


def fix_text(t):
    for _cid, old, new in CLAIM_FIXES:
        assert t.count(old) == 1, old
        t = t.replace(old, new)
    for old, new in BRIEF_FIXES:
        assert t.count(old) == 1, old
        t = t.replace(old, new)
    return t


def main():
    db = get_db()
    ids = sorted({c for c, _, _ in CLAIM_FIXES})
    claims = {r["id"]: dict(r) for r in db.execute(
        f"SELECT id, stance, confidence, reasoning FROM claims WHERE id IN ({','.join('?' * len(ids))})", ids)}
    new_stance = {i: claims[i]["stance"] for i in ids}
    for cid, old, new in CLAIM_FIXES:
        assert new_stance[cid].count(old) == 1, (cid, old)
        new_stance[cid] = new_stance[cid].replace(old, new)
    note = db.execute("SELECT content FROM context_notes WHERE id = 651").fetchone()[0]
    assert note.count(NOTE_651[0]) == 1
    brief = db.execute("SELECT content FROM context_notes WHERE id = 652").fetchone()[0]
    brief2 = fix_text(brief)
    wiki = WIKI.read_bytes().decode("utf-8")
    wiki2 = fix_text(wiki)
    assert brief2 == wiki2, "DB un dailies atšķiras"
    if "--apply" not in sys.argv:
        print("sausā palaide OK:", len(CLAIM_FIXES), "pozīciju fragmenti,", len(BRIEF_FIXES), "prozas labojumi, piezīme #651")
        return
    lines = ["-- ROLLBACK: @quality-reviewer § H labojumi 2026-09-27",
             "-- Atceļ: scripts/fix_qa_2026-09-27.py --apply. Piemērots: 2026-09-27.",
             f"-- Pēc rollback OBLIGĀTI: scripts/reembed_claims.py {' '.join(map(str, ids))}",
             "-- wiki/dailies/2026-09-27.md (gitignored) pārraksta no context_notes #652.", "BEGIN;"]
    for i in ids:
        c = claims[i]
        lines.append(f"UPDATE claims SET stance = {q(c['stance'])}, confidence = {c['confidence']}, "
                     f"reasoning = {q(c['reasoning'])} WHERE id = {i};")
    lines.append(f"UPDATE context_notes SET content = {q(note)} WHERE id = 651;")
    lines.append(f"UPDATE context_notes SET content = {q(brief)} WHERE id = 652;")
    lines += ["COMMIT;", ""]
    ROLLBACK.write_text("\n".join(lines), encoding="utf-8")
    with db:
        for i in ids:
            db.execute("UPDATE claims SET stance = ? WHERE id = ?", (new_stance[i], i))
        r = claims[724990]["reasoning"]
        db.execute("UPDATE claims SET confidence = 0.6, reasoning = ? WHERE id = 724990",
                   ("Izvērtēts 2026-09-27: runātājs noteikts no partijas paraksta, saturs no automātiska video "
                    "atšifrējuma, kura tekstu DB neglabā — tāpēc 0,6, ne 0,65 (quality-reviewer). " + r,))
        db.execute("UPDATE context_notes SET content = ? WHERE id = 651", (note.replace(*NOTE_651),))
        db.execute("UPDATE context_notes SET content = ? WHERE id = 652", (brief2,))
    WIKI.write_bytes(wiki2.encode("utf-8"))
    print("applied; rollback:", ROLLBACK)


if __name__ == "__main__":
    main()
