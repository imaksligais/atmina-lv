# -*- coding: utf-8 -*-
"""NEEDS_REVIEW triāža 2026-08-03 (otrā grupa: politiķi 74/82/105/107/150/
156/164/176/187/224).

Aizver 6 no 10 atlasītajām karodziņa rindām: marķieris ``NEEDS_REVIEW:``
aizstāts ar ``Izvērtēts 2026-08-03:`` un pievienots nosaukts lēmuma pamats.
Mainīts TIKAI ``reasoning`` teksts — ``topic``, ``stance``, ``quote`` un
``confidence`` netiek aiztikti.

Pārējās 4 rindas NETIEK aiztiktas (operatora lēmums):
  548574 (Burovs)   — pamatojumā nosauktais precedents #14451 ir tēmā
                      'Vēlēšanas', nevis 'Valsts pārvalde'; tēmas migrācija.
  555824 (Butāns)   — glabātais citāts nesakrīt ar avota dokumentu (76616).
  555685 (Madžiņš)  — tēma 'Kultūra' pret korpusa 'Imigrācija' (#615859);
                      jutīga satura atribūcija.
  554006 (Žuravļevs)— vienīgā analogā pozīcija (#532034) ir 'Sociālā
                      politika', šī ir 'Tieslietas'; konvencijas lēmums.

Embeddings NAV skarti: ``store_claim()`` iegulst ``f"{topic}: {stance}"``,
un ne viens, ne otrs nemainās, tāpēc ``claim_vectors`` paliek sinhroni.

``review_status`` ir DERIVĒTA kolonna — ``claims_review_status_au`` trigeris
to pārrēķina pats. Ar roku to nerakstīt.

Lietošana:
    .venv/Scripts/python.exe scripts/fix_needs_review_triage_2026-08-03_b.py
        -> uzraksta rollback failu un parāda plānoto; NEKO nemaina
    .venv/Scripts/python.exe scripts/fix_needs_review_triage_2026-08-03_b.py --apply
        -> piemēro (rollback jau ir uz diska)
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DB = REPO / "data" / "atmina.db"
ROLLBACK = REPO / "data" / "rollback_needs_review_triage_2026-08-03_b.sql"

# claim_id -> jaunais PILNAIS reasoning teksts
NEW_REASONING: dict[int, str] = {
    555715: (
        "LETA raksts par Informācijas sabiedrības padomes sēdi. Kučinskis kā "
        "finanšu ministrs sēdē informēja par elektronisko iepirkumu sistēmas "
        "pilnveidošanu; saturu (divi galvenie pasākumi, 140 000 eiro slieksnis, "
        "e-katalogu pozīciju slēgšana) LETA atreferē caur Finanšu ministriju, "
        "tieša citāta nav. Pozīcija ir ministrijas virzīta un ministra "
        "prezentēta, tāpēc pazemināta ticamība. Izvērtēts 2026-08-03: tēmas "
        "robeža bija starp Digitālā politika, Valsts pārvalde un Budžets un "
        "finanses; paliek Digitālā politika. Pamats: korpusā valsts IKT "
        "iepirkumu politikas pozīcijas kopš jūnija konsekventi glabājas šajā "
        "tēmā (claim 532066, 547948, 548186, 548312, 555701, 555734, 555777), "
        "tostarp pozīcija 555701 par to pašu 27. jūlija Informācijas sabiedrības "
        "padomes sēdi. Vienīgais Valsts pārvalde piemērs (claim 11381) ir no "
        "aprīļa, pirms šī konvencija nostabilizējās. Saturs pārbaudīts pret "
        "dokumentu 74898: 140 000 eiro slieksnis, spēkā stāšanās 2027. gada "
        "1. janvārī, e-katalogu satura pārskatīšana un konkurences mērķis "
        "atbilst avotam."
    ),
    555669: (
        "Pozīcija izriet no žurnālista pārstāstītā raidījuma komentāra; verbatim "
        "citāts šai domai rakstā nav pieejams, tāpēc ticamība pazemināta. "
        "Izvērtēts 2026-08-03: paliek Degviela un enerģētika. Pamats: dokumentā "
        "73873 viņas argumenta ķēde beidzas pie bāzes tarifiem un gaidāmā "
        "elektroenerģijas cenu kāpuma, kas skar iedzīvotājus, tātad kodols ir "
        "cenu veidošanās, nevis kapitālsabiedrības finanšu pārvaldība. Tuvākā "
        "Latvenergo pozīcija, kas glabājas tēmā Valsts kapitālsabiedrības "
        "(claim 532158), atšķiras tieši ar kodolu — tur runa ir par dividenžu "
        "izņemšanu pret uzņēmuma aizņemšanos, ne par ietekmi uz patērētāja cenu."
    ),
    555667: (
        "Tvītā formulēta pirmās personas nostāja par publiskā finansējuma "
        "piešķiršanu nevalstiskajām organizācijām: nosoda nozaru biznesa "
        "biedrību uzturēšanu no nodokļu naudas un pauž, ka uzņēmējiem pašiem "
        "jāfinansē sava interešu aizstāvība. Izvērtēts 2026-08-03: paliek "
        "Budžets un finanses. Pamats: korpusā izveidojies dalījums — pozīcijas, "
        "kas iebilst pret nodokļu naudas novirzīšanu biedrībām, glabājas tēmā "
        "Budžets un finanses (claim 615848, 555823, 555843, 555790), bet "
        "finansēšanas kārtības un nevalstisko organizāciju aizstāvības "
        "pozīcijas nonāk tēmā Valsts pārvalde (claim 555723, 555735, 555756). "
        "Šmita izteikuma kodols ir nodokļu naudas izlietojums, tāpēc tas "
        "iekļaujas pirmajā grupā."
    ),
    548588: (
        "Satiksmes ministra tieša citāta pozīcija pēc padomes sēdes: valstij "
        "būs jādotē ostu infrastruktūras uzturēšana miljonu eiro apmērā. "
        "Pirmpersonas amatpersonas novērtējums. Pārējie raksta pieminējumi "
        "(LDz atstāstījums, autokravu pārvirzīšanas formulējums) ir LDz "
        "pozīciju atstāstīšana, nevis paša Kozlovska nostāja — tos "
        "neekstraktēju. Izvērtēts 2026-08-03: paliek Transports. Pamats: "
        "korpusā ostu un tranzīta nozares pozīcijas dominējoši glabājas šajā "
        "tēmā (14 pozīcijas), un Budžets un finanses netiek izvēlēts tikai "
        "tāpēc, ka nozares infrastruktūras uzturēšanai vajadzīga nauda. Citāts "
        "pārbaudīts pret dokumentu 72059 un sakrīt burtiski; pozīcijas "
        "formulējums par valsts piemaksāšanu balstās raksta kontekstā — padomes "
        "sēde bija par ostu infrastruktūras finansējuma iekļaušanu nākamā gada "
        "budžetā."
    ),
    555822: (
        "Formulēts retoriska jautājuma veidā, taču intervijas kontekstā "
        "(Pulsar Optics konkurence, vietējo ražotāju atbalsts kā prezidentūras "
        "mērķis) nostāja ir viennozīmīga — protekcionisma virziens ES "
        "tirdzniecības politikā. Zemāka pārliecība tieši jautājuma formas dēļ. "
        "Izvērtēts 2026-08-03: paliek ES politika. Pamats: abas iepriekš "
        "minētās alternatīvas atkrīt — Lauksaimniecība neatbilst, jo dokumentā "
        "76632 runa ir par optikas ražotāju Pulsar Optics un rūpniecības "
        "precēm, bet Budžets un finanses izteikumā nav budžeta satura; "
        "tirdzniecības aizsardzība pret Ķīnas precēm ir Eiropas Savienības "
        "kompetence, un korpusā līdzīgās pozīcijas glabājas tēmā ES politika. "
        "Jautājuma forma izvērtēta atsevišķi: tajā pašā intervijā viņš to pašu "
        "nostāju pauž arī apgalvojuma formā — piedāvā tramvaju ražošanu "
        "Daugavpilī kā valstij prioritāru projektu un iebilst pret to pirkšanu "
        "no ārvalstu ražotājiem —, tāpēc retoriskais jautājums nav vienīgais "
        "pozīcijas avots. Ticamība 0.6 paliek negrozīta."
    ),
    555672: (
        "Tiešs citāts par transatlantisko slogu sadali pēc NATO samita. "
        "Izvērtēts 2026-08-03: paliek Ārpolitika. Pamats: kodols ir sabiedroto "
        "attiecības un sloga sadale (ASV loma NATO, Eiropas atbildība), nevis "
        "Latvijas aizsardzības spējas. Tā paša dokumenta otrā pozīcija "
        "(claim 555671) ir saturiski atšķirīga — NBS gatavība atbildēt uz "
        "Krievijas provokācijām — un pamatoti aizņem tēmu Aizsardzība un "
        "drošība; tēmas maiņa sapludinātu abas pozīcijas vienā ierakstā, jo "
        "idempotences trijnieks ir (opponent_id, source_url, topic). Citāts "
        "pārbaudīts pret dokumentu 73872 un sakrīt burtiski."
    ),
}


def sql_quote(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"


def main() -> int:
    apply = "--apply" in sys.argv
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row

    rows = {}
    for cid in NEW_REASONING:
        r = db.execute(
            "SELECT id, opponent_id, topic, reasoning, review_status "
            "FROM claims WHERE id=?", (cid,)
        ).fetchone()
        if r is None:
            print(f"STOP: claim {cid} nav atrasts")
            return 1
        if "NEEDS_REVIEW" not in (r["reasoning"] or ""):
            print(f"STOP: claim {cid} reasoning nesatur NEEDS_REVIEW — jau aizvērts?")
            return 1
        rows[cid] = r

    # rollback PIRMS piemērošanas (CLAUDE.md eskalācijas noteikums #8)
    lines = [
        "-- Rollback: atceļ scripts/fix_needs_review_triage_2026-08-03_b.py",
        "-- Forward change (piemērots 2026-08-03): 6 NEEDS_REVIEW pozīcijas",
        "--   aizvērtas — marķieris 'NEEDS_REVIEW:' aizstāts ar",
        "--   'Izvērtēts 2026-08-03:' un pievienots nosaukts lēmuma pamats.",
        "--   Skarts TIKAI reasoning; topic/stance/quote/confidence nemainīti.",
        "--",
        "-- Embeddings NAV skarti: store_claim() iegulst f\"{topic}: {stance}\",",
        "-- un abi lauki nemainās, tāpēc claim_vectors paliek sinhroni.",
        "-- review_status ir derivēta kolonna — AFTER UPDATE OF reasoning",
        "-- trigeris to pārrēķina pats; ar roku to nerakstīt.",
        "",
        "BEGIN TRANSACTION;",
        "",
    ]
    for cid, r in rows.items():
        lines.append(f"-- atgriež #{cid} (op {r['opponent_id']}, {r['topic']}) reasoning oriģinālu")
        lines.append(f"UPDATE claims SET reasoning = {sql_quote(r['reasoning'])} WHERE id = {cid};")
        lines.append("")
    lines.append("COMMIT;")
    ROLLBACK.write_text("\n".join(lines), encoding="utf-8")
    print(f"rollback uzrakstīts: {ROLLBACK}  ({len(rows)} rindas)")

    if not apply:
        print("\nDRY RUN — nekas nav mainīts. Palaid ar --apply.")
        for cid, r in rows.items():
            print(f"  {cid} op{r['opponent_id']:>4} {r['topic']}: "
                  f"{len(r['reasoning'])} -> {len(NEW_REASONING[cid])} zīmes")
        return 0

    cur = db.cursor()
    cur.execute("BEGIN")
    for cid, text in NEW_REASONING.items():
        cur.execute("UPDATE claims SET reasoning=? WHERE id=?", (text, cid))
        if cur.rowcount != 1:
            db.rollback()
            print(f"STOP: claim {cid} rowcount={cur.rowcount}")
            return 1
    db.commit()
    print(f"piemērots: {len(NEW_REASONING)} rindas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
