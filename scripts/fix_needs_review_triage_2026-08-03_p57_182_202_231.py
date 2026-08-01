"""NEEDS_REVIEW triāža 2026-08-03 — politiķi 57, 182, 202, 231.

Tvērums: 14 `review_status='needs_review'` claims četriem žurnālistu kontiem
(57 Lato Lapsa, 182 Otto Ozols, 202 Marats Kasems, 231 Krišjānis Kļaviņš).
Katrs claim izlasīts kopā ar avota dokumentu.

Šis skripts AIZVER 7 claims, kuru šaubas ir atbildamas ar nosauktu pamatu
(rubrikas tests tēmai vai korpusa precedents). `NEEDS_REVIEW` marķieris tiek
aizstāts ar `Izvērtēts 2026-08-03:`; teksts PIRMS marķiera saglabāts burtiski
(griežam pēc marķiera indeksa, nevis pārrakstām).

  #555757 Lapsa, Tieslietas — robeža pret Valsts pārvalde. Pamats: korpusa
          precedents (555691, 20415, 14413, 10972, 6831 — visi Tieslietas).
  #555792 Kasems, Kultūra — robeža pret Imigrācija / Ukraina un Krievija.
          Pamats: 531939 = ieceļošanas liegums -> Imigrācija; 548587 = tiesisks
          ievešanas aizliegums -> Ukraina un Krievija; 17868 = Krievijas
          naratīvi kultūras saturā -> Kultūra (tuvākais precedents).
  #555799 Lapsa, Tieslietas — robeža pret Digitālā politika. Pamats: rubrika
          (Digitālā politika = e-pakalpojumi/dati/AI/kiberdrošība), plus
          korpusā kriminālatbildības grozījumi ir Tieslietas (614937-614948).
  #555859 Kļaviņš, ES politika — robeža pret Imigrācija. Pamats: kodola tests
          (izņem Šengenu -> pozīcija sabrūk).
  #555870 Kasems, Ukraina un Krievija — robeža pret Valsts pārvalde /
          Sabiedriskie mediji. Pamats: abas alternatīvas izslēdz rubrika.
  #615790 Lapsa, Vēlēšanas — sarkasma apgriešana. Pamats: pejoratīvi tajā pašā
          teikumā + precedents 20727; "zilzemnieki" -> ZZS, jo tā ir vienīgā
          `parties` rinda ar "Zemnieku" nosaukumā.
  #615836 Kļaviņš, Vēlēšanas — robeža pret Ukraina un Krievija / Korupcija un
          KNAB. Pamats: rubrikas tests "vai paliktu aktuāls bez vēlēšanām".

NEAIZTIEK `topic`, `stance`, `quote`, `confidence`, `salience` — tikai
`reasoning`. Tāpēc embedding pārrēķins NAV vajadzīgs: `store_claim()` iegulst
`f"{topic}: {stance}"`, un ne viens, ne otrs netiek mainīts.

NERAKSTA `review_status` — to uztur triggeri `claims_review_status_ai/au`.

ĀRPUS ŠĪ SKRIPTA (operatora lēmums, nekas netiek rakstīts) — 7 claims:
  (B) 548550, 555812, 555830, 555891, 615796, 615799
  (C) 555644
  Pamatojums katram — sesijas atskaitē.

Rollback: data/rollback_needs_review_triage_2026-08-03_p57_182_202_231.sql
(ģenerēts PIRMS izmaiņām, satur pilnu oriģinālo `reasoning` tekstu).

Lietošana:
    .venv/Scripts/python.exe scripts/fix_needs_review_triage_2026-08-03_p57_182_202_231.py --emit-rollback
    .venv/Scripts/python.exe scripts/fix_needs_review_triage_2026-08-03_p57_182_202_231.py --apply
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

DB_PATH = "data/atmina.db"
ROLLBACK_PATH = Path(
    "data/rollback_needs_review_triage_2026-08-03_p57_182_202_231.sql"
)

MARKER = "NEEDS_REVIEW"

# claim_id -> (gaidītais opponent_id, gaidītā tēma, jaunais `Izvērtēts` teksts).
# Teksts PIRMS marķiera tiek saglabāts burtiski; šis nāk tā vietā.
RESOLVE: dict[int, tuple[int, str, str]] = {
    555757: (
        57,
        "Tieslietas",
        "Izvērtēts 2026-08-03: tēmas robeža bija starp Tieslietas un Valsts "
        "pārvalde; paliek Tieslietas. Pamats — Lapsas kritika par "
        "tiesībaizsardzības iestādēm korpusā konsekventi klasificēta kā "
        "Tieslietas (claims 555691, 20415, 14413, 10972, 6831), savukārt Valsts "
        "pārvalde attiektos uz iestāžu organizāciju, nevis uz pilnvaru robežām "
        "attiecībā pret iedzīvotājiem. Stance paliek avota robežās, un "
        "pārliecība 0,6 atbilst tam, ka konkrēts politikas priekšlikums nav "
        "formulēts.",
    ),
    555792: (
        202,
        "Kultūra",
        "Izvērtēts 2026-08-03: tēmas robeža bija starp Kultūra, Imigrācija un "
        "Ukraina un Krievija; paliek Kultūra. Pamats — izteikuma priekšmets ir "
        "koncertdarbība Latvijā, nevis ieceļošanas liegums (tas ir Imigrācija, "
        "sal. claim 531939) un nevis tiesisks ievešanas aizliegums (tas ir "
        "Ukraina un Krievija, sal. claim 548587); tuvākais precedents Kasema "
        "korpusā ir claim 17868 par Krievijas naratīviem kultūras saturā, kas "
        "arī ir Kultūra. Robeža ir šaura, taču saglabātā vērtība rubrikā ir "
        "aizstāvama, tāpēc tēmas migrācija netiek ierosināta.",
    ),
    555799: (
        57,
        "Tieslietas",
        "Izvērtēts 2026-08-03: tēmas robeža bija starp Tieslietas un Digitālā "
        "politika; paliek Tieslietas. Pamats — rubrikā Digitālā politika aptver "
        "e-pakalpojumus, datu aizsardzību, AI regulējumu un kiberdrošību, bet ne "
        "kriminālatbildību par izteikumiem; korpusā kriminālatbildības grozījumi "
        "konsekventi ir Tieslietas (claims 614937-614948). Norāde par asu "
        "izteiksmi ir atrisināta jau saglabātajā tekstā: stance ir neitrāla, "
        "citāts nav saglabāts un neviens politiķis nav nosaukts vārdā, tāpēc "
        "atsevišķs operatora lēmums pirms publicēšanas nav vajadzīgs.",
    ),
    555859: (
        231,
        "ES politika",
        "Izvērtēts 2026-08-03: tēmas robeža bija starp ES politika un "
        "Imigrācija; paliek ES politika. Pamats — kodola tests: ja no izteikuma "
        "izņem Šengenas zonu, pozīcija sabrūk, jo prasība ir par dalības "
        "mehānismu, savukārt nelegālā imigrācija ir tikai pamatojums. Stance ir "
        "avota robežās un citāts ir verbatim pirmajā personā, tāpēc pārliecība "
        "0,8 ir atbilstoša.",
    ),
    555870: (
        202,
        "Ukraina un Krievija",
        "Izvērtēts 2026-08-03: tēma bija neskaidra starp Ukraina un Krievija, "
        "Valsts pārvalde un Sabiedriskie mediji; paliek Ukraina un Krievija. "
        "Pamats — rubrikā Sabiedriskie mediji attiecas uz sabiedrisko mediju "
        "politiku, nevis uz dezinformāciju vispār, bet Valsts pārvalde prasītu, "
        "lai kodols būtu ministru atlases kārtība; šajā izteikumā tā nav. Paliek "
        "Kremļa naratīva atspēkošana, ko apstiprina arī paša tvīta birka "
        "#propaganda un norāde, ka Mamikins uzstājas Krievijas televīzijā.",
    ),
    615790: (
        57,
        "Vēlēšanas",
        "Izvērtēts 2026-08-03: šaubas bija par sarkasma apgriešanu — burtiski "
        "tvīts aicina balsot PAR šīm partijām. Apgriešana apstiprināta: tajā "
        "pašā teikumā partijas nosauktas par vēzi un sērgu, kas ar patiesu "
        "aicinājumu balsot nav savienojams, un tas saskan ar 2026-05-22 fiksēto "
        "aicinājumu neatbalstīt Progresīvos (claim 20727). Apzīmējums "
        "“zilzemnieki” attiecināts uz Zaļo un Zemnieku savienību, jo "
        "tā ir vienīgā partija `parties` tabulā, kuras nosaukumā ir "
        "“Zemnieku”. Stance pati norāda uz ironisko formu, tāpēc "
        "lasītājs netiek maldināts. Norāde “par šo” attiecas uz "
        "pievienoto materiālu, kas dokumenta tekstā nav redzams, taču stance to "
        "neinterpretē. Tvīts ir Lapsas paša formulējums, nevis cita autora "
        "pārpublicējums.",
    ),
    615836: (
        231,
        "Vēlēšanas",
        "Izvērtēts 2026-08-03: tēmas robeža bija starp Vēlēšanas, Ukraina un "
        "Krievija un Korupcija un KNAB; paliek Vēlēšanas. Pamats — rubrikas "
        "tests “vai izteikums paliktu aktuāls arī bez tuvajām vēlēšanām” "
        "dod noliedzošu atbildi: rāmis ir partiju reitingi un nākamās Saeimas "
        "sastāvs, bet Krievijas ietekme un iepirkumu karteļi ir apgalvojuma "
        "saturs, ne tā ietvars. Apgalvojums saglabāts ar atribūcijas norādi "
        "“apgalvo” un autora paša modalitāti “var pārstāt "
        "eksistēt”; deputāti nav nosaukti vārdā, tāpēc atsevišķs reputācijas "
        "izvērtējums nav vajadzīgs.",
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


def _new_reasoning(old: str, replacement: str) -> str:
    """Saglabā tekstu pirms marķiera burtiski, marķiera vietā liek `Izvērtēts`."""
    idx = old.index(MARKER)
    prefix = old[:idx]
    return prefix + replacement


def emit_rollback(db: sqlite3.Connection) -> int:
    lines = [
        "-- Rollback: atceļ "
        "scripts/fix_needs_review_triage_2026-08-03_p57_182_202_231.py",
        "-- Forward change (piemērots 2026-08-03): NEEDS_REVIEW triāža politiķiem",
        "--   57 (Lapsa), 182 (Ozols), 202 (Kasems), 231 (Kļaviņš).",
        "--   7 claims: `NEEDS_REVIEW` marķieris aizstāts ar `Izvērtēts 2026-08-03:`.",
        "--   Mainīts TIKAI `reasoning`; topic/stance/quote/confidence neskarti,",
        "--   tāpēc `claim_vectors` pārrēķins NAV vajadzīgs ne turp, ne atpakaļ.",
        "--   `review_status` atjaunojas pats ar triggeri claims_review_status_au.",
        "-- Pamatojums katram gadījumam: skripta docstring.",
        "",
        "BEGIN TRANSACTION;",
        "",
    ]
    missing = []
    for cid in sorted(RESOLVE):
        r = db.execute(
            "SELECT reasoning, topic, opponent_id FROM claims WHERE id = ?", (cid,)
        ).fetchone()
        if r is None:
            missing.append(cid)
            continue
        lines.append(f"-- #{cid} (pid {r['opponent_id']}, {r['topic']})")
        lines.append(
            f"UPDATE claims SET reasoning = {_sql_str(r['reasoning'])} "
            f"WHERE id = {cid};"
        )
        lines.append("")
    if missing:
        print(f"APTURU: claims nav DB: {missing}")
        return 1
    lines.append("COMMIT;")
    ROLLBACK_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Rollback uzrakstīts: {ROLLBACK_PATH} ({len(RESOLVE)} claims)")
    return 0


def apply(db: sqlite3.Connection) -> int:
    changed = 0
    for cid, (exp_pid, exp_topic, replacement) in sorted(RESOLVE.items()):
        r = db.execute(
            "SELECT opponent_id, topic, reasoning, review_status "
            "FROM claims WHERE id = ?",
            (cid,),
        ).fetchone()
        if r is None:
            print(f"  ! #{cid}: nav DB — apturu, nekas necommitots")
            return 1
        if r["opponent_id"] != exp_pid or r["topic"] != exp_topic:
            print(
                f"  ! #{cid}: gaidīju pid={exp_pid} topic={exp_topic!r}, "
                f"atradu pid={r['opponent_id']} topic={r['topic']!r} — apturu"
            )
            return 1
        if MARKER not in r["reasoning"]:
            print(f"  ! #{cid}: marķieris {MARKER} nav atrasts — apturu")
            return 1
        new = _new_reasoning(r["reasoning"], replacement)
        if MARKER in new:
            print(f"  ! #{cid}: {MARKER} palicis jaunajā tekstā — apturu")
            return 1
        if "Izvērtēts 2026-08-03:" not in new:
            print(f"  ! #{cid}: jaunajā tekstā trūkst Izvērtēts marķiera — apturu")
            return 1
        db.execute("UPDATE claims SET reasoning = ? WHERE id = ?", (new, cid))
        changed += 1
        print(f"  ✓ #{cid} (pid {exp_pid}, {exp_topic}) marķieris aizstāts")

    # Triggera verifikācija PIRMS commit.
    bad = db.execute(
        "SELECT id, review_status FROM claims WHERE id IN "
        f"({','.join(str(c) for c in RESOLVE)}) AND review_status != 'reviewed'"
    ).fetchall()
    if bad:
        print(f"  ! trigger nav uzstādījis 'reviewed': {[dict(b) for b in bad]}")
        db.rollback()
        return 1

    db.commit()
    print(f"Commitots: {changed} claims -> review_status='reviewed'")
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
            print(
                f"APTURU: {ROLLBACK_PATH} neeksistē. "
                "Palaid --emit-rollback pirms --apply."
            )
            return 1
        return apply(db)
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
