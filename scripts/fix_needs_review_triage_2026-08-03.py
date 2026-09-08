"""NEEDS_REVIEW triāža 2026-08-03 — Ceriņš/LDDK/Vītols/Liepnieks/Stendzenieks/Tavars/Krištopans.

Tvērums: 14 `review_status='needs_review'` claims politiķiem 203, 193, 64, 61,
60, 52, 9. Katram izlasīts gan claim, gan avota dokuments.

ATRISINA 9 claims (marķieris `NEEDS_REVIEW:` -> `Izvērtēts 2026-08-03:`,
skaidrojums saglabāts, pievienots lēmums). NEMAINA topic/stance/quote/
confidence, tāpēc `claim_vectors` NAV jāpārrēķina — `store_claim` iegulst
`f"{topic}: {stance}"`, un ne viens, ne otrs netiek aiztikts.

  #555775 Krištopans, Rail Baltica — referents apstiprināts ar tās pašas dienas
          korpusu (doc 76046, 76135 un paša runātāja doc 76420).
  #615802 Krištopans, Valodu politika — pozīcija balstās tikai uz tvīta otro,
          patstāvīgo teikumu; trūkstošā sarunas replika skar tikai pirmo.
  #555777 Tavars, Digitālā politika — valdības puses IKT moratorija izteikumi
          korpusā konsekventi šajā grupā (#547948, #548186, #548312, #555734).
  #555826 Tavars, Transports — rūpniecības grupas 32 kanoniskajās nav; objekts
          ir ritošā sastāva iepirkums.
  #548556 Stendzenieks, Korupcija un KNAB — kodols ir izšķērdēšana un valdības
          atbildība, ne enerģētikas mehānisms.
  #555787 LDDK, Izglītība — zinātnes/pētniecības precedents (14 pret 9);
          raidījuma temats apstiprināts ar doc 76091.
  #555828 LDDK, Pilsētvide — rubrika šajā grupā tieši nosauc urbāno mobilitāti;
          tāpat #548322, #532452, #18035.
  #555790 Ceriņš, Budžets un finanses — NVO izteikumus korpuss šķiro pēc kodola;
          finansējuma kodols -> Budžets un finanses (11 pozīcijas).
  #555871 Ceriņš, Budžets un finanses — "pētīšana" identificēta kā zinātniskie
          pētījumi (doc 76090, 76091 + 30.–31.07. saruna); tēma paliek, jo
          iebildums ir fiskāls.

NEAIZTIEK (5 claims paliek `needs_review`, lēmums operatoram):
  #615871 Liepnieks — retorisks jautājums kā pozīcija (formas jautājums).
  #555710 Liepnieks — apgalvojums par eksperta neitralitāti, ne politikas
          risinājums; tā pati formas robeža.
  #554002 Stendzenieks — stance nosauc referentu ("mobilo sakaru operators"),
          kura dokumentā nav; specifika pārsniedz avotu.
  #555807 Vītols — ekstraktors tieši lūdza operatoram izlemt NVO taksonomiju.
  #555663 Vītols — Kultūra pret Budžets un finanses: divi noteikumi (konkrētais
          objekts pret izteikuma kodolu) rāda pretējos virzienos.

Rollback: data/rollback_needs_review_triage_2026-08-03.sql (ģenerēts PIRMS izmaiņām).

Lietošana:
    .venv/Scripts/python.exe scripts/fix_needs_review_triage_2026-08-03.py --emit-rollback
    .venv/Scripts/python.exe scripts/fix_needs_review_triage_2026-08-03.py --apply
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

DB_PATH = "data/atmina.db"
ROLLBACK_PATH = Path("data/rollback_needs_review_triage_2026-08-03.sql")

MARKER_OLD = "NEEDS_REVIEW:"
MARKER_NEW = "Izvērtēts 2026-08-03:"

# claim_id -> pievienotais lēmuma teksts (marķiera aizstāšana notiek atsevišķi)
DECISIONS: dict[int, str] = {
    555775: (
        " Lēmums: tēma paliek Rail Baltica — referents apstiprināts ar tās pašas "
        "dienas korpusu. 2026-07-29 dokumenti 76046 un 76135 atreferē Kulberga "
        "izteikumu par konsultantu vērtējumu, ka projekta izmaksas pieaugtu līdz "
        "24 miljardiem, bet paša Krištopana tvīts tā paša datuma vakarā (dok. "
        "76420) tieši nosauc neatkarīgo Spānijas ekspertu auditu par Rail Baltica "
        "un atsaucas uz TV3 ziņām. Interpretācija tādējādi vairs nav vienīgi "
        "runātāja iepriekšējo pozīciju konteksts."
    ),
    615802: (
        " Lēmums: pozīcija paliek. Tā balstās vienīgi uz tvīta otro teikumu, kas "
        "ir paša formulēts un saturiski patstāvīgs; trūkstošā sarunas biedra "
        "replika attiecas tikai uz pirmo teikumu ('Saprotu un piekrītu'), kas "
        "pozīcijā nav izmantots. Salīdzinājums 'daudz lielāka problēma par krievu "
        "valodu' ir jēdzīgs vienīgi parādības, ne atsevišķa vārda līmenī, tāpēc "
        "vispārinājums uz anglicismu izplatību ir pamatots. Ticamība 0,6 saglabāta."
    ),
    555777: (
        " Lēmums: tēma paliek Digitālā politika. Korpusā valdības puses izteikumi "
        "par IKT lielo iepirkumu moratoriju ir konsekventi šajā grupā (#547948, "
        "#548186, #548312, #555734), savukārt Korupcija un KNAB lietota tad, kad "
        "kodols ir krāpšana vai karteļi (#548193, #548344, #615792, arī paša "
        "Tavara #532213 par dienesta pārbaudi). Šis izteikums ir par iepirkumu "
        "saskaņošanas kārtību, tāpēc atbilst pirmajai rindai."
    ),
    555826: (
        " Lēmums: tēma paliek Transports. 32 kanoniskajās grupās rūpniecības "
        "politikas nav, un izteikuma konkrētais objekts ir ritošā sastāva — "
        "vilcienu vagonu un tramvaju — iepirkums, tāpēc Transports ir tuvākā "
        "grupa; Valsts pārvalde vai Budžets un finanses aptvertu iepirkuma formu, "
        "ne saturu. Blakus esošais izteikums no tās pašas intervijas par armijas "
        "apgādi glabāts atsevišķi (#555827, Aizsardzība un drošība)."
    ),
    548556: (
        " Lēmums: tēma paliek Korupcija un KNAB. Izteikuma kodols ir valdības "
        "atbildība par miljardu izšķērdēšanu un skaidra signāla nesniegšana "
        "sabiedrībai; OIK šeit ir izšķērdēšanas objekts, un, to izņemot, pozīcija "
        "saglabājas. Degviela un enerģētika būtu pareizā grupa tikai izteikumam "
        "par pašu obligātā iepirkuma komponentes mehānismu."
    ),
    555787: (
        " Lēmums: tēma paliek Izglītība. Korpusā zinātnes un pētniecības "
        "izteikumi biežāk ir šajā grupā (14 pozīcijas pret 9 grupā Budžets un "
        "finanses), un Budžets un finanses lietota tad, kad kodols ir valsts "
        "izdevumu apjoms. Raidījuma tematu apstiprina pašas LDDK ieraksts (dok. "
        "76091, 2026-07-29): saruna bija par valsts finansējumu zinātniskiem "
        "pētījumiem."
    ),
    555828: (
        " Lēmums: tēma paliek Pilsētvide. Rubrika šajā grupā tieši nosauc urbāno "
        "mobilitāti, un runa ir par Rīgas satiksmes organizāciju viena tilta "
        "pārbūves laikā, nevis par valsts transporta politiku. Tāda pati izvēle "
        "izdarīta citiem Vanšu tilta izteikumiem (#548322, #532452, #18035)."
    ),
    555790: (
        " Lēmums: tēma paliek Budžets un finanses. Korpusā NVO izteikumi tiek "
        "šķiroti pēc izteikuma kodola, nevis pēc nozares: kur runa ir par "
        "finansējuma piešķiršanu, lietota Budžets un finanses (11 pozīcijas), kur "
        "par sektora pārvaldību — Valsts pārvalde (26 pozīcijas). Šī izteikuma "
        "kodols ir finansējuma pārskatīšana."
    ),
    555871: (
        " Lēmums: nozare noskaidrota — runa ir par zinātniskajiem pētījumiem, ne "
        "izmeklēšanu. Tvīts atsaucas uz Andri Biti, kura tās nedēļas publiskais "
        "izteikums bija tieši par valsts finansējumu zinātniskiem pētījumiem "
        "(dok. 76090 un 76091, 2026-07-29), un 30.–31. jūlija sarunā X par to "
        "pašu strīdu iesaistījās gan atbalstītāji, gan kritiķi (dok. 77677, "
        "76697, 77697). Tēma paliek Budžets un finanses, jo Ceriņa iebildums ir "
        "fiskāls — nodokļu maksātāju bāze un aizņemšanās apjoms, ne pētniecības "
        "saturs."
    ),
}


def _connect() -> sqlite3.Connection:
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db


def _sql_str(v) -> str:
    if v is None:
        return "NULL"
    if isinstance(v, (int, float)):
        return str(v)
    return "'" + str(v).replace("'", "''") + "'"


def emit_rollback(db: sqlite3.Connection) -> int:
    lines = [
        "-- Rollback: atceļ scripts/fix_needs_review_triage_2026-08-03.py",
        "-- Forward change (piemērots 2026-08-03): 9 NEEDS_REVIEW claims aizvērti —",
        "--   marķieris 'NEEDS_REVIEW:' aizstāts ar 'Izvērtēts 2026-08-03:' un",
        "--   pievienots lēmuma pamatojums. Mainīts TIKAI reasoning teksts.",
        "-- Pamatojums katram gadījumam: skripta docstring.",
        "--",
        "-- Embeddings NAV skarti: topic un stance nemainās, tāpēc claim_vectors",
        "-- paliek sinhroni un pārrēķins nav vajadzīgs (nedz uz priekšu, nedz atpakaļ).",
        "-- review_status ir DERIVĒTA kolonna — AFTER UPDATE OF reasoning trigeris to",
        "-- pārrēķina pats; ar roku to nerakstīt.",
        "",
        "BEGIN TRANSACTION;",
        "",
    ]
    missing = []
    for cid in sorted(DECISIONS):
        r = db.execute("SELECT reasoning FROM claims WHERE id = ?", (cid,)).fetchone()
        if r is None:
            missing.append(cid)
            lines.append(f"-- claim {cid}: nav DB")
            continue
        lines.append(f"-- atgriež #{cid} reasoning tekstu (pilns oriģināls)")
        lines.append(
            f"UPDATE claims SET reasoning = {_sql_str(r['reasoning'])} WHERE id = {cid};"
        )
        lines.append("")
    lines.append("COMMIT;")
    ROLLBACK_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Rollback uzrakstīts: {ROLLBACK_PATH} ({len(DECISIONS) - len(missing)} rindas)")
    if missing:
        print(f"  ! nav DB: {missing}")
        return 1
    return 0


def apply(db: sqlite3.Connection) -> int:
    changed = 0
    for cid, decision in DECISIONS.items():
        r = db.execute(
            "SELECT reasoning, review_status FROM claims WHERE id = ?", (cid,)
        ).fetchone()
        if r is None:
            print(f"  ! #{cid}: nav DB — apturu, nekas nemainīts")
            return 1
        old = r["reasoning"]
        if old.count(MARKER_OLD) != 1:
            print(
                f"  ! #{cid}: gaidīju tieši 1 '{MARKER_OLD}', atradu "
                f"{old.count(MARKER_OLD)} — apturu, nekas nemainīts"
            )
            return 1
        new = old.replace(MARKER_OLD, MARKER_NEW) + decision
        if "NEEDS_REVIEW" in new:
            print(f"  ! #{cid}: marķieris palicis tekstā — apturu")
            return 1
        db.execute("UPDATE claims SET reasoning = ? WHERE id = ?", (new, cid))
        changed += 1
        print(f"  ✓ #{cid} marķieris aizvērts ({len(old)} -> {len(new)} zīmes)")

    # Verifikācija PIRMS commit: trigerim jābūt pārlicis visas 9 uz 'reviewed'.
    bad = db.execute(
        "SELECT id, review_status FROM claims WHERE id IN "
        f"({','.join(str(c) for c in DECISIONS)}) AND review_status IS NOT 'reviewed'"
    ).fetchall()
    if bad:
        print(f"  ! trigeris neizdevās: {[dict(b) for b in bad]} — ROLLBACK")
        db.rollback()
        return 1
    db.commit()
    print(f"Pabeigts: {changed} claims -> review_status='reviewed'")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--emit-rollback", action="store_true")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    if not (args.emit_rollback or args.apply):
        ap.error("norādi --emit-rollback vai --apply")

    db = _connect()
    try:
        if args.emit_rollback:
            return emit_rollback(db)
        if not ROLLBACK_PATH.exists():
            print(f"APTURU: {ROLLBACK_PATH} neeksistē. Palaid --emit-rollback pirms --apply.")
            return 1
        return apply(db)
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
