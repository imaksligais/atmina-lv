#!/usr/bin/env python
"""Veco neizskatīto pāru iztukšošanas plāns — rutīnas soļa «backlog» komanda.

Lasa `src.routine.stale_extraction_pairs(db, <datums>)` (pāru līmenis:
`role='subject'`, `extracted_at IS NULL`, bez claim, rindas tvērums, vecāki par
dienas rindas `--days 2` tvērumu) un sadala tos @claim-extractor vienībās pa
≤12 dokiem (`.claude/agents/claim-extractor.md` § 5):

* politiķis ar >12 dokiem → `lane`: viena vienība, secīgi gabali pa 12;
* pārējie → `pack`: vairāku politiķu doki vienā gabalā līdz 12 kopā.

Plāns ir `scripts/sweep_unit.py` saderīgs (`--plan <ceļš>`): vienību gabalus
izdrukā ar `scripts/sweep_unit.py <atslēga> <vienība> <gabals> --plan <ceļš>`.
Aģentiem — tikai Opus @claim-extractor — dod brīfu
`wiki/operations/stale-sweep-brief.md` un gabala sarakstu. Runbook:
`wiki/operations/operacijas.md` § Veci neizskatīti pāri.

Tikai lasa DB; raksta tikai plāna JSON.

Lietošana:
    .venv/Scripts/python.exe scripts/plan_stale_sweep.py
    .venv/Scripts/python.exe scripts/plan_stale_sweep.py --date 2026-10-05 --include-vestnesis
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import OrderedDict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from src.db import get_db, today_lv  # noqa: E402
from src.routine import stale_extraction_pairs  # noqa: E402

CHUNK_MAX = 12  # claim-extractor § 5: ≤12 doku vienā izsaukumā


def build_units(pairs: list[dict], reviewed: set[int]) -> list[dict]:
    """Sagrupē pārus pa pid un sadala `lane`/`pack` vienībās (≤12 doku gabali)."""
    by_pid: OrderedDict[int, dict] = OrderedDict()
    for p in pairs:
        entry = by_pid.setdefault(p["pid"], {"name": p["name"], "docs": []})
        if p["doc_id"] not in entry["docs"]:
            entry["docs"].append(p["doc_id"])

    def pol(pid: int) -> dict:
        docs = by_pid[pid]["docs"]
        return {
            "pid": pid,
            "name": by_pid[pid]["name"],
            "already_reviewed": [d for d in docs if d in reviewed],
        }

    units: list[dict] = []
    small: list[int] = []
    for pid, entry in by_pid.items():
        docs = entry["docs"]
        if len(docs) > CHUNK_MAX:
            chunks = [
                [{"pid": pid, "docs": docs[i:i + CHUNK_MAX]}]
                for i in range(0, len(docs), CHUNK_MAX)
            ]
            units.append({"type": "lane", "pols": [pol(pid)], "chunks": chunks})
        else:
            small.append(pid)

    # First-fit decreasing: lielākie vispirms, katrs pack ≤12 doku.
    bins: list[list[int]] = []
    sizes: list[int] = []
    for pid in sorted(small, key=lambda x: -len(by_pid[x]["docs"])):
        n = len(by_pid[pid]["docs"])
        for i, used in enumerate(sizes):
            if used + n <= CHUNK_MAX:
                bins[i].append(pid)
                sizes[i] += n
                break
        else:
            bins.append([pid])
            sizes.append(n)
    for b in bins:
        units.append({
            "type": "pack",
            "pols": [pol(pid) for pid in b],
            "chunks": [[{"pid": pid, "docs": by_pid[pid]["docs"]} for pid in b]],
        })
    return units


def main(argv: list[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    ap = argparse.ArgumentParser(description="Veco neizskatīto pāru iztukšošanas plāns.")
    ap.add_argument("--date", default=None, help="rutīnas diena YYYY-MM-DD (noklusējums šodiena)")
    ap.add_argument("--include-vestnesis", action="store_true",
                    help="pievienot arī Vēstneša pārus (atslēga 'vestnesis')")
    ap.add_argument("--out", default=None,
                    help="plāna ceļš (noklusējums docs/audits/<datums>-stale-sweep/plan.json)")
    args = ap.parse_args(argv)

    day = args.date or today_lv().isoformat()
    out = Path(args.out) if args.out else REPO / "docs" / "audits" / f"{day}-stale-sweep" / "plan.json"

    db = get_db()
    try:
        stale = stale_extraction_pairs(db, day)
        keys = ["main"] + (["vestnesis"] if args.include_vestnesis else [])
        all_docs = sorted({p["doc_id"] for k in keys for p in stale[k]})
        reviewed: set[int] = set()
        for i in range(0, len(all_docs), 500):
            part = all_docs[i:i + 500]
            reviewed |= {
                r[0] for r in db.execute(
                    f"SELECT id FROM documents WHERE reviewed_at IS NOT NULL "
                    f"AND id IN ({','.join('?' * len(part))})",
                    part,
                )
            }
    finally:
        db.close()

    plan = {k: build_units(stale[k], reviewed) for k in keys}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"Robeža: scraped_at < {stale['cutoff']}")
    for k in keys:
        units = plan[k]
        n_pairs = len(stale[k])
        n_chunks = sum(len(u["chunks"]) for u in units)
        print(
            f"{k}: pāri {n_pairs}, vienības {len(units)} (paralēli), "
            f"gabali {n_chunks} (= @claim-extractor izsaukumi, Opus)"
        )
    if not args.include_vestnesis:
        print(f"vestnesis (nav plānā): pāri {len(stale['vestnesis'])}")
    print(f"Plāns: {out}")
    print("Gabals: .venv/Scripts/python.exe scripts/sweep_unit.py <atslēga> <vienība> <gabals> "
          f"--plan {out}")
    print("Brīfs: wiki/operations/stale-sweep-brief.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
