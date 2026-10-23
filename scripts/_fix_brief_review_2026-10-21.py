"""@quality-reviewer labojumi 2026-10-21 pārskatam (note 734), piezīmei 733 un 4 pozīciju stance.
Rollback: data/rollback_brief_review_2026-10-21.sql (komitēts pirms apply). Pēc apply:
scripts/reembed_claims.py 743343 743373 743380 743361. --write-rollback | --apply"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")
from src.db import get_db  # noqa: E402

KOM_OLD = "Mandātu, ētikas un iesniegumu komisija skatīja Lindas Liepiņas iesniegumu par Judina attieksmi pret Saeimas darbinieci."
KOM_NEW = "Mandātu, ētikas un iesniegumu komisija pēc Lindas Liepiņas iesnieguma atbalstīja ētikas lietas ierosināšanu par Judina attieksmi pret Saeimas darbinieci."
STANCE = {
    743343: ("apstiprinājumu atteikšanās no tās pilsonības", "apstiprinājumu par atteikšanos no tās pilsonības"),
    743373: ("kurā šodien piedalījās", "kurā 21. oktobrī piedalījās"),
    743380: ("jau rīt rosināt", "jau 22. oktobrī rosināt"),
    743361: ("Pauž gaidas, ka", "Paredz, ka"),
}
BRIEF = [
    ("Jūlija Stepaņenko (SV-AJ) aicina jau 22. oktobrī lemt par likumu, kas pilsonības piešķiršanu atceltu vai nepieļautu;",
     "Jūlija Stepaņenko (SV-AJ) aicina jau 22. oktobrī lemt par likumu, kas pilsonības piešķiršanu atceltu vai nepieļautu ([tvnet.lv](https://pmo.ee/8568922), [x.com](https://x.com/ZKLukasevica/status/2112884799337808197), [x.com](https://x.com/StepanenkoJulij/status/2112809926947156477));"),
    ("**Ētikas komisija skata Lindas Liepiņas iesniegumu pret Andreju Judinu.** Mandātu, ētikas un iesniegumu komisija vērtēja Liepiņas (LPV) iesniegumu par Judina (JV) attieksmi pret Saeimas darbinieci",
     "**Ētikas komisija ierosina ētikas lietu pret Andreju Judinu.** Mandātu, ētikas un iesniegumu komisija pēc Lindas Liepiņas (LPV) iesnieguma atbalstīja ētikas lietas ierosināšanu pret Judinu (JV) par viņa attieksmi pret Saeimas darbinieci"),
    (KOM_OLD, KOM_NEW),
    ("*Abos blokos šodien bija iekšējas domstarpības: koalīcijā divi JV deputāti aicina 22. oktobrī novērst Višvanatas pilsonības piešķiršanu, bet AS deputāts tam vajadzību neredz, un ziņu dienestu jautājumā JV un NA pārstāvji nostājās atšķirīgi; opozīcijā PRO",
     "*Abos blokos 21. oktobrī bija iekšējas domstarpības. Koalīcijā divi JV deputāti aicina 22. oktobrī novērst Višvanatas pilsonības piešķiršanu, bet AS deputāts tam vajadzību neredz, un ziņu dienestu jautājumā JV un NA pārstāvji nostājās atšķirīgi. Opozīcijā PRO"),
    ("no 8. oktobra Saeimas sēdes stenogrammas", "no divu 8. oktobrī notikušu Saeimas sēžu stenogrammām"),
    ("bez kopīgas debates", "bez kopīgām debatēm"),
    ("iebilda, Gunārs Kūtris (ZZS) tam daļēji piekrita", "iebilda, bet Gunārs Kūtris (ZZS) tam daļēji piekrita"),
    ("ierobežotu žurnālistus, bet Maija Armaņeva (LPV) kritizē", "ierobežotu žurnālistus. Maija Armaņeva (LPV) kritizē"),
    ("Komisija galīgajā lasījumā atbalsta", "Komisija galīgajam lasījumam atbalsta"),
    ("Augulis paraksta graudu", "Augulis parakstījis graudu"),
] + [(a, b) for a, b in STANCE.values()]


def q(s):
    return "'" + s.replace("'", "''") + "'"


db = get_db()
brief, topic, source = db.execute("SELECT content, topic, source FROM context_notes WHERE id=734").fetchone()
(note733,) = db.execute("SELECT content FROM context_notes WHERE id=733").fetchone()
for a, _ in BRIEF:
    assert brief.count(a) == 1, ("brief", a[:60], brief.count(a))
assert note733.count(KOM_OLD) == 1
stances = {}
for cid, (a, _) in STANCE.items():
    (s,) = db.execute("SELECT stance FROM claims WHERE id=?", (cid,)).fetchone()
    assert s.count(a) == 1, cid
    stances[cid] = s

if "--write-rollback" in sys.argv:
    out = ["-- Forward (apply 2026-10-21): @quality-reviewer labojumi — context_notes 734 (daily_brief, nedeplojots), 733;",
           "--   claims.stance 743343, 743373, 743380, 743361 (pēc rollback: reembed_claims.py tiem pašiem id).",
           "--   Skripts: scripts/_fix_brief_review_2026-10-21.py", "BEGIN;",
           f"UPDATE context_notes SET content={q(brief)} WHERE id=734;",
           f"UPDATE context_notes SET content={q(note733)} WHERE id=733;"]
    out += [f"UPDATE claims SET stance={q(s)} WHERE id={cid};" for cid, s in stances.items()]
    out.append("COMMIT;")
    (ROOT / "data/rollback_brief_review_2026-10-21.sql").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("rollback rakstīts")
elif "--apply" in sys.argv:
    from src.tools import store_context_note
    for cid, (a, b) in STANCE.items():
        db.execute("UPDATE claims SET stance=? WHERE id=?", (stances[cid].replace(a, b), cid))
    db.execute("UPDATE context_notes SET content=? WHERE id=733", (note733.replace(KOM_OLD, KOM_NEW),))
    db.commit()
    new = brief
    for a, b in BRIEF:
        new = new.replace(a, b)
    res = json.loads(store_context_note(topic=topic, note_type="daily_brief", content=new, source=source))
    print(res)
    (n,) = db.execute("SELECT COUNT(*) FROM context_notes WHERE note_type='daily_brief' AND topic=?", (topic,)).fetchone()
    print("daily_brief rindas ar šo tēmu:", n)
