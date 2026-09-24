"""Zelta tests Jev pretrunu priekšfiltram — denominatori pirmie, DB tikai lasa.

Jautājums, uz ko atbild: ja `@contradiction-hunter` lasītu tikai pārus, kam
Jev dod p ≥ θ, vai tas pazaudētu kādu no jau ZINĀMAJĀM pretrunām
(`contradictions`, position↔position), un cik kandidātu tas noņemtu?

Divi atsevišķi denominatori — nekad nesapludināt:
  1. zelts kandidātos / zelts kopā   — kNN kandidātu ģenerēšanas griesti (k)
  2. zelts virs θ / zelts kandidātos — paša Jev pilnīgums
Zelts ārpus kandidātiem Jev nekad neredz; tas ir k jautājums, ne modeļa.
Pozīcijas bez `stated_at` ir trešais, atsevišķs izlaidums — tās nekad
neiet kandidātos, jo bez datuma nav zināms virziens (sk.
`src/contradiction_candidates.py` docstring); skriptā tās drukā kā
"pozīcijas bez datuma izlaistas N".

Usage:
  .venv/Scripts/python.exe scripts/jev_contradiction_eval.py --dry-run          # 0 API: tikai (1)
  .venv/Scripts/python.exe scripts/jev_contradiction_eval.py --k 40             # dzīvs skrējiens
  .venv/Scripts/python.exe scripts/jev_contradiction_eval.py --politicians 2,12 --k 100
  .venv/Scripts/python.exe scripts/jev_contradiction_eval.py --sample 1000 --seed 20260918  # reproducējams pilots
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sqlite3
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.contradiction_candidates import (  # noqa: E402
    DEFAULT_K, DEFAULT_THRESHOLD, OPPOSITE_CRITERIA, OPPOSITE_INSTRUCTIONS, PAIR_CONTEXT, candidate_pairs,
    pair_states, undated_positions,
)
from src.db import get_db  # noqa: E402
from src.jev_filter import JevCache, JevStats, judge_rows  # noqa: E402

DEFAULT_THRESHOLDS = [0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]

_GOLD_SQL = """
    SELECT c.id, c.opponent_id, c.claim_old_id, c.claim_new_id, c.confirmed, c.severity
      FROM contradictions c
      JOIN claims a ON a.id = c.claim_old_id
      JOIN claims b ON b.id = c.claim_new_id
     WHERE a.claim_type = 'position' AND b.claim_type = 'position'
     ORDER BY c.id
