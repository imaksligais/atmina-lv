"""Mērķēta trūkstošo Saeimas balsojumu ielāde no parity audita — ar (datums, laiks) vārtiem.

Pretstatā `p3_backfill_year_urllib.py --year N`, kas iet cauri visam gadam un
dedublē TIKAI pēc URL (src/saeima/votes.py:413): tā kā titania pārarhivē lapas
ar jauniem UNID, akls gada palaidiens ievieto dublikātus jau esošiem
balsojumiem. Šis skripts ņem `audit_saeima_agenda_parity.py` izvades JSON un
ielādē tikai to, kas tur atzīmēts kā trūkstošs, pirms katras rakstīšanas vēlreiz
pārbaudot `(vote_date, vote_time)` pret DB.

Divi apzināti lēmumi, kurus var pārslēgt ar karodziņiem:

1. **Reģistrācijas balsojumi neģenerē claims** (`--registration-claims`, lai
   ieslēgtu). "Deputātu klātbūtnes reģistrācija" nav balsojums — "Reģistrējies"
   nav Par/Pret/Atturas. Vēsturiski tie tomēr ģenerēja claims: DB ir 316 tādu
   rindu un **30 376** no tām atvasinātu claim (~5.6% no visiem). Turpināt to
   nozīmētu pievienot vēl troksni; sk. BACKLOG.
2. **Kopsavilkumu pārmanto no tā paša dokumenta** (`--no-summary-reuse`, lai
   atslēgtu). Procedurāls balsojums par 1051/Lp14 dabū to pašu kopsavilkumu,
   kas jau ir šī dokumenta galvenajam balsojumam. Kopsavilkumus neizdomā —
   ja māsas ieraksta nav, summary paliek NULL un tas parādās atskaitē, lai
   @saeima-tracker to aizpildītu (Step 3.5). Procedurāli balsojumi bez
   dokumenta atsauces NULL drīkst palikt pēc aģenta prompta.

Lietošana:
    python scripts/ingest_saeima_missing_votes.py --parity data/parity_2025.json
    python scripts/ingest_saeima_missing_votes.py --parity data/parity_2025.json --dates 2025-04-10,2025-12-11 --apply
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

from scripts.p3_backfill_year_urllib import (  # noqa: E402
    _fetch,
    _parse_vote_page,
    _to_vote_result,
)
from src.preflight import ensure_embeddings_live  # noqa: E402
from src.saeima import (  # noqa: E402
    IndividualVote,
    VoteResult,
    generate_claims_from_votes,
    match_deputies_to_politicians,
    store_vote,
)

DB_PATH = str(REPO_ROOT / "data" / "atmina.db")
_DOC_NR_RE = re.compile(r"\((\d+/(?:Lp14|Lm14|P14))\)")
_REGISTRATION_RE = re.compile(r"klātbūtnes reģistrācij", re.IGNORECASE)


def _doc_nr(motif: str) -> str | None:
    m = _DOC_NR_RE.search(motif or "")
    return m.group(1) if m else None


def _sibling_summary(db: sqlite3.Connection, doc_nr: str | None) -> str | None:
    """Kopsavilkums no cita balsojuma par to pašu dokumentu (garākais uzvar)."""
    if not doc_nr:
        return None
    row = db.execute(
        """SELECT summary FROM saeima_votes
           WHERE document_nr = ? AND summary IS NOT NULL AND TRIM(summary) <> ''
           ORDER BY LENGTH(summary) DESC LIMIT 1""",
        (doc_nr,),
    ).fetchone()
    return row[0] if row else None


def repair_claims(dates: set[str] | None, apply: bool) -> int:
    """Atjauno claims balsojumiem, kas ir DB, bet kuriem claim ģenerēšana krita.

    `store_vote()` commit-o pirms `generate_claims_from_votes()`, tāpēc kļūda
    claim pusē (piem. nepareizs interpretators bez embedding steka) atstāj
    balsojumu ar individuālajām balsīm, bet bez claims. Šis režīms to salabo,
    nepārlādējot neko no titania.
    """
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    q = """SELECT v.* FROM saeima_votes v
           WHERE v.url NOT IN (SELECT DISTINCT source_url FROM claims WHERE source_url IS NOT NULL)
             AND v.motif NOT LIKE '%klātbūtnes reģistrācij%'
             AND EXISTS (SELECT 1 FROM saeima_individual_votes iv WHERE iv.vote_id = v.id)"""
    params: list = []
    if dates:
        q += " AND v.vote_date IN ({})".format(",".join("?" * len(dates)))
        params = sorted(dates)
    rows = db.execute(q + " ORDER BY v.vote_date, v.vote_time", params).fetchall()
    if apply:
        ensure_embeddings_live()
    print(f"=== CLAIM REMONTS — {len(rows)} balsojumi bez claims ===\n")

    total = 0
    for r in rows:
        ivs = [
            IndividualVote(deputy_name=x["deputy_name"], faction=x["faction"],
                           vote=x["vote"], politician_id=x["politician_id"])
            for x in db.execute(
                "SELECT * FROM saeima_individual_votes WHERE vote_id = ?", (r["id"],))
        ]
        print(f'  #{r["id"]} {r["vote_date"]} {r["vote_time"]} '
              f'({sum(1 for i in ivs if i.politician_id)}/{len(ivs)} sekoti) '
              f'{r["motif"][:60]}')
        if not apply:
            continue
        vote = VoteResult(
            motif=r["motif"], date=r["vote_date"], time=r["vote_time"],
            total_par=r["total_par"], total_pret=r["total_pret"],
            total_atturas=r["total_atturas"], total_nebalso=r["total_nebalso"],
            result=r["result"], url=r["url"], individual_votes=ivs,
        )
        try:
            total += len(generate_claims_from_votes(vote, r["id"], DB_PATH))
        except Exception as e:  # noqa: BLE001
            print(f"    FAIL: {e}")
    db.close()
    print(f"\n  izveidoti claims: {total}")
    if not apply:
        print("  (sausā palaide — pievieno --apply)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--parity", help="audit_saeima_agenda_parity.py JSON")
    ap.add_argument("--repair-claims", action="store_true",
                    help="neko nelādē; atjauno claims balsojumiem, kas jau ir DB")
    ap.add_argument("--dates", default=None, help="komatatdalīti ISO datumi (apakškopa)")
    ap.add_argument("--apply", action="store_true", help="bez tā — sausā palaide")
    ap.add_argument("--registration-claims", action="store_true")
    ap.add_argument("--no-summary-reuse", action="store_true")
    ap.add_argument("--allow-partial-parity", action="store_true",
                    help="turpināt, arī ja parity JSON satur neauditētas sēdes")
    ap.add_argument("--rollback-out", default=None,
                    help="kur rakstīt pāra rollback SQL (obligāts ar --apply)")
    args = ap.parse_args()

    if args.repair_claims:
        want = {d.strip() for d in args.dates.split(",")} if args.dates else None
        return repair_claims(want, args.apply)

    if not args.parity:
        print("ATTEIKUMS: vajadzīgs --parity (vai --repair-claims).")
        return 2

    if args.apply and not args.rollback_out:
        print("ATTEIKUMS: --apply prasa --rollback-out "
              "(CLAUDE.md — katra datu mutācija nāk ar pāra rollback).")
        return 2

    results = json.loads((REPO_ROOT / args.parity).read_text(encoding="utf-8"))

    # Parity JSON var būt APCIRPTS darba uzdevums (2026-08-09). Sēde, kuras
    # agendu neizdevās nolasīt, JSON-ā ir ar `missing: []` — tāpēc bez šīs
    # pārbaudes tā izskatās kā sēde bez robiem, un ielāde par to klusē. Kļūda
    # tā pārceļas no diagnostikas uz RAKSTOŠO ceļu: mēs ielādējam „visu, kas
    # trūkst" no faila, kurā daļa sēžu vispār nav auditēta.
    unaudited = [r for r in results if r.get("error")]
    if unaudited and not args.allow_partial_parity:
        print(f"ATTEIKUMS: parity JSON satur {len(unaudited)} sēdes, kuras nav "
              f"nolasītas — tas ir apcirpts darba uzdevums, ne tukšs robs:")
        for r in unaudited:
            print(f'  {r.get("date")} ({r.get("session_type")}): {r.get("error")}')
        print("\nAtkārto auditu tiem datumiem (--dates), vai apzināti turpini "
              "ar --allow-partial-parity.")
        return 2
    if unaudited:
        print(f"BRĪDINĀJUMS: turpinu ar apcirptu parity JSON — {len(unaudited)} "
              f"sēdes nav auditētas: "
              + ", ".join(str(r.get("date")) for r in unaudited) + "\n")

    missing = [m for r in results for m in r["missing"]]
    if args.dates:
        want = {d.strip() for d in args.dates.split(",")}
        missing = [m for m in missing if m["vote_date"] in want]
    missing.sort(key=lambda m: (m["vote_date"], m["vote_time"]))

    if args.apply:
        # Pirms pirmās rakstīšanas, ne pie pirmā claim: store_vote() commit-o
        # atsevišķi no claim ģenerēšanas, tāpēc vēlāka embedding kļūme atstāj
        # balsojumu rindas bez claims (sk. ensure_embeddings_live docstring).
        ensure_embeddings_live()

    mode = "IELĀDE" if args.apply else "SAUSĀ PALAIDE"
    print(f"=== {mode} — {len(missing)} trūkstoši balsojumi ===\n")

    db = sqlite3.connect(DB_PATH)
    stats = {
        "stored": 0, "skipped_present": 0, "failed": 0,
        "claims": 0, "reg_votes": 0, "summary_reused": 0, "summary_null": 0,
        "indiv_total": 0, "indiv_matched": 0,
    }
    summary_null_rows: list[str] = []
    inserted_vote_ids: list[int] = []
    inserted_claim_ids: list[int] = []

    for m in missing:
        key = (m["vote_date"], m["vote_time"])
        exists = db.execute(
            "SELECT 1 FROM saeima_votes WHERE vote_date = ? AND vote_time = ?", key
        ).fetchone()
        if exists:
            stats["skipped_present"] += 1
            continue

        is_reg = bool(_REGISTRATION_RE.search(m["motif"] or ""))
        doc_nr = _doc_nr(m["motif"])
        summary = None if args.no_summary_reuse else _sibling_summary(db, doc_nr)
        if summary:
            stats["summary_reused"] += 1
        elif doc_nr:
            stats["summary_null"] += 1
            summary_null_rows.append(f'{m["vote_date"]} {m["vote_time"]} {doc_nr} {m["motif"][:70]}')
        if is_reg:
            stats["reg_votes"] += 1

        if not args.apply:
            stats["stored"] += 1
            continue

        try:
            parsed = _parse_vote_page(_fetch(m["url"]))
            vote = _to_vote_result(parsed, m["url"])
            if not vote.motif or not vote.individual_votes:
                stats["failed"] += 1
                print(f'  FAIL tukši dati {m["vote_date"]} {m["vote_time"]}')
                continue
            match_deputies_to_politicians(vote.individual_votes, DB_PATH)
            vote_db_id = store_vote(
                vote, agenda_item_id=None, db_path=DB_PATH,
                summary=summary, document_url=None, document_nr=doc_nr,
            )
            # ID tiek fiksēts UZREIZ pēc store_vote, PIRMS claim ģenerēšanas:
            # store_vote() jau ir izdarījis commit, tāpēc vēlāks izņēmums claim
            # pusē atstāj balsojuma rindu DB. Ja ID pierakstītu pēc tam, rollback
            # segtu tikai pilnībā izdevušos ielādes un klusi noklusētu pārējās
            # (2026-07-25: tieši tā palika 20 rindas ārpus rollback faila).
            inserted_vote_ids.append(vote_db_id)
            claim_ids = []
            if not is_reg or args.registration_claims:
                claim_ids = generate_claims_from_votes(vote, vote_db_id, DB_PATH)
            inserted_claim_ids.extend(claim_ids)
            stats["stored"] += 1
            stats["claims"] += len(claim_ids)
            stats["indiv_total"] += len(vote.individual_votes)
            stats["indiv_matched"] += sum(1 for iv in vote.individual_votes if iv.politician_id)
        except Exception as e:  # noqa: BLE001
            stats["failed"] += 1
            print(f'  FAIL {m["vote_date"]} {m["vote_time"]}: {e}')

    db.close()

    if args.apply and inserted_vote_ids:
        vids = ",".join(str(i) for i in inserted_vote_ids)
        cids = ",".join(str(i) for i in inserted_claim_ids) or "-1"
        path = REPO_ROOT / args.rollback_out
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "-- Rollback: scripts/ingest_saeima_missing_votes.py\n"
            f"-- Atgriež: {len(inserted_vote_ids)} saeima_votes rindas + to individuālās\n"
            f"-- balsis + {len(inserted_claim_ids)} saeima_vote claims, kas ielādēti no\n"
            f"-- {args.parity} (trūkstošie balsojumi pēc agenda↔DB parity audita).\n"
            "-- Piemērots: aizpildi datumu pie palaišanas.\n"
            "BEGIN TRANSACTION;\n"
            f"DELETE FROM claims WHERE id IN ({cids});\n"
            f"DELETE FROM saeima_individual_votes WHERE vote_id IN ({vids});\n"
            f"DELETE FROM saeima_votes WHERE id IN ({vids});\n"
            "COMMIT;\n",
            encoding="utf-8",
        )
        print(f"\n  rollback: {path}")

    print("\n--- kopsavilkums ---")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    if stats["indiv_total"]:
        rate = 100.0 * stats["indiv_matched"] / stats["indiv_total"]
        print(f"  deputātu atbilstība: {rate:.2f}%")
    if summary_null_rows:
        print(f"\n  {len(summary_null_rows)} balsojumi ar dokumenta atsauci, bet BEZ kopsavilkuma")
        print("  (@saeima-tracker Step 3.5 darbs, ne šī skripta):")
        for row in summary_null_rows[:20]:
            print(f"    {row}")
        if len(summary_null_rows) > 20:
            print(f"    … vēl {len(summary_null_rows) - 20}")
    if not args.apply:
        print("\n  (sausā palaide — nekas nav ierakstīts; pievieno --apply)")

    # Kļūme JĀPADOD tālāk kā izejas kods. 2026-08-01 pirmajā 2026. gada partijā
    # viens balsojums izkrita ar tīkla noildzi, `failed: 1` bija kopsavilkumā —
    # un skripts izgāja ar 0. Bulk ielāde, kas ziņo par panākumu, kamēr daļa
    # ievades pazuda, ir tieši tā klase, ko CLAUDE.md sauc par defektu #1.
    if stats["failed"]:
        print(f"\n  NEIELĀDĒTI {stats['failed']} balsojumi — sk. FAIL rindas augšā.")
        print("  Palaid to pašu komandu vēlreiz: pirms katras rakstīšanas notiek")
        print("  (vote_date, vote_time) pārbaude, tāpēc atkārtojums ir drošs un")
        print("  jau ielādētie tiks izlaisti (skipped_present).")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
