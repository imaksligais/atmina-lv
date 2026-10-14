"""Stance korektūra 2026-09-15 vakara rutīnā — trīs rindas.

Kas: #710919 procentu atstarpes (LV stils «90 %»); #710944 un #710947 saīsināti
no 136/142 vārdiem uz ≤100, saglabājot visus avota kvalifikatorus (lint 5. likums
`prose-block-too-long` — stance nonāk pārskata tabulas šūnā verbatim).

Rollback: data/rollback_stance_trim_2026-09-15.sql (pilns pre-image, rakstīts
PIRMS piemērošanas). Pēc piemērošanas OBLIGĀTI pārrēķināt vektorus:
    .venv/Scripts/python.exe scripts/reembed_claims.py 710919 710944 710947

Lietojums (no repo saknes): .venv/Scripts/python.exe scripts/fix_stance_trim_2026-09-15.py [--apply]
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.db import get_db  # noqa: E402

ROLLBACK = Path("data/rollback_stance_trim_2026-09-15.sql")

NEW = {
    710919: (
        "Novēl zivsaimniecības nozarei izdošanos «vismaz uz 100 %» un nosauc nozares "
        "stratēģijas mērķus par ambicioziem: zivju apstrādes nozarē līdz 2034. gadam "
        "sasniegt līdz 500 milj. eiro apgrozījumu gadā ar 90 % eksporta īpatsvaru, bet "
        "zvejniecībā par 30 % palielināt pievienoto vērtību uz vienu nodarbināto."
    ),
    710944: (
        "Pēc valdības sēdes par paātrinātu infrastruktūras maksas pārskatīšanu Krievijas "
        "labības tranzītam uzsver, ka tūlītējs lēmums bija svarīgs, jo Krievijas graudi "
        "caur ostām plūst tieši tagad; paaugstinātā maksa ātrākajā variantā var stāties "
        "spēkā triju nedēļu laikā, «LatRailNet» tiks aicināts to piemērot 300 % apmērā, un "
        "Eiropas normatīvi to pieļaujot; tranzīta graudiem paredzēta fiziska pārbaude "
        "(līgums ar Anglijas laboratoriju, piesaistīti Ukrainas eksperti); Latvija palīdzēs "
        "arī Ukrainas graudu eksportam caur Latvijas ostām, ja atrisinās transportēšanu, "
        "bet prioritāte ir Latvijas zemnieku graudi; nenoliedz, ka pavadzīmes var viltot, "
        "taču uzskata, ka kravas varot izsekot."
    ),
    710947: (
        "Uzskata, ka dabas aizsardzības lēmumiem jābalstās datos un vienādos principos "
        "pļavā, mežā un jūrā, nevis situatīvi mainot zinātnisko datu, sabiedrības interešu "
        "un politisko apsvērumu svaru; jautā, vai ir atbildīgi izslēgt zālāju biotopus no "
        "Natura 2000 saraksta (viņaprāt, visticamāk, pašvaldību iebildumu dēļ), ja "
        "zinātniskais izvērtējums un Eiropas Komisijas pārkāpuma procedūra norāda uz "
        "aizsardzības nepietiekamību; par jūras teritoriju «Selga uz rietumiem no Tūjas» "
        "iebilst, ka ar upes nēģa klātbūtni vien nepietiek — jāparāda teritorijas nozīme "
        "populācijas saglabāšanā; uzskata, ka ar spēcīgu zinātnisku pamatojumu jābūt "
        "iespējai mainīt aizsargājamo teritoriju robežas, un ka politisks lēmums, kas "
        "atšķiras no zinātniskā vērtējuma, jānosauc par politisku."
    ),
}


def sql_str(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"


def main() -> int:
    apply = "--apply" in sys.argv
    db = get_db()
    rows = {r["id"]: r for r in db.execute(
        "SELECT id, stance FROM claims WHERE id IN (710919, 710944, 710947)"
    ).fetchall()}
    assert set(rows) == set(NEW), f"trūkst rindu: {set(NEW) - set(rows)}"
    for cid, txt in NEW.items():
        n = len(txt.split())
        print(f"{cid}: {len(rows[cid]['stance'].split())} → {n} vārdi")
        assert n <= 120, cid
    if ROLLBACK.exists():
        print(f"{ROLLBACK} jau eksistē — nepārrakstu (labojums jau piemērots?)")
    else:
        lines = [
            "-- Rollback: scripts/fix_stance_trim_2026-09-15.py (stance korektūra #710919, #710944, #710947)",
            "-- Apply date: 2026-09-15. Pēc rollback pārrēķināt vektorus:",
            "--   .venv/Scripts/python.exe scripts/reembed_claims.py 710919 710944 710947",
            "BEGIN;",
        ]
        for cid, r in rows.items():
            lines.append(f"UPDATE claims SET stance = {sql_str(r['stance'])} WHERE id = {cid};")
        lines.append("COMMIT;")
        ROLLBACK.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"rollback rakstīts: {ROLLBACK}")
    if not apply:
        print("sausā palaide — --apply, lai rakstītu")
        return 0
    with db:
        for cid, txt in NEW.items():
            if rows[cid]["stance"] == txt:
                print(f"{cid}: jau labots, izlaižu")
                continue
            db.execute("UPDATE claims SET stance = ? WHERE id = ?", (txt, cid))
    print("piemērots; tagad: .venv/Scripts/python.exe scripts/reembed_claims.py 710919 710944 710947")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