"""


def gold_pairs(db: sqlite3.Connection) -> list[dict]:
    return [{"id": int(r[0]), "opponent_id": int(r[1]), "old": int(r[2]), "new": int(r[3]),
             "confirmed": int(r[4] or 0), "severity": r[5]} for r in db.execute(_GOLD_SQL).fetchall()]


def select_sample(all_pairs: list[tuple[int, int]], gold: list[dict], n: int, seed: int) -> list[tuple[int, int]]:
    """Reproducējams pilots: visi zelta pāri, kas ir kandidātos, + N nejauši no PĀRĒJIEM.

    `all_pairs` secība ir stabila (`candidate_pairs()` sakārto pēc datuma), tāpēc tas pats
    `seed` vienmēr izvēlas tos pašus nejaušos pārus. Zelts un nejaušā izlase nepārklājas —
    zelts vienmēr iekšā, lai pilots joprojām atbild uz pilnīguma jautājumu."""
    gold_keys = {frozenset((g["old"], g["new"])) for g in gold}
    gold_in_cand = [p for p in all_pairs if frozenset(p) in gold_keys]
    rest = [p for p in all_pairs if frozenset(p) not in gold_keys]
    chosen = random.Random(seed).sample(rest, min(n, len(rest)))
    return gold_in_cand + chosen


def question_tag() -> str:
    """8 hex zīmes no jautājuma (instrukcijas+kritēriji) SHA-256 — maina jautājumu, maina tagu,
    lai divi eval-skrējieni ar DAŽĀDIEM jautājumiem nesaraksta viens otru output failā."""
    canon = json.dumps({"instructions": OPPOSITE_INSTRUCTIONS, "criteria": OPPOSITE_CRITERIA},
                       ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()[:8]


def summarize(gold: list[dict], probs: dict[frozenset[int], float | None],
              thresholds: list[float]) -> dict:
    detail = []
    for g in gold:
        key = frozenset((g["old"], g["new"]))
        detail.append({"id": g["id"], "confirmed": g["confirmed"], "severity": g["severity"],
                       "in_candidates": key in probs, "p": probs.get(key)})
    in_cand = [d for d in detail if d["in_candidates"]]
    judged = sum(1 for p in probs.values() if p is not None)
    unavailable = sum(1 for p in probs.values() if p is None)
    rows = []
    for t in thresholds:
        kept = sum(1 for p in probs.values() if p is not None and p >= t)
        rows.append({
            "threshold": t,
            "gold_kept": sum(1 for d in in_cand if d["p"] is not None and d["p"] >= t),
            "gold_confirmed_kept": sum(1 for d in in_cand if d["confirmed"] and d["p"] is not None and d["p"] >= t),
            "candidates_kept": kept,
            "kept_pct": (100.0 * kept / judged) if judged else 0.0,
        })
    return {"gold_total": len(gold), "in_candidates": len(in_cand),
            "gold_confirmed_in_candidates": sum(1 for d in in_cand if d["confirmed"]),
            "judged": judged, "unavailable": unavailable, "rows": rows, "gold_detail": detail}


def render(s: dict, stats: JevStats, sample: dict | None = None) -> str:
    out = [f"Denominators: zelts {s['gold_total']}, kandidātos {s['in_candidates']} "
           f"(apstiprināti {s['gold_confirmed_in_candidates']}), vērtēti pāri {s['judged']}, "
           f"nepieejami {s['unavailable']}"]
    if sample is not None:
        out.append(f"Izlase: {sample['n']} nejauši kandidāti (seed {sample['seed']}) — "
                   f"«paliek %» zemāk ir daļa no IZLASES, ne visiem kandidātiem")
    out += [stats.summary(),
           "",
           f"{'θ':>5} | {'zelts ≥θ':>10} | {'apstipr. ≥θ':>12} | {'kandidāti ≥θ':>13} | {'paliek %':>8}"]
    for r in s["rows"]:
        out.append(f"{r['threshold']:>5} | {r['gold_kept']:>4}/{s['in_candidates']:<5} | "
                   f"{r['gold_confirmed_kept']:>5}/{s['gold_confirmed_in_candidates']:<6} | "
                   f"{r['candidates_kept']:>13} | {r['kept_pct']:>7.1f}")
    out.append("")
    out.append("Zelta pāri (p = Jev varbūtība; None = ārpus kandidātiem vai nepieejams):")
    for d in s["gold_detail"]:
        p = "None" if d["p"] is None else f"{d['p']:.2f}"
        out.append(f"  #{d['id']:<3} {str(d['severity'] or ''):<20} confirmed={d['confirmed']} p={p}"
                   + ("" if d["in_candidates"] else "  (ārpus top-k kandidātiem)"))
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--k", type=int, default=DEFAULT_K)
    ap.add_argument("--politicians", default="", help="komatu saraksts ar opponent_id; tukšs = visi zelta")
    ap.add_argument("--dry-run", action="store_true", help="tikai kandidātu pilnīgums, 0 API")
    ap.add_argument("--max-pairs", type=int, default=80_000, help="izdevumu vārts: vairāk nesūta")
    ap.add_argument("--thresholds", default=",".join(map(str, DEFAULT_THRESHOLDS)))
    ap.add_argument("--sample", type=int, default=None,
                    help="reproducējams pilots: zelts kandidātos + N nejauši no pārējiem, vērtē tikai tos")
    ap.add_argument("--seed", type=int, default=20260918, help="--sample nejaušā izlase (noklusējums 20260918)")
    ap.add_argument("--out", default=None,
                    help="noklusējums: data/jev_eval_<datums>_<jautājuma-hash>[_<label>].json")
    ap.add_argument("--label", default="", help="papildu sufikss izvades faila nosaukumā (aiz jautājuma haša)")
    args = ap.parse_args()
    thresholds = [float(t) for t in args.thresholds.split(",") if t]

    db = get_db()
    gold = gold_pairs(db)
    pids = sorted({g["opponent_id"] for g in gold})
    if args.politicians:
        chosen = {int(x) for x in args.politicians.split(",") if x}
        pids = [p for p in pids if p in chosen]
        gold = [g for g in gold if g["opponent_id"] in chosen]

    all_pairs: list[tuple[int, int]] = []
    per_pid: dict[int, int] = {}
    for pid in pids:
        pairs = candidate_pairs(pid, k=args.k)
        per_pid[pid] = len(pairs)
        all_pairs.extend(pairs)
    cand = {frozenset(p) for p in all_pairs}
    in_cand = sum(1 for g in gold if frozenset((g["old"], g["new"])) in cand)
    undated = sum(undated_positions(db, pid) for pid in pids)
    print(f"Politiķi {len(pids)}, k={args.k}, kandidātu pāri {len(all_pairs)} "
          f"({', '.join(f'{p}:{n}' for p, n in per_pid.items())}); zelts kandidātos {in_cand}/{len(gold)}; "
          f"pozīcijas bez datuma izlaistas {undated}")

    judged_pairs = all_pairs
    sample_info: dict | None = None
    if args.sample is not None:
        judged_pairs = select_sample(all_pairs, gold, args.sample, args.seed)
        sample_info = {"n": args.sample, "seed": args.seed}
        print(f"Izlase: zelts kandidātos {in_cand} + {args.sample} nejauši (seed {args.seed})")

    if args.dry_run:
        if len(judged_pairs) > args.max_pairs:
            print(f"Piezīme: dzīvs skrējiens ar šiem parametriem apstātos — {len(judged_pairs)} pāri > --max-pairs {args.max_pairs}")
        db.close()
        return 0
    if len(judged_pairs) > args.max_pairs:
        print(f"STOP: {len(judged_pairs)} pāri > --max-pairs {args.max_pairs}; sašaurini --politicians, --k vai --sample")
        db.close()
        return 2

    states = pair_states(db, judged_pairs)
    db.close()
    stats = JevStats()
    probs_list = judge_rows(states, OPPOSITE_INSTRUCTIONS, OPPOSITE_CRITERIA,
                            context=PAIR_CONTEXT, cache=JevCache(), stats=stats)
    probs = {frozenset(p): pr for p, pr in zip(judged_pairs, probs_list, strict=True)}
    s = summarize(gold, probs, thresholds)
    print(render(s, stats, sample_info))
    if sample_info:
        # «paliek %» tabulā ir no visas izlases (zelts + nejaušie); šeit — tikai nejaušie,
        # jo tas ir skaitlis, ko salīdzina ar zelta pilnīgumu (CHANGELOG 2026-09-18 (2)).
        gold_keys = {frozenset((g["old"], g["new"])) for g in gold}
        rnd = [pr for k, pr in probs.items() if k not in gold_keys and pr is not None]
        print("Nejaušo vien (bez zelta): " + "; ".join(
            f"θ={t}: {sum(1 for pr in rnd if pr >= t)}/{len(rnd)} = {100 * sum(1 for pr in rnd if pr >= t) / len(rnd):.1f} %"
            for t in thresholds) if rnd else "Nejaušo vien: nav vērtētu")
    out_path = args.out or (f"data/jev_eval_{date.today().isoformat()}_{question_tag()}"
                            f"{('_' + args.label) if args.label else ''}.json")
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(json.dumps({"k": args.k, "politicians": pids, "per_pid": per_pid,
                                          "undated_excluded": undated,
                                          "question": {"instructions": OPPOSITE_INSTRUCTIONS,
                                                      "criteria": OPPOSITE_CRITERIA, "context": PAIR_CONTEXT},
                                          "models": sorted(stats.models),
                                          "default_threshold": DEFAULT_THRESHOLD,
                                          "sample": sample_info,
                                          "summary": s, "stats": {**stats.__dict__, "models": sorted(stats.models)},
                                          "pairs": [[a, b, probs[frozenset((a, b))]] for a, b in judged_pairs]},
                                         ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nRezultāts: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
