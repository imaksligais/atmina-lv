"""Verdikts 15 (docs/verdikti-2026-11-03.md): balsojuma #206 (1360/Lp14, nodošana komisijām) summary.

Vecais teksts nenosauca likumprojekta saturu (Valsts kontroles revīzija Saeimas finansēm;
LSM 21.05.2026, saeima_bills.summary labots 2026-10-19), izlaida «7 pret» un vērtēja
(«neparasts opozīcijas iniciatīvas atbalsts»). Maina saeima_votes.summary un no tā
atvasinātās saeima_vote stances (prefikss + summary). bill_id/current_stage neskar (inv #12);
saeima_vote rindām vektoru nav (re-embed nevajag).
Bez karoga: tikai skaita. `--apply`: raksta. Rollback: data/rollback_vote_summary_1360lp14_2026-11-03.sql
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.db import get_db  # noqa: E402

VOTE_ID = 206
OLD = ("LPV frakcijas (Krištopans, Armaņeva, Šlesers, Liepiņa, Stobova) ierosinātie grozījumi "
       "Saeimas kārtības rullī nodoti komisijām (45 par, daļa koalīcijas pievienojusies, 31 atturēts) "
       "— neparasts opozīcijas iniciatīvas atbalsts.")
NEW = ("LPV frakcijas deputātu (Krištopans, Armaņeva, Šlesers, Liepiņa, Stobova) iesniegtie grozījumi "
       "Saeimas kārtības rullī, kas paredz Saeimas finanšu revīziju nodot Valsts kontrolei, "
       "nodoti komisijām (45 par, 7 pret, 31 atturas).")
EXPECTED_CLAIMS = 89


def main(apply: bool) -> None:
    db = get_db()
    url, summary = db.execute("SELECT url, summary FROM saeima_votes WHERE id=?", (VOTE_ID,)).fetchone()
    n = db.execute("SELECT count(*) FROM claims WHERE claim_type='saeima_vote' AND source_url=? "
                   "AND instr(stance, ?) > 0", (url, OLD)).fetchone()[0]
    print(f"summary sakrīt: {summary == OLD}; stances ar veco tekstu: {n}/{EXPECTED_CLAIMS}")
    if summary != OLD or n != EXPECTED_CLAIMS:
        sys.exit("STOP: stāvoklis neatbilst gaidītajam")
    if not apply:
        return
    with db:
        c = db.execute("UPDATE claims SET stance=replace(stance, ?, ?) WHERE claim_type='saeima_vote' "
                       "AND source_url=? AND instr(stance, ?) > 0", (OLD, NEW, url, OLD)).rowcount
        v = db.execute("UPDATE saeima_votes SET summary=? WHERE id=? AND summary=?", (NEW, VOTE_ID, OLD)).rowcount
    print(f"mainīts: stances {c}/{EXPECTED_CLAIMS}, summary {v}/1")
    if c != EXPECTED_CLAIMS or v != 1:
        sys.exit("STOP: skaits nesakrīt")


if __name__ == "__main__":
    main("--apply" in sys.argv)
