"""Vienreizēja migrācija: `saeima_vote` stance pirmā summary burta reģistrs.

Kāpēc: līdz 2026-10-08 `generate_claims_from_votes()` pazemināja kopsavilkuma
pirmo burtu visur, izņemot akronīmus — «Atbalsta: ministru kabineta
likumprojekts…» (wiki/CHANGELOG.md 2026-10-08 (6)). Ģenerators
salabots (`src.saeima.votes.stance_summary_case`); šis skripts pārrēķina tikai
VĒSTURISKO stance pirmā summary burta reģistru. `saeima_votes.summary` nemainās,
prefikss nemainās, viss pārējais stance teksts nemainās. Vektoru nav
(`saeima_vote` rindām tos neveido) — pārembedot nevajag.

Drošība:
- Plānā nonāk tikai claims, kuru stance PRECĪZI sakrīt ar veco ģeneratora
  izvadi `"<prefikss>: <vecais_reģistrs(summary)>"`. Rokas labotie, sentinel un
  «Balsoja PAR: <motif>» stance tiek izlaisti un saskaitīti.
- Dry run (noklusējums) uzraksta atgriešanas SQL ar plāna hash galvenē.
  `--apply` pārrēķina plānu, salīdzina hash ar atgriešanas faila galveni un
  atsakās, ja tie atšķiras (atgriešanas fails ir jāģenerē un jāiekomitē PIRMS
  piemērošanas, CLAUDE.md escalation 8).
- Atgriešanas SQL ir kompakts: maiņa ir viens burts zināmā pozīcijā, tāpēc
  rindas grupē pēc (pozīcija, burts) un katrai grupai ir viens UPDATE ar
  `id IN (...)`. SQLite `lower()` NETIEK lietots — tas ir tikai ASCII (Ā/Š/Ž).

Lietošana (`--db` ir obligāts — nav noklusējuma ražošanas DB):
    .venv/Scripts/python.exe scripts/fix_saeima_stance_propnoun_case.py --db data/atmina.db
    .venv/Scripts/python.exe scripts/fix_saeima_stance_propnoun_case.py --db data/atmina.db --apply
"""

from __future__ import annotations

import argparse
import hashlib
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.saeima.votes import stance_summary_case  # noqa: E402

DEFAULT_ROLLBACK = "data/rollback_saeima_stance_propnoun_case_2026-10-08.sql"
PREFIXES = ("Atbalsta", "Iebilst pret", "Atturējās balsojumā par", "Nebalsoja par")
SENTINEL = "Kopsavilkums nav pieejams"


def old_case(summary: str) -> str:
    """Ģeneratora loģika līdz 2026-10-08 (tikai akronīmu izņēmums)."""
    if summary[:2].isupper():
        return summary
    return summary[0].lower() + summary[1:]


def build_plan(db: sqlite3.Connection):
    """→ (plan, stats). plan = [(claim_id, k, old_char, new_char, old_stance, new_stance)],
    k = rakstzīmju skaits pirms summary pirmā burta stance tekstā."""
    stats = Counter()
    stats["saeima_vote_claims"] = db.execute(
        "SELECT COUNT(*) FROM claims WHERE claim_type = 'saeima_vote'").fetchone()[0]
    stats["claims_matched_to_vote_url"] = db.execute(
        "SELECT COUNT(*) FROM claims c WHERE c.claim_type = 'saeima_vote'"
        " AND EXISTS (SELECT 1 FROM saeima_votes v WHERE v.url = c.source_url)").fetchone()[0]
    plan = []
    votes = db.execute(
        "SELECT id, url, summary, motif FROM saeima_votes"
        " WHERE summary IS NOT NULL AND summary != ''").fetchall()
    for _vid, url, summary, motif in votes:
        if summary.startswith(SENTINEL) or summary == motif:
            continue
        old, new = old_case(summary), stance_summary_case(summary)
        if old == new:
            continue
        stats["votes_affected"] += 1
        for cid, stance in db.execute(
                "SELECT id, stance FROM claims WHERE claim_type = 'saeima_vote'"
                " AND source_url = ?", (url,)):
            hit = next((p for p in PREFIXES if stance == f"{p}: {old}"), None)
            if hit is None:
                done = any(stance == f"{p}: {new}" for p in PREFIXES)
                stats["claims_already_correct" if done else "claims_skipped_nonmatching"] += 1
                continue
            k = len(hit) + 2
            plan.append((cid, k, old[0], new[0], stance, f"{hit}: {new}"))
    stats["claims_planned"] = len(plan)
    return plan, stats


