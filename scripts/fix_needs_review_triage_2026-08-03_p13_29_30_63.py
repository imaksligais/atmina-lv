"""NEEDS_REVIEW triāža 2026-08-03 — politiķu izlase 63, 30, 29, 13.

Konteksts: 13 atvērti `review_status='needs_review'` claims Rajevskim (63),
Baško (30), Alvim Hermanim (29) un Jānim Hermanim (13). Katram izlasīts gan
claim, gan avota dokuments. Klasifikācija: 8 atrisināmi (šis skripts), 4 paliek
operatoram, 1 prasa labojumu, ko šis skripts NEDARA.

Skripts skar TIKAI `claims.reasoning`: `NEEDS_REVIEW:` marķieris aizstāts ar
`Izvērtēts 2026-08-03:` (kanoniskā forma — CLAUDE.md eskalācijas nots. #2 +
wiki/operations/weekly-routine.md) un beigās pievienots lēmuma teikums ar
nosauktu pamatu. `topic`/`stance`/`quote`/`confidence` NETIEK aiztikti, tāpēc
`claim_vectors` pārrēķins NAV vajadzīgs — `store_claim` iegulst
`f"{topic}: {stance}"`, un reasoning tajā neietilpst.

ATRISINA 8 claims (visos flagotais jautājums bija tēmas robeža):
  #615855 J. Hermanis, Budžets un finanses — paša eksporta/ekonomikas pozīcijas
          (#254, #276, #7019, #547904, #547905) ir tajā pašā tēmā; Valsts pārvaldē
          ir tikai birokrātijas sloga izmaksu pozīcija #7021.
  #553949 A. Hermanis, Korupcija un KNAB — Rail Baltica un mediji ir ilustrācijas,
          kodols ir apgalvojums par valsts naudas izzagšanu.
  #615824 A. Hermanis, Koalīcija un partijas — reitingi ir ievads, kodols ir
          koalīcijas partneru izvēle (tēmu rubrikas tests, 2026-06-10).
  #615825 A. Hermanis, Valsts pārvalde — 'railbaltikiem' daudzskaitlī = projektu
          kategorija, prasība ir strukturāla, ne budžeta sadales jautājums.
  #615872 A. Hermanis, Budžets un finanses — gandrīz identiskā #532403 (27.06.)
          jau ir tajā pašā tēmā.
  #615808 Baško, Korupcija un KNAB — dalītais precedents izšķirts par labu
          tuvākajam (#548144 = tas pats asimetrijas arguments).
  #555844 Rajevskis, Sociālā politika — korpusā demogrāfijas pozīcijas dominējoši
          ir Sociālajā politikā (23 pret 1 Budžetā un finansēs).
  #615816 Rajevskis, Valsts pārvalde — precedenti #555753/#555803; policijas
          saturs korpusā dominējoši Valsts pārvaldē (1394 pozīcijas).

NEAIZTIEK (paliek `needs_review`, lēmums operatoram):
  #553940 Baško, ES politika, conf 0.5 — flags prasīja pārbaudīt iniciatīvas
          saturu. Korpuss to atbild: doc 53372 skaidro, ka SAVE EUROPE ACT ir ES
          pilsoņu iniciatīva nelegālās imigrācijas apturēšanai, un claim #531935
          par TO PAŠU iniciatīvu ir tēmā 'Imigrācija'. Tātad tēma, visticamāk,
          jālabo, un tas ir `topic` mutācija ar embedding pārrēķinu — ārpus šī
          skripta tvēruma. Idempotences sadursme pārbaudīta: nav.
  #555665 Baško, Vēlēšanas — aģenta pamatojums balstās uz 'priekšvēlēšanu
          kontekstu', kura dokumentā (73915) nav; Pilsētvide/Pašvaldības dzīvas
          alternatīvas.
  #615865 Baško, Valsts pārvalde — vienīgais tiešais precedents #169 ('Atbalsta
          tautas vēlētu prezidentu') ir tēmā 'Vēlēšanas', t.i. pretējs aģenta
          izvēlei.
  #615791 Rajevskis, Valsts pārvalde, conf 0.5 — divas šaubas; otrā (t.co saites
          saturs nav pieejams + 'nevis konkrēta politikas prasība') no korpusa
          nav atrisināma.
  #555896 Rajevskis, Veselības aprūpe — tēma ir pareiza, BET stance noņem avota
          hedžus ('iespējams, sākuši pirkt vairāk' -> 'mudina iepirkt vairāk';
          'visbiežāk' izlaists). Stance labojums ir operatora lēmums.

Rollback: data/rollback_needs_review_triage_2026-08-03_p13_29_30_63.sql
(ģenerēts PIRMS izmaiņām, satur pilnu oriģinālo reasoning tekstu).

NB: tā paša datuma paralēlā sesija raksta
data/rollback_needs_review_triage_2026-08-03.sql (rindas 548475, 554001, 555717,
555719, 555786, 555815, 555890) — kopu ar šo nav.

Lietošana:
    .venv/Scripts/python.exe scripts/fix_needs_review_triage_2026-08-03_p13_29_30_63.py --emit-rollback
    .venv/Scripts/python.exe scripts/fix_needs_review_triage_2026-08-03_p13_29_30_63.py --apply
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

DB_PATH = "data/atmina.db"
ROLLBACK_PATH = Path("data/rollback_needs_review_triage_2026-08-03_p13_29_30_63.sql")

MARKER_OLD = "NEEDS_REVIEW:"
MARKER_NEW = "Izvērtēts 2026-08-03:"

# claim_id -> lēmuma teikums, ko pievieno reasoning beigās.
DECISIONS = {
    615855: (
        "Lēmums (triāža 2026-08-03): tēma paliek Budžets un finanses — autora "
        "agrākās eksporta un ekonomikas pozīcijas (#254, #276, #7019, #547904, "
        "#547905) ir tajā pašā tēmā, bet Valsts pārvaldē ievietota tikai "
        "birokrātijas sloga izmaksu pozīcija #7021; šeit birokrātisko šķēršļu "
        "mazināšana ir viens no argumentiem, ne izteikuma kodols. Retvīta "
        "izcelsme jau atspoguļota ar quote=None un pazeminātu ticamību."
    ),
    553949: (
        "Lēmums (triāža 2026-08-03): tēma paliek Korupcija un KNAB — abus "
        "piemērus vieno apgalvojums par valsts naudas izzagšanu, tāpēc Rail "
        "Baltica un mediji ir ilustrācijas, ne izteikuma priekšmets; tā pati "
        "izvēle ir plurālā autora līdzīgo apgalvojumu kopā."
    ),
    615824: (
        "Lēmums (triāža 2026-08-03): tēma paliek Koalīcija un partijas — pēc "
        "tēmu rubrikas testa (2026-06-10) reitingi ir tikai izteikuma ievads, "
        "bet kodols ir koalīcijas partneru izvēle, kas paliktu aktuāla arī bez "
        "tuvajām vēlēšanām."
    ),
    615825: (
        "Lēmums (triāža 2026-08-03): tēma paliek Valsts pārvalde — avota vārds "
        "'railbaltikiem' lietots daudzskaitlī kā projektu kategorija, tāpēc tā "
        "nav pozīcija par konkrēto projektu, un prasība ir strukturāla "
        "(likvidēt iespēju, ka šādas struktūras rodas), ne budžeta sadales "
        "jautājums."
    ),
    615872: (
        "Lēmums (triāža 2026-08-03): tēma paliek Budžets un finanses — kodols "
        "ir ekonomiskā modeļa raksturojums, un gandrīz identiskā pozīcija "
        "#532403 (27.06.2026.) jau ir tajā pašā tēmā; maiņa sašķeltu vienu "
        "argumentu divās tēmās."
    ),
    615808: (
        "Lēmums (triāža 2026-08-03): tēma paliek Korupcija un KNAB — dalītais "
        "precedents izšķirts par labu tuvākajam: #548144 ir tieši tas pats "
        "asimetrijas arguments (biedrības drīkst, partijas nedrīkst) un ir šajā "
        "tēmā, savukārt #548107 attiecas uz aģitācijas aizliegumiem, kas ir cits "
        "priekšmets. Partiju finansēšanas uzraudzība Latvijā ir KNAB kompetencē, "
        "tāpēc izvēle atbilst arī tēmas institucionālajam saturam."
    ),
    555844: (
        "Lēmums (triāža 2026-08-03): tēma paliek Sociālā politika — atsevišķas "
        "demogrāfijas tēmas 32 kanonisko grupu vidū nav, un korpusā demogrāfijas "
        "pozīcijas dominējoši atrodas tieši Sociālajā politikā (23 pozīcijas "
        "pret 1 Budžetā un finansēs), tostarp tās pašas dienas #615877. Budžets "
        "un finanses novietotu kultūras diagnozi fiskālā tēmā."
    ),
    615816: (
        "Lēmums (triāža 2026-08-03): tēma paliek Valsts pārvalde — pozīcijas "
        "priekšmets ir dienesta kontroles mehānisms, tā pati izvēle lietota "
        "saistītajām policijas disciplīnas pozīcijām #555753 un #555803, un "
        "korpusā policijas saturs dominējoši atrodas Valsts pārvaldē."
    ),
}

CLAIM_IDS = sorted(DECISIONS)

# Nedrīkst mainīties — pēc --apply salīdzina baitu pa baitam.
FROZEN_COLS = ["topic", "stance", "quote", "confidence", "salience", "source_url"]


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


def _new_reasoning(old: str, cid: int) -> str:
    return old.replace(MARKER_OLD, MARKER_NEW, 1).rstrip() + " " + DECISIONS[cid]


def emit_rollback(db: sqlite3.Connection) -> int:
    lines = [
        "-- Rollback: atceļ scripts/fix_needs_review_triage_2026-08-03_p13_29_30_63.py",
        "-- Uz priekšu vērstā izmaiņa (piemērota 2026-08-03): NEEDS_REVIEW triāža",
        "--   politiķu izlasei 63 (Rajevskis), 30 (Baško), 29 (A. Hermanis), 13 (J. Hermanis).",
        "--   8 rindām claims.reasoning marķieris 'NEEDS_REVIEW:' aizstāts ar",
        "--   'Izvērtēts 2026-08-03:' un pievienots lēmuma teikums:",
        "--   " + ", ".join(str(c) for c in CLAIM_IDS) + ".",
        "--",
        "-- Skar TIKAI reasoning — topic/stance/quote/confidence nav aiztikti, tāpēc",
        "-- claim_vectors pārrēķins NAV vajadzīgs (embedding = topic || ': ' || stance).",
        "-- review_status ir atvasināts ar trigeri AFTER UPDATE OF reasoning, tāpēc tas",
        "-- atgriežas 'needs_review' pats no sevis, tiklīdz oriģinālais teksts ir atlikts.",
        "",
        "BEGIN TRANSACTION;",
        "",
    ]
    missing = []
    for cid in CLAIM_IDS:
        r = db.execute(
            "SELECT reasoning, review_status FROM claims WHERE id = ?", (cid,)
        ).fetchone()
        if r is None:
            missing.append(cid)
            continue
        lines.append(f"-- atgriež #{cid} reasoning (pilns oriģināls, review_status="
                     f"{r['review_status']})")
        lines.append(
            f"UPDATE claims SET reasoning = {_sql_str(r['reasoning'])} WHERE id = {cid};"
        )
        lines.append("")
    if missing:
        print(f"APTURU: DB nav claims {missing}")
        return 1
    lines.append("COMMIT;")
    lines.append("")
    lines.append(f"-- Pārbaude pēc atgriešanas (jābūt {len(CLAIM_IDS)}):")
    lines.append("-- SELECT COUNT(*) FROM claims WHERE review_status = 'needs_review'")
    lines.append("--   AND id IN (" + ", ".join(str(c) for c in CLAIM_IDS) + ");")
    ROLLBACK_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Rollback uzrakstīts: {ROLLBACK_PATH} ({len(CLAIM_IDS)} rindas)")
    return 0


def apply(db: sqlite3.Connection) -> int:
    before = {}
    for cid in CLAIM_IDS:
        r = db.execute(
            f"SELECT reasoning, review_status, {', '.join(FROZEN_COLS)} "
            "FROM claims WHERE id = ?",
            (cid,),
        ).fetchone()
        if r is None:
            print(f"APTURU: #{cid} nav DB")
            return 1
        if r["review_status"] != "needs_review":
            print(f"APTURU: #{cid} review_status={r['review_status']!r}, gaidīju "
                  "'needs_review' — kāds cits jau to ir mainījis")
            return 1
        n = r["reasoning"].count(MARKER_OLD)
        if n != 1:
            print(f"APTURU: #{cid} satur {n} 'NEEDS_REVIEW' marķierus, gaidīju tieši 1")
            return 1
        before[cid] = {c: r[c] for c in FROZEN_COLS}

    for cid in CLAIM_IDS:
        old = db.execute("SELECT reasoning FROM claims WHERE id = ?", (cid,)).fetchone()[0]
        new = _new_reasoning(old, cid)
        if MARKER_OLD in new:
            print(f"APTURU: #{cid} pēc aizvietošanas joprojām satur marķieri")
            return 1
        db.execute("UPDATE claims SET reasoning = ? WHERE id = ?", (new, cid))
        print(f"  ✓ #{cid} marķieris aizstāts")

    # Verifikācija PIRMS commit: trigeris + iesaldētie lauki.
    bad = 0
    for cid in CLAIM_IDS:
        r = db.execute(
            f"SELECT reasoning, review_status, {', '.join(FROZEN_COLS)} "
            "FROM claims WHERE id = ?",
            (cid,),
        ).fetchone()
        if r["review_status"] != "reviewed":
            print(f"  ! #{cid}: review_status={r['review_status']!r}, gaidīju 'reviewed'")
            bad += 1
        if "NEEDS_REVIEW" in r["reasoning"] or "Izvērtēts 2026-08-03:" not in r["reasoning"]:
            print(f"  ! #{cid}: reasoning marķieris nav pareizs")
            bad += 1
        for c in FROZEN_COLS:
            if r[c] != before[cid][c]:
                print(f"  ! #{cid}: {c} MAINĪJIES ({before[cid][c]!r} -> {r[c]!r})")
                bad += 1
    if bad:
        db.rollback()
        print(f"APTURU: {bad} verifikācijas kļūdas, transakcija atritināta")
        return 1

    db.commit()
    print(f"OK: {len(CLAIM_IDS)} rindas atrisinātas, {len(FROZEN_COLS)} iesaldētie "
          "lauki nemainīti katrā")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="NEEDS_REVIEW triāža 2026-08-03 (63/30/29/13)")
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
