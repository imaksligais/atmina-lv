"""Rutīna 2026-11-07, solis 2c: dienas NEEDS_REVIEW pozīciju izvērtējums (15 rindas).

  --write-rollback  uzraksta data/rollback_needs_review_resolve_2026-11-07.sql no pašreizējām DB vērtībām
  --apply           izpilda forward (atsaka, ja rollback nav commitēts)

Visām 15 stance paliek avota robežās; šaubu pazīmi atrisina nosaukts dokuments vai
avota paša teksts (izvērtēts ar advisor). 753306 stance noņemti ekstraktora meta-vārdi
«nenosauktu …» → pēc --apply: scripts/reembed_claims.py 753306.
"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8")

from src.db import get_db  # noqa: E402

RB = Path("data/rollback_needs_review_resolve_2026-11-07.sql")
D = "Izvērtēts 2026-11-07: "

EVIDENCE = {
    753289: "Delfi teksts atstāsta Rinkēviča teikto ar atsauces verbiem («atzina», «pauda cerību», «aicināja»); stance nepārsniedz šo atstāstu, «daļas» saglabāts.",
    753290: "stance paliek tvīta vārdu robežās; konteksts — tās pašas dienas ziņas par Latvijai neattiecinātu izņēmumu migrantu solidaritātes mehānismā (Zeltīta doc 152993, Rajevska doc 153027); ironiskā pateicība nostāju neapgriež.",
    753293: "stance paliek tvīta vārdu robežās un premjeru vārdā nenosauc; konteksts — 07.11. protests Jēkabpilī, kurā runāja Kulbergs (doc 152897). Tēma ir tuvākā pieejamā, nemainīta (idempotences atslēga).",
    753297: "paša tvīts; stance paliek tā robežās, asais apzīmējums ietīts atrunā «ko viņš raksturo kā»; konteksts — Kiršteina tās pašas dienas tvīti par Polijas prezidentu (752757, 752851).",
    753301: "paša tvīts protesta dienā; ironiskais teikums par Kulbergu tikai citēts, nostāja (atbalsts protestam) izteikta tieši; konteksts — doc 152897.",
    753302: "paša tvīts; stance paliek tā robežās un norāda ironiju; konteksts — tās pašas dienas Kulberga (753313, 753314) un Šlesera (753316) izteikumi par graudu tranzītu.",
    753305: "paša tvīts; stance paliek tā robežās, vērtējums mīkstināts («pauž iespaidu»); konteksts — Kulberga runa protestā Jēkabpilī (doc 152897, 152933), kuru Velps klausījās klātienē.",
    753306: "paša tvīts; konteksts — Velpa tās pašas dienas tvīti par Krievijas graudu tranzītu (753303); stance pārrakstīta tvīta vārdos, bez meta-piezīmēm.",
    753320: "paša tvīts; stance paliek tā robežās, ironiskais nobeigums nostāju neapgriež; konteksts — tās pašas dienas ziņas par graudu tranzītu un migrantu solidaritātes mehānismu (doc 152993, 152897).",
    753322: "paša tvīts, atbilde Kiršteinam; minētās valstis (Somija, Nīderlande, Kipra) nosauc Kiršteina doc 152611 (753296); stance tās neievieš.",
    753323: "paša tvīts; stance paliek tā robežās un ielu nenosauc; vispārīgs vērtējums par ielu rekonstrukciju, konteksts nostāju nemaina.",
    753326: "paša tvīts (slots neutral|first_party — sloti.md: kā parasts politiķis); prognozes teikums tiešs, ironiskais sākums tikai atstāstīts; konteksts — Kulberga runa (doc 152933).",
    753329: "nra.lv redakcijas teksts divreiz attiecina uz Verginu («deputāte Ilze Vergina uzskata, ka …»); stance nepārsniedz šo atstāstu un saka tikai iespējamību.",
    753333: "citētais teikums ir Kola paša vārdi ECR paziņojumā («ECR MEP @RihardsKols … said»), ko viņš retvītoja; atribūcija nepārprotama.",
    753334: "paša tvīta retvīts (RT @StankevicsA); asais apzīmējums ietīts atrunā; stance NBS aicinājuma saturu neievieš.",
}

STANCE_753306 = (
    "Uzskata, ka ir iespējas apturēt «šo tranzītu», taču tam vajag politisko gribu un «bez nekādiem "
    "sodiem», un pārmet, ka ar «paziņojumiem» atkal stāsta vienu, bet nedara neko."
)


def _strip_marker(reasoning: str) -> str:
    r = reasoning
    if r.startswith("NEEDS_REVIEW:"):
        r = r[len("NEEDS_REVIEW:"):].strip()
    assert "NEEDS_REVIEW" not in r, r
    return r


def _sql(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"


def write_rollback(db) -> None:
    lines = [
        "-- Rollback: rutīna 2026-11-07, NEEDS_REVIEW izvērtējums (scripts/_fix_needs_review_rutina_2026-11-07.py)",
        "-- Forward: claims.reasoning NEEDS_REVIEW → «Izvērtēts 2026-11-07: … Sākotnēji: …» 15 rindām;",
        "--          753306 stance pārrakstīta (pēc rollback: scripts/reembed_claims.py 753306).",
        "-- Apply date: 2026-11-07",
        "BEGIN;",
    ]
    for cid in EVIDENCE:
        reasoning, stance = db.execute("SELECT reasoning, stance FROM claims WHERE id=?", (cid,)).fetchone()
        assert reasoning.startswith("NEEDS_REVIEW:"), (cid, reasoning[:40])
        if cid == 753306:
            lines.append(f"UPDATE claims SET reasoning={_sql(reasoning)}, stance={_sql(stance)} WHERE id={cid};")
        else:
            lines.append(f"UPDATE claims SET reasoning={_sql(reasoning)} WHERE id={cid};")
    lines.append("COMMIT;")
    RB.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"rakstīts {RB} ({len(EVIDENCE)} rindas)")


def apply(db) -> None:
    out = subprocess.run(["git", "ls-files", "--error-unmatch", str(RB)], capture_output=True)
    dirty = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", str(RB)])
    if out.returncode != 0 or dirty.returncode != 0:
        sys.exit(f"STOP: {RB} nav commitēts")
    n = 0
    for cid, ev in EVIDENCE.items():
        reasoning = db.execute("SELECT reasoning FROM claims WHERE id=?", (cid,)).fetchone()[0]
        new = D + ev + " Sākotnēji: " + _strip_marker(reasoning)
        if cid == 753306:
            cur = db.execute("UPDATE claims SET reasoning=?, stance=? WHERE id=?", (new, STANCE_753306, cid))
        else:
            cur = db.execute("UPDATE claims SET reasoning=? WHERE id=?", (new, cid))
        assert cur.rowcount == 1
        n += 1
    db.commit()
    left = db.execute(
        f"SELECT COUNT(*) FROM claims WHERE review_status='needs_review' AND id IN ({','.join(map(str, EVIDENCE))})"
    ).fetchone()[0]
    print(f"atjaunināts {n}/{len(EVIDENCE)}; needs_review atlicis: {left}")


if __name__ == "__main__":
    db = get_db()
    if "--write-rollback" in sys.argv:
        write_rollback(db)
    elif "--apply" in sys.argv:
        apply(db)
    else:
        print(__doc__)