def plan_hash(plan) -> str:
    ids = ",".join(str(p[0]) for p in sorted(plan))
    return hashlib.sha256(ids.encode()).hexdigest()[:16]


def _q(ch: str) -> str:
    return "'" + ch.replace("'", "''") + "'"


def rollback_sql(plan, db_path: str, today: str) -> str:
    groups = defaultdict(list)
    for cid, k, old_ch, new_ch, _o, _n in plan:
        groups[(k, old_ch, new_ch)].append(cid)
    out = [
        "-- Forward: scripts/fix_saeima_stance_propnoun_case.py --apply —",
        "-- saeima_vote claims stance: summary pirmais burts mazais → lielais, ja",
        "-- summary sākas ar īpašvārdu (src.saeima.votes.stance_summary_case).",
        f"-- Ģenerēts dry run {today} no DB: {db_path}",
        "-- Apply date: nav piemērots (ieraksti datumu, kad piemēro).",
        f"-- plan-hash: {plan_hash(plan)} count: {len(plan)}",
        "-- Šis fails atjauno IEPRIEKŠĒJO burtu (tikai tajā pozīcijā, tikai tad, ja tur",
        "-- joprojām ir jaunais burts). Nelieto SQLite lower() — tas ir tikai ASCII.",
        "BEGIN;",
    ]
    for (k, old_ch, new_ch), ids in sorted(groups.items()):
        ids.sort()
        for i in range(0, len(ids), 5000):
            chunk = ",".join(map(str, ids[i:i + 5000]))
            out.append(
                f"UPDATE claims SET stance = substr(stance, 1, {k}) || {_q(old_ch)}"
                f" || substr(stance, {k + 2}) WHERE substr(stance, {k + 1}, 1) = {_q(new_ch)}"
                f" AND id IN ({chunk});")
    out.append("COMMIT;")
    return "\n".join(out) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--db", required=True)
    ap.add_argument("--rollback", default=DEFAULT_ROLLBACK)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args(argv)

    from datetime import date
    db = sqlite3.connect(args.db)
    plan, stats = build_plan(db)
    for key in ("saeima_vote_claims", "claims_matched_to_vote_url", "votes_affected",
                "claims_planned", "claims_already_correct", "claims_skipped_nonmatching"):
        print(f"{key}: {stats[key]}")
    starts = Counter(" ".join(p[5].split(": ", 1)[1].split()[:2]) for p in plan)
    print("biežākie saglabātie sākumi:")
    for s, n in starts.most_common(40):
        print(f"  {n:6d}  {s}")
    print(f"plan-hash: {plan_hash(plan)}")

    rb = Path(args.rollback)
    if not args.apply:
        rb.write_text(rollback_sql(plan, args.db, date.today().isoformat()), encoding="utf-8")
        print(f"DRY RUN — nekas nav mainīts. Atgriešanas SQL: {rb}")
        return 0

    if not rb.exists():
        print(f"ATTEIKTS: nav atgriešanas faila {rb} — vispirms dry run + commit.")
        return 1
    header = next((ln for ln in rb.read_text(encoding="utf-8").splitlines()
                   if ln.startswith("-- plan-hash:")), "")
    if f"plan-hash: {plan_hash(plan)} count: {len(plan)}" not in header:
        print(f"ATTEIKTS: plāns mainījies kopš dry run ({header!r}) — ģenerē atgriešanas failu no jauna.")
        return 1
    with db:
        n = 0
        for cid, _k, _o, _n, old_stance, new_stance in plan:
            n += db.execute("UPDATE claims SET stance = ? WHERE id = ? AND stance = ?",
                            (new_stance, cid, old_stance)).rowcount
        if n != len(plan):
            raise RuntimeError(f"atjaunināti {n} no {len(plan)} — transakcija atcelta")
    print(f"PIEMĒROTS: {n} claims. Atgriešana: sqlite3 {args.db} < {rb}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
