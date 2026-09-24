"""Backfill 1. partijas atradumi vecajos claims (operatora «jā» 2026-09-23).

15 dzēšanas (10 dublikāti + 5 biroja balss pēc 2026-08-25 konvencijas) un
8 stance pārrakstīšanas (5 nepareizi nolasīti + 3 tēmu sadursmju apvienošana).
Pierādījumi: docs/audits/2026-09-23-backfill-batch1/ (agent-*-report.md).

Lietojums (no repo saknes):
    .venv/Scripts/python.exe scripts/fix_backfill_batch1_old_claims_2026-09-23.py           # sauss
    .venv/Scripts/python.exe scripts/fix_backfill_batch1_old_claims_2026-09-23.py --apply   # raksta

--apply vispirms uzraksta rollback failu, tad vienā transakcijā maina DB.
Pēc tam: scripts/reembed_claims.py visiem 8 pārrakstītajiem.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import sqlite_vec

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "atmina.db"
ROLLBACK = ROOT / "data" / "rollback_backfill_batch1_old_claims_2026-09-23.sql"
IDS_FILE = ROOT / "data" / "rollback_backfill_batch1_old_claims_2026-09-23.ids"

DELETE = {
    # dublikāti: dzēšamais -> paturamais
    521141: "dublikāts #521099 (tā pati LTV intervija, nepareizs stated_at)",
    532362: "dublikāts #532334 (paša tvīts ir pirmavots)",
    18230: "dublikāts #18229 (viena LR intervija trijos medijos)",
    18231: "dublikāts #18229 (viena LR intervija trijos medijos)",
    18101: "dublikāts #18217 (paša tvīts ir pirmavots)",
    520852: "dublikāts #520843 (viena intervija trijos medijos)",
    520851: "dublikāts #520843 (viena intervija trijos medijos)",
    521161: "dublikāts #521160 (agrākā publikācija, satur to pašu)",
    527813: "dublikāts #527812 (tā pati preses konference, avotā nav tiešas runas)",
    18137: "dublikāts #18275 (agrākā publikācija ar tiešu citātu)",
    # biroja balss (konvencija 2026-08-25)
    521116: "biroja balss (padomnieks Drēģeris); tā pati nostāja paša tvītā #521115",
    531904: "biroja balss (padomnieks Sadovskis); tā pati nostāja paša tvītā #531903",
    532350: "biroja balss (padomniece Grundule)",
    521026: "biroja balss (padomniece Gulbe)",
    20722: "biroja balss (LM paziņojums)",
}

R = "Izvērtēts 2026-09-23 (backfill 1. partijas atradums, docs/audits/2026-09-23-backfill-batch1): "

UPDATE = {
    527890: dict(
        stance='Uzskata, ka Baltijas valstīm "Rail Baltica" jāīsteno kopīgi, nevis atrauti; norāda, ka pabeigšanai 2030. gadā jāsakrīt ļoti daudziem nosacījumiem, jo RB Rail ziņojumā termiņš ir «2030+», un šaubās, vai Igaunijai izdosies sasniegt savu 2030. gada mērķi. Saka, ka viņam ir ideja projekta optimālai īstenošanai, ko pārrunās ar ekspertiem, bet termiņus un finansējumu — ar Eiropas Komisijas prezidenti.',
        reasoning=R + "stance labots pēc avota — iepriekš kļūdaini lasīja «gatavību pabeigt 2030. gadā», lai gan Kulbergs 2030. gadu apšauba (saskan ar #548274). Citāts ir paša vārdi.",
    ),
    532366: dict(
        stance="Uzskata, ka regulējumam par kompensāciju dronu vai citu militāru incidentu radītajiem zaudējumiem jābūt iespējami vienkāršam: iesniegumam trīs dienas, lēmumam — līdz vienam mēnesim; zaudējumus līdz 10 000 eiro varētu kompensēt ar ministra lēmumu, lielākus — ar valdības lēmumu.",
        reasoning=R + "stance labots pēc avota — mēneša termiņš attiecas uz lēmumu par katru iesniegumu, ne uz MK noteikumu pieņemšanu. LTV «Rīta Panorāma» intervija, pārstāsts.",
    ),
    18366: dict(
        stance="Norāda, ka premjere Siliņa šobrīd neplāno demisionēt, un uzsver, ka valdības tālāko likteni izšķirs parlamenta vairākums.",
        reasoning=R + "stance labots — «ZZS demisiju neatbalstīs» teica Brigmanis, ne Kozlovskis; «aizstāv valdības turpināšanos» bija plašāk par avotu. LTV «Kas notiek Latvijā?», tieša runa.",
    ),
    18324: dict(
        stance="Uzskata, ka jaunas valdības veidošanai ir jēga arī nepilnus piecus mēnešus pirms Saeimas vēlēšanām: Siliņas koalīcijai bijis grūti pieņemt lēmumus, un jaunā valdība varētu kļūt par kodolu arī nākamajai valdībai pēc vēlēšanām.",
        reasoning=R + "stance labots — «Siliņas valdība faktiski kritusi» ir ZZS kā partijas paziņojums, ne Rokpelņa teiktais. TV3 «900 sekundes» intervija, pārstāsts.",
    ),
    521029: dict(
        stance="Viņa vadītā valdība deklarācijā apņemas pastiprināt imigrantu kontroli: ierobežot jaunu ilgtermiņa vīzu un uzturēšanās atļauju izsniegšanu un noteikt pieļaujamo trešo valstu pilsoņu skaitu.",
        reasoning=R + "stance pārrakstīts — iepriekšējais jauca imigrāciju ar drošību un izglītību un bija gramatiski nepilnīgs. Avots ir valdības deklarācija, ko iesniedz premjers; žurnālista minējums par Dombravas ietekmi stance neietilpst.",
    ),
    521078: dict(
        stance='Uzskata, ka no "Rail Baltica" trases atteikties nevar, lai gan jebkurš variants būs sāpīgs; aicina izveidot nopietnu projekta vadības grupu premjera vadībā ar regulāriem progresa ziņojumiem, ko paredz arī viņa valdības deklarācija.',
        confidence=0.8,
        reasoning=R + "stance pārrakstīts uz Kulberga paša teikto LTV «De facto» (iepriekš apraksts par deklarāciju); apvienots ar agrāk neglabāto nostāju «atteikties no trases nevar» (tēmu sadursme). Ticamība 0,6→0,8, jo stance balsta paša tiešs citāts.",
    ),
    532213: dict(
        stance="Uzdeva turpināt dienesta pārbaudi IT iepirkumu krāpšanas lietā, ņemot vērā jaunatklātos faktus; sola pārbaudīt katru VDAA katalogu iepirkumu un jaunus atļaut tikai ar finanšu ministra atļauju, bet uzskata, ka pārbaudīt katru iepirkumu citos projektos nav iespējams un atbildība ir arī īstenotājam.",
        quote="Tas nebūtu iespējams. Atbildība ir, protams, arī pašam īstenotājam",
        reasoning=R + "apvienots ar agrāk neglabāto Tavara tiešo runu par iepirkumu pārbaudēm (tēmu sadursme, doc 56037); citāts aizstāts ar paša vārdiem (iepriekš raksta ievads).",
    ),
    532226: dict(
        stance="Nodod Imigrācijas likumu Saeimai otrreizējai caurlūkošanai, rosinot pārskatīt normu par termiņuzturēšanās atļaujām apmaiņā pret investīcijām Latvijā; aicina izvērtēt, vai NATO, OECD un EEZ valstu pilsoņiem nevajadzētu ļaut prasīt termiņuzturēšanās atļauju pret nekustamā īpašuma iegādi.",
        reasoning=R + "apvienots ar agrāk neglabāto vēstules priekšlikumu par uzturēšanās atļaujām pret nekustamo īpašumu (tēmu sadursme, doc 56685). Avots ir prezidenta vēstule Saeimai — viņa paša teksts.",
    ),
}

COLS = ["id", "opponent_id", "document_id", "topic", "stance", "quote", "confidence",
        "reasoning", "salience", "source_url", "stated_at", "created_at", "claim_type",
        "speaker_id", "party_id"]


def sql_lit(v):
    if v is None:
        return "NULL"
    if isinstance(v, (int, float)):
        return repr(v)
    return "'" + str(v).replace("'", "''") + "'"


def main(apply: bool) -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    db = sqlite3.connect(DB_PATH)
    db.enable_load_extension(True)
    sqlite_vec.load(db)

    all_ids = list(DELETE) + list(UPDATE)
    rows = {r[0]: r for r in db.execute(
        f"SELECT {', '.join(COLS)} FROM claims WHERE id IN ({','.join('?' * len(all_ids))})", all_ids)}
    missing = [i for i in all_ids if i not in rows]
    if missing:
        raise SystemExit(f"STOP: trūkst claims {missing}")
    refs = db.execute(
        f"SELECT COUNT(*) FROM contradictions WHERE claim_old_id IN ({','.join('?' * len(all_ids))})"
        f" OR claim_new_id IN ({','.join('?' * len(all_ids))})", all_ids + all_ids).fetchone()[0]
    if refs:
        raise SystemExit(f"STOP: {refs} pretrunas atsaucas uz šīm rindām")

    print(f"examined={len(all_ids)} delete={len(DELETE)} update={len(UPDATE)}")
    for i, why in DELETE.items():
        print(f"  DEL #{i}: {why}")
    for i, ch in UPDATE.items():
        print(f"  UPD #{i}: {', '.join(ch)}")
    if not apply:
        print("sauss skrējiens — nekas nav rakstīts")
        return

    lines = [
        "-- Rollback: scripts/fix_backfill_batch1_old_claims_2026-09-23.py (piemērots 2026-09-23)",
        "-- Atjauno 15 dzēstos claims un 8 pārrakstīto rindu stance/quote/confidence/reasoning.",
        "-- PĒC TAM: .venv/Scripts/python.exe scripts/reembed_claims.py --ids-from "
        "data/rollback_backfill_batch1_old_claims_2026-09-23.ids",
        "BEGIN;",
    ]
    for i in DELETE:
        vals = ", ".join(sql_lit(v) for v in rows[i])
        lines.append(f"INSERT INTO claims ({', '.join(COLS)}) VALUES ({vals});")
    for i in UPDATE:
        r = dict(zip(COLS, rows[i]))
        lines.append(
            f"UPDATE claims SET stance={sql_lit(r['stance'])}, quote={sql_lit(r['quote'])}, "
            f"confidence={sql_lit(r['confidence'])}, reasoning={sql_lit(r['reasoning'])} WHERE id={i};")
    lines.append("COMMIT;")
    ROLLBACK.write_text("\n".join(lines) + "\n", encoding="utf-8")
    IDS_FILE.write_text("\n".join(str(i) for i in all_ids) + "\n", encoding="utf-8")
    print(f"rollback -> {ROLLBACK.relative_to(ROOT)}")

    with db:
        for i in DELETE:
            db.execute("DELETE FROM claim_vectors WHERE claim_id = ?", (i,))
            db.execute("DELETE FROM claims WHERE id = ?", (i,))
        for i, ch in UPDATE.items():
            sets = ", ".join(f"{k} = ?" for k in ch)
            db.execute(f"UPDATE claims SET {sets} WHERE id = ?", (*ch.values(), i))

    left = db.execute(f"SELECT COUNT(*) FROM claims WHERE id IN ({','.join('?' * len(DELETE))})",
                      list(DELETE)).fetchone()[0]
    ok_upd = sum(
        db.execute("SELECT stance = ? AND review_status = 'reviewed' FROM claims WHERE id = ?",
                   (ch["stance"], i)).fetchone()[0] for i, ch in UPDATE.items())
    print(f"deleted_remaining={left} (jābūt 0), updated_ok={ok_upd}/{len(UPDATE)}")
    if left or ok_upd != len(UPDATE):
        raise SystemExit("verifikācija neizdevās")


if __name__ == "__main__":
    main("--apply" in sys.argv)
