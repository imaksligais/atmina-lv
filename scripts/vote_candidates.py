"""Balsojumu īsais saraksts — ko `@contradiction-hunter` lasa PIRMO retorikai pret balsojumu.

Katrai deputāta pozīcijai izdrukā tuvākos likumprojektus, par kuriem viņš ir balsojis,
ar paša balsīm visā ķēdē. Tā ir LASĪŠANAS SECĪBA ar izmērītu pilnīgumu (10 no 13
publicēto balsojumu pretrunu ir top-10, 12 no 13 top-40 —
`docs/audits/2026-11-13-pretrunu-faktu-parbaude/eval_vote_candidates.py`), ne verdikts.
Tukšs saraksts neko nepierāda; strukturālā pārbaude (T9) paliek obligāta. Tikai lasa DB.

Usage:
  .venv/Scripts/python.exe scripts/vote_candidates.py 105                    # šīs rutīnas dienas pozīcijas
  .venv/Scripts/python.exe scripts/vote_candidates.py 105 --claims 527657 --top 20
  .venv/Scripts/python.exe scripts/vote_candidates.py 105 --day 2026-11-12
  .venv/Scripts/python.exe scripts/vote_candidates.py 105 --votes-day 2026-11-18   # sēdes diena: balsojumi pret visām pozīcijām
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.briefs import current_routine_day, routine_day_window  # noqa: E402
from src.db import get_db  # noqa: E402
from src.vote_candidates import DEFAULT_TOP, positions_for_votes, shortlist  # noqa: E402


def _day_positions(db, pid: int, day: str) -> list[int]:
    start, end = routine_day_window(day)
    return [r[0] for r in db.execute(
        """SELECT id FROM claims WHERE opponent_id = ? AND claim_type = 'position'
           AND (speaker_id IS NULL OR speaker_id = opponent_id) AND created_at >= ? AND created_at < ? ORDER BY id""",
        (pid, start, end),
    )]


def format_shortlist(name: str, result: dict) -> str:
    st = result["stats"]
    lines = [f"Balsojumu īsais saraksts: {name} — pozīcijas {st['positions_in']}, bez vektora izlaistas {st['no_vector']}, "
             f"likumprojekti ar paša nodotu balsi {st['bills_voted']}, rāda top {st['top']}"]
    if not st["bills_voted"]:
        lines.append("  Šim politiķim nav nodotu balsu — retorikai pret balsojumu nav ko salīdzināt.")
    for p in result["positions"]:
        lines.append(f"\nPOZĪCIJA {p['claim_id']} ({(p['stated_at'] or '')[:10]}, {p['topic']}): {p['stance']}")
        for i, b in enumerate(p["bills"], 1):
            own = Counter(v["vote"] for v in b["ballots"])
            dates = sorted({v["vote_date"] for v in b["ballots"]})
            span = dates[0] if len(dates) == 1 else f"{dates[0]}…{dates[-1]}"
            mixed = " JAUKTA ĶĒDE (T14)" if len(own) > 1 else ""
            lines.append(f"  {i}. {b['key']} [{b['score']}] {span}, {b['topic']} | paša balsis: "
                         + ", ".join(f"{k}×{n}" for k, n in own.items()) + mixed)
            lines.append(f"     {b['text'][:260]}")
            lines.append(f"     balsojumi: {', '.join(str(v['id']) for v in b['ballots'][:12])}"
                         + (" …" if len(b["ballots"]) > 12 else ""))
    return "\n".join(lines)


def format_votes_day(name: str, day: str, result: dict) -> str:
    st = result["stats"]
    lines = [f"Dienas balsojumi pret pozīcijām: {name}, {day} — likumprojekti ar paša saturisku balsi {st['bills_today']}, "
             f"pozīcijas ar vektoru un datumu {st['positions']}, rāda top {st['top']}"]
    for b in result["bills"]:
        own = Counter(v["vote"] for v in b["ballots"])
        mixed = " JAUKTA ĶĒDE (T14)" if len(own) > 1 else ""
        lines.append(f"\nLIKUMPROJEKTS {b['key']} ({b['topic']}) | paša balsis visā ķēdē: "
                     + ", ".join(f"{k}×{n}" for k, n in own.items()) + mixed)
        lines.append(f"   {b['text'][:260]}")
        for i, p in enumerate(b["positions"], 1):
            lines.append(f"  {i}. pozīcija {p['claim_id']} [{p['score']}] {(p['stated_at'] or '')[:10]}, {p['topic']}: {(p['stance'] or '')[:200]}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("politician", type=int, help="tracked_politicians.id")
    ap.add_argument("--claims", type=int, nargs="+", help="pozīciju id (noklusējums: rutīnas dienas pozīcijas)")
    ap.add_argument("--day", help="rutīnas diena YYYY-MM-DD (noklusējums: šodienas)")
    ap.add_argument("--votes-day", help="sēdes diena YYYY-MM-DD: tās dienas balsojumi pret visām deputāta pozīcijām")
    ap.add_argument("--top", type=int, default=DEFAULT_TOP)
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    db = get_db()
    try:
        row = db.execute("SELECT name FROM tracked_politicians WHERE id = ?", (args.politician,)).fetchone()
        if row is None:
            print(f"KĻŪDA: politiķa {args.politician} nav")
            return 1
        if args.votes_day:
            print(format_votes_day(row["name"], args.votes_day, positions_for_votes(db, args.politician, args.votes_day, top=args.top)))
            return 0
        ids = args.claims or _day_positions(db, args.politician, args.day or current_routine_day())
        print(format_shortlist(row["name"], shortlist(db, args.politician, ids, top=args.top)))
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
