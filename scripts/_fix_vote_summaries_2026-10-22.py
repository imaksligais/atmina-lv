"""Nepareizi saeima_votes.summary (b01 pārskatīšana 2026-10-22, backlog/saeima.md): 22/Lp14 (4 balsojumi —
zemes likumiskās lietošanas teksts, bet likums pievieno PKC Valsts kancelejai; avots: likumprojekts 22.pdf,
titania), 1106/Lp14 (3 balsojumi — Maksātnespējas kontroles dienesta paketes teksts, bet likums par
publisku personu kapitālsabiedrībām; avots: saeima_bills + titania), 1153/Lp14 3. las. un 1185/Lp14
3. las. (2026-04-30 sēdes tā pati kļūda). Labo summary + saeima_vote claims stance (tiem vektoru nav).
Rollback: data/rollback_vote_summaries_2026-10-22.sql. --write-rollback | --apply"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")
from src.db import get_db  # noqa: E402

OLD22 = ("Precizē likumiskās zemes lietošanas tiesības zem ēkām un būvēm — nosaka, ka lietošanā esošās zemes "
         "platību zemes un ēku īpašnieki nosaka savstarpēji vienojoties; saskaņo ar 2021. gada Civillikuma spēkā "
         "stāšanās likuma grozījumiem, kas piespiedu nomu aizstāja ar likumisko zemes lietošanu.")
NEW22 = ("Pievieno Pārresoru koordinācijas centru Valsts kancelejai — likumā vārdus «Pārresoru koordinācijas "
         "centrs» aizstāj ar «Valsts kanceleja»; likums stājas spēkā 2023. gada 1. martā.")
B1106 = ("Atceļ prasību pirms publiskas personas kapitālsabiedrības dibināšanas izdot valdības noteikumus vai "
         "pašvaldības saistošos noteikumus par stratēģiski svarīgām precēm un tirgus nepilnību, ļauj dibināt "
         "kapitālsabiedrības arī eksporta tirgiem paredzētu preču vai pakalpojumu radīšanai un nosaka, ka tām "
         "jāievēro godīga konkurence, ko uzrauga Konkurences padome. Iesniedzējs: Ministru kabinets.")
FULL = {
    6286: B1106 + " Balsojums — 1. lasījums; iznākums: Pieņemts (83 par).",
    159: B1106 + " Balsojums — 2. lasījums; iznākums: Pieņemts vienprātīgi (78/0/0).",
    5786: B1106 + " Balsojums — 3., galīgais lasījums; iznākums: Pieņemts (80 par).",
    153: ("Ievieš atsevišķās lietošanas tiesību — zemesgrāmatā nostiprinātu dzīvokļa īpašnieka tiesību nošķirti "
          "no citiem lietot noteiktu kopīpašuma daļu — un regulē kopīgās infrastruktūras lietošanu kopā ar citu "
          "māju dzīvokļu īpašniekiem. Iesniedzējs: Ministru kabinets. Balsojums — 3. lasījums; iznākums: "
          "Pieņemts vienprātīgi (77/0/0)."),
    140: ("Ievieš veterinārās e-veselības informācijas sistēmu un veterināro zāļu reģistra sistēmu, nosaka "
          "Pārtikas drošības institūta BIOR lomu veterināro zāļu kontrolē, kā arī regulējumu par cilvēku zāļu "
          "lietošanu dzīvniekiem un antimikrobiālās rezistences mazināšanu. Balsojums — 3. lasījums; iznākums: "
          "Pieņemts vienprātīgi (82/0/0)."),
}
PREFIX = {5536: (OLD22, NEW22), 3155: (OLD22, NEW22), 3265: (OLD22, NEW22), 3432: (OLD22, NEW22)}


def low(s):
    return s[0].lower() + s[1:]


def q(s):
    return "'" + s.replace("'", "''") + "'"


db = get_db()
plan = []  # (vote_id, old_summary, new_summary, url, [(claim_id, old_stance, new_stance)])
for vid in list(PREFIX) + list(FULL):
    old, url = db.execute("SELECT summary, url FROM saeima_votes WHERE id=?", (vid,)).fetchone()
    if vid in PREFIX:
        a, b = PREFIX[vid]
        assert old.count(a) == 1, (vid, "jau labots?")
        new = old.replace(a, b)
        frm, to = low(a), low(b)
    else:
        assert "Maksātnespējas kontroles dienest" in old, (vid, "jau labots?")
        new, frm, to = FULL[vid], low(old), low(FULL[vid])
    rows = db.execute("SELECT id, stance FROM claims WHERE claim_type='saeima_vote' AND source_url=?",
                      (url,)).fetchall()
    # Stance parasti sāk ar mazo burtu, bet īpašvārdu (piem., «Farmācijas») atstāj ar lielo.
    fix = []
    for cid, st in rows:
        src = frm if st.count(frm) == 1 else frm[0].upper() + frm[1:]
        assert st.count(src) == 1, (vid, cid)
        fix.append((cid, st, st.replace(src, to)))
    plan.append((vid, old, new, fix))

if "--write-rollback" in sys.argv:
    out = ["-- Forward (apply 2026-10-22): saeima_votes.summary 9 balsojumiem (22/Lp14 ×4, 1106/Lp14 ×3, 1153/Lp14 3. las.,",
           "--   1185/Lp14 3. las.) + to saeima_vote claims stance (vektoru nav). Skripts: scripts/_fix_vote_summaries_2026-10-22.py",
           "BEGIN;"]
    for vid, old, _, cl in plan:
        out.append(f"UPDATE saeima_votes SET summary={q(old)} WHERE id={vid};")
        out += [f"UPDATE claims SET stance={q(s)} WHERE id={cid};" for cid, s, _ in cl]
    out.append("COMMIT;")
    (ROOT / "data/rollback_vote_summaries_2026-10-22.sql").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("rollback:", len(plan), "balsojumi,", sum(len(c) for *_, c in plan), "claims")
elif "--apply" in sys.argv:
    for vid, _, new, cl in plan:
        db.execute("UPDATE saeima_votes SET summary=? WHERE id=?", (new, vid))
        for cid, _, ns in cl:
            db.execute("UPDATE claims SET stance=? WHERE id=?", (ns, cid))
    db.commit()
    ids = ",".join(map(str, FULL))
    left = db.execute(f"SELECT COUNT(*) FROM saeima_votes WHERE id IN ({ids})"
                      " AND summary LIKE '%Maksātnespējas%'").fetchone()[0]
    left22 = db.execute("SELECT COUNT(*) FROM claims WHERE stance LIKE ?", ("%" + low(OLD22)[:60] + "%",)).fetchone()[0]
    print("labots:", len(plan), "balsojumi,", sum(len(c) for *_, c in plan), "claims; vecā teksta paliek:", left, left22)
else:
    for vid, old, new, cl in plan:
        print(vid, len(cl), "claims |", new[:90])
