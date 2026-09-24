"""Jev īsais saraksts vienam politiķim — ko `@contradiction-hunter` lasa PIRMO.

Kandidātu pāri (top-k kaimiņi no claim_vectors) → Jev «vai new (vēlākais izteikums
vai rīcība) ir nesavienojams ar old» (v2, sk. `OPPOSITE_INSTRUCTIONS`) → pāri ar p ≥ θ dilstoši. Tas ir LASĪŠANAS SECĪBA
ar izmērītu pilnīgumu (zelta tests, CHANGELOG 2026-09-18 (2): 16/18
apstiprināto pie θ=0,3, 6,7 % kandidātu paliek; #17 un #36 zem sliekšņa),
ne verdikts: katru pāri joprojām vērtē hunter → @devils-advocate →
operators, `confirmed=0` paliek. Balsojumu pusi (retorika-pret-balsojumu)
šis skripts NESKAR — T9.

Usage:
  .venv/Scripts/python.exe scripts/jev_contradiction_shortlist.py 10 --threshold 0.7
  .venv/Scripts/python.exe scripts/jev_contradiction_shortlist.py "Kulbergs" --k 100 --all
  .venv/Scripts/python.exe scripts/jev_contradiction_shortlist.py 72 --dry-run          # 0 API: tikai denominators
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.contradiction_candidates import (  # noqa: E402
    DEFAULT_K, DEFAULT_THRESHOLD, OPPOSITE_CRITERIA, OPPOSITE_INSTRUCTIONS, PAIR_CONTEXT, candidate_pairs,
    pair_states, undated_positions,
)
from src.db import get_db  # noqa: E402
from src.jev_filter import JevCache, JevStats, judge_rows  # noqa: E402


def format_shortlist(name: str, n_claims: int, pairs: list[dict], threshold: float,
                     stats: JevStats, show_all: bool = False, undated: int = 0) -> str:
    ranked = sorted((p for p in pairs if p["p"] is not None), key=lambda p: -p["p"])
    above = [p for p in ranked if p["p"] >= threshold]
    out = [f"# {name} — Jev īsais saraksts",
           f"Denominators: pozīcijas {n_claims}, bez datuma izlaistas {undated}, kandidātu pāri {len(pairs)}, "
           f"virs θ={threshold}: {len(above)}, nepieejami {sum(1 for p in pairs if p['p'] is None)}",
           stats.summary(), "",
           "| p | pāris | datumi | tēmas | vecā nostāja | jaunā nostāja |",
           "|---|---|---|---|---|---|"]
    for p in (ranked if show_all else above):
        out.append(f"| {p['p']:.2f} | #{p['old_id']} → #{p['new_id']} | {p['old_date']} → {p['new_date']} | "
                   f"{p['old_topic']} → {p['new_topic']} | {p['old_stance']} | {p['new_stance']} |")
    return "\n".join(out)


def _resolve(db, arg: str) -> tuple[int, str]:
    if arg.isdigit():
        row = db.execute("SELECT id, name FROM tracked_politicians WHERE id = ?", (int(arg),)).fetchone()
    else:
        rows = db.execute("SELECT id, name FROM tracked_politicians WHERE name LIKE ? AND "
                          "relationship_type IS NOT 'inactive'", (f"%{arg}%",)).fetchall()
        if len(rows) != 1:
            raise SystemExit(f"'{arg}' atbilst {len(rows)} politiķiem: {[r[1] for r in rows]}")
        row = rows[0]
    if row is None:
        raise SystemExit(f"politiķis {arg!r} nav atrasts")
    return int(row[0]), str(row[1])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("politician")
    ap.add_argument("--k", type=int, default=DEFAULT_K)
    ap.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    ap.add_argument("--all", action="store_true", help="drukā arī pārus zem θ (dilstoši)")
    ap.add_argument("--max-pairs", type=int, default=80_000, help="izdevumu vārts: vairāk nesūta")
    ap.add_argument("--dry-run", action="store_true", help="tikai denominators, 0 API")
    args = ap.parse_args()

    db = get_db()
    pid, name = _resolve(db, args.politician)
    pairs = candidate_pairs(pid, k=args.k)
    n_claims = db.execute("SELECT COUNT(*) FROM claims WHERE opponent_id = ? AND claim_type = 'position' "
                          "AND (speaker_id IS NULL OR speaker_id = opponent_id)", (pid,)).fetchone()[0]
    undated = undated_positions(db, pid)

    if args.dry_run:
        print(f"Denominators: pozīcijas {n_claims}, bez datuma izlaistas {undated}, kandidātu pāri {len(pairs)}, "
              f"virs θ={args.threshold}: —, nepieejami —")
        if len(pairs) > args.max_pairs:
            print(f"Piezīme: dzīvs skrējiens ar šiem parametriem apstātos — {len(pairs)} pāri > --max-pairs {args.max_pairs}")
        db.close()
        return 0
    if len(pairs) > args.max_pairs:
        print(f"STOP: {len(pairs)} pāri > --max-pairs {args.max_pairs}; sašaurini --k")
        db.close()
        return 2

    states = pair_states(db, pairs)
    db.close()
    stats = JevStats()
    probs = judge_rows(states, OPPOSITE_INSTRUCTIONS, OPPOSITE_CRITERIA,
                       context=PAIR_CONTEXT, cache=JevCache(), stats=stats)
    rows = [{"old_id": a, "new_id": b, "p": p,
             "old_date": s["old"]["date"], "new_date": s["new"]["date"],
             "old_topic": s["old"]["topic"], "new_topic": s["new"]["topic"],
             "old_stance": s["old"]["stance"], "new_stance": s["new"]["stance"]}
            for (a, b), s, p in zip(pairs, states, probs, strict=True)]
    print(format_shortlist(name, n_claims, rows, args.threshold, stats, show_all=args.all, undated=undated))
    return 0


if __name__ == "__main__":
    sys.exit(main())
