#!/usr/bin/env python
"""Dienas `NEEDS_REVIEW` pozīciju izvērtējuma pieraksts (`/dienas-rutina` solis 2c).

Līdz 2026-11-12 šo soli katru rutīnu rakstīja no jauna kā vienreizēju skriptu
(`scripts/fix_needs_review_*`, `scripts/_resolve_review_*`); šis ir tas pats ar
vieniem un tiem pašiem vārtiem. Kārtība (CLAUDE.md escalation 8 — rollback
commitē PIRMS izmaiņas):

    .venv/Scripts/python.exe scripts/resolve_needs_review.py --list                      # 0. rindas ar avotu
    .venv/Scripts/python.exe scripts/resolve_needs_review.py --decisions D.json          # 1. dry-run
    .venv/Scripts/python.exe scripts/resolve_needs_review.py --decisions D.json --write-rollback
    git commit data/rollback_needs_review_rutina_<rutīnas-diena>[_<tag>].sql             # 3. commit
    .venv/Scripts/python.exe scripts/resolve_needs_review.py --decisions D.json --apply  # 4. apply

`--decisions` = JSON saraksts `{"id": int, "evidence": str}`; `evidence` ir
pierādījums no avota (latviski, pilns teikums). Rindas, ko atstāj operatoram,
failā neliek. Raksta TIKAI `claims.reasoning`:

    NEEDS_REVIEW: <sākotnējais>  →  Izvērtēts YYYY-MM-DD: <evidence> Sākotnēji: <sākotnējais>

`review_status` atvasina trigeris (nekad ar roku); `stance`/`topic` netiek
aiztikti, tāpēc vektori nav jāpārrēķina. Stance labojumi iet caur
`scripts/apply_stance_fixes.py`.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from src.briefs import current_routine_day, needs_review_day_claims, routine_day_window  # noqa: E402
from src.db import get_db, now_lv  # noqa: E402

DATA_DIR = REPO / "data"
MARKER = "NEEDS_REVIEW"
PREFIX = MARKER + ":"
_ID_LINE = re.compile(r"WHERE id = (\d+);")
_SENTENCE_END = (".", "!", "?", "»", ")", "…")


def rollback_path(day: str, tag: str) -> Path:
    suffix = f"_{tag}" if tag else ""
    return DATA_DIR / f"rollback_needs_review_rutina_{day}{suffix}.sql"


def is_committed(path: Path) -> bool:
    """Fails ir git kokā UN nav mainīts kopš pēdējā commit."""
    if not path.resolve().is_relative_to(REPO):
        return False
    rel = path.resolve().relative_to(REPO).as_posix()
    tracked = subprocess.run(["git", "ls-files", "--error-unmatch", rel], cwd=REPO, capture_output=True)
    if tracked.returncode != 0:
        return False
    return subprocess.run(["git", "diff", "--quiet", "HEAD", "--", rel], cwd=REPO).returncode == 0


def _sql(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _short(text: str | None, n: int = 150) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= n else text[: n - 1] + "…"


def load_decisions(path: str) -> list[dict]:
    decisions = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(decisions, list):
        raise ValueError("fails nav JSON saraksts")
    ids = [int(d["id"]) for d in decisions]
    if len(ids) != len(set(ids)):
        raise ValueError("dublēti id")
    for d in decisions:
        ev = d.get("evidence")
        if not isinstance(ev, str) or not ev.strip():
            raise ValueError(f"id {d['id']}: tukšs evidence")
        if MARKER in ev:
            # Trigeris pēc marķiera vārda rindu atzīmētu no jauna.
            raise ValueError(f"id {d['id']}: evidence satur vārdu {MARKER}")
    return decisions


def new_reasoning(old: str, evidence: str, date: str) -> str:
    """Marķieri aizstāj ar izvērtējumu; sākotnējais teksts paliek aiz «Sākotnēji:»."""
    if not old.startswith(PREFIX):
        raise ValueError(f"reasoning nesākas ar «{PREFIX}»")
    rest = old[len(PREFIX):].strip()
    if MARKER in rest:
        raise ValueError(f"sākotnējā tekstā vārds {MARKER} ir vēlreiz")
    ev = evidence.strip()
    if not ev.endswith(_SENTENCE_END):
        ev += "."
    return f"Izvērtēts {date}: {ev} Sākotnēji: {rest}"


def rollback_sql(ids: list[int], old: dict[int, str], day: str) -> str:
    lines = [
        f"-- Rollback: rutīnas {day} solis 2c (scripts/resolve_needs_review.py).",
        f"-- Forward: {len(ids)} rindām claims.reasoning marķieris -> «Izvērtēts … Sākotnēji: …».",
        f"-- Apply date: {day}. Atjauno veco reasoning; review_status atjauno trigeris.",
        "BEGIN;",
    ]
    lines += [f"UPDATE claims SET reasoning = {_sql(old[i])} WHERE id = {i};" for i in ids]
    lines.append("COMMIT;")
    return "\n".join(lines) + "\n"


def list_day(day: str) -> int:
    """Dienas needs_review pozīcijas ar avota tekstu — viss, kas vajadzīgs lēmumam."""
    from src.analyze import get_claim_source

    db = get_db()
    try:
        rows = needs_review_day_claims(db, day)
        # Atpakaļdatētas pozīcijas (veci tvīti, kas ielādēti šodien) skeleta
        # logā (`stated_at`) nekrīt, bet ir šīs rutīnas darbs: ņem arī tās pēc
        # `created_at` (LV pulkstenis) rutīnas dienas logā (2026-11-18: 3 no 17).
        start, end = routine_day_window(day)
        seen = {r["id"] for r in rows}
        n_window = len(rows)
        rows += [r for r in db.execute(
            """SELECT c.id, p.name, c.topic FROM claims c
               JOIN tracked_politicians p ON c.opponent_id = p.id
               WHERE c.created_at >= ? AND c.created_at < ? AND c.claim_type = 'position'
                 AND c.review_status = 'needs_review' AND p.relationship_type != 'inactive'
               ORDER BY c.id""", (start, end),
        ) if r["id"] not in seen]
        ids = [r["id"] for r in rows]
        claims = {
            r["id"]: r for r in db.execute(
                f"SELECT id, stance, quote, reasoning, confidence FROM claims "
                f"WHERE id IN ({','.join('?' * len(ids))})", ids,
            )
        } if ids else {}
    finally:
        db.close()
    print(f"Rutīnas diena {day}: needs_review pozīcijas {len(rows)} "
          f"(dienas logā {n_window}, kā print_routine; atpakaļdatētas {len(rows) - n_window})")
    for r in rows:
        c = claims[r["id"]]
        src = get_claim_source(r["id"]) or {}
        print(f"\n===== {r['id']} | {r['name']} | {r['topic']} | c={c['confidence']}")
        print(f"stance:    {c['stance']}")
        print(f"quote:     {c['quote']}")
        print(f"reasoning: {c['reasoning']}")
        print(f"avots:     doc {src.get('document_id')} {src.get('source_url')}")
        if src.get("title"):
            print(f"virsraksts: {src['title']}")
        print(f"teksts:    {src.get('content')}")
        if src.get("context"):
            print(f"konteksts (tikai lasīšanai): {src['context']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    ap = argparse.ArgumentParser(description="NEEDS_REVIEW izvērtējumu pieraksts (noklusējums dry-run).")
    ap.add_argument("--list", action="store_true", help="izdrukā dienas needs_review rindas ar avotu")
    ap.add_argument("--day", help="rutīnas diena --list režīmam (noklusējums: pašreizējā)")
    ap.add_argument("--decisions", help="JSON saraksts {id, evidence}")
    ap.add_argument("--tag", default="", help="rollback faila vārda papildinājums (atkārtotam skrējienam tajā pašā dienā)")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--write-rollback", action="store_true")
    g.add_argument("--apply", action="store_true")
    args = ap.parse_args(argv)

    if args.list:
        return list_day(args.day or current_routine_day())
    if not args.decisions:
        ap.error("vajag --list vai --decisions")

    try:
        decisions = load_decisions(args.decisions)
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as e:
        print(f"ATSAKU: nederīgs decisions fails: {e}")
        return 2
    if not decisions:
        print("Saraksts tukšs — nekas nav darāms.")
        return 0
    ids = [int(d["id"]) for d in decisions]
    marks = ",".join("?" * len(ids))
    day = current_routine_day()
    rb = rollback_path(day, args.tag)
    date = now_lv()[:10]

    db = get_db()
    try:
        old = {r["id"]: r["reasoning"] or "" for r in db.execute(
            f"SELECT id, reasoning FROM claims WHERE id IN ({marks})", ids)}
        missing = [i for i in ids if i not in old]
        if missing:
            print(f"ATSAKU: nav claims rindas id {missing}")
            return 2
        new: dict[int, str] = {}
        bad: list[str] = []
        for d in decisions:
            cid = int(d["id"])
            try:
                new[cid] = new_reasoning(old[cid], d["evidence"], date)
            except ValueError as e:
                bad.append(f"#{cid}: {e} ({_short(old[cid], 60)})")
        if bad:
            # Viss vai nekas: daļējs skrējiens atstātu rollback ar citu id kopu.
            print("ATSAKU (nekas nav rakstīts):\n  " + "\n  ".join(bad))
            return 2

        for cid in ids:
            print(f"#{cid}  {_short(new[cid])}")

        if args.write_rollback:
            if rb.exists() and is_committed(rb):
                print(f"ATSAKU: {rb.name} jau ir commitēts — atkārtotam skrējienam dod --tag.")
                return 2
            rb.parent.mkdir(parents=True, exist_ok=True)
            rb.write_text(rollback_sql(ids, old, day), encoding="utf-8")
            print(f"Rollback uzrakstīts: {rb}\nCommitē to PIRMS --apply (CLAUDE.md escalation 8).")
            return 0
        if not args.apply:
            print(f"Dry-run ({len(ids)} rindas) — nekas nav rakstīts. Nākamais solis: --write-rollback.")
            return 0

        if not rb.exists():
            print(f"ATSAKU: nav rollback faila {rb}. Vispirms --write-rollback un commit.")
            return 2
        if not is_committed(rb):
            print(f"ATSAKU: {rb.name} nav commitēts vai ir mainīts pēc commit. Commitē to PIRMS --apply.")
            return 2
        planned = {int(i) for i in _ID_LINE.findall(rb.read_text(encoding="utf-8"))}
        if planned != set(ids):
            print(f"ATSAKU: rollback id kopa ({len(planned)}) nesakrīt ar decisions ({len(ids)}). "
                  "Pārraksti ar --write-rollback un commitē vēlreiz.")
            return 2

        updated = 0
        with db:  # viena transakcija: izņēmums → ROLLBACK
            for cid in ids:
                updated += db.execute(
                    "UPDATE claims SET reasoning = ? WHERE id = ? AND reasoning = ?",
                    (new[cid], cid, old[cid]),
                ).rowcount
            if updated != len(ids):
                raise RuntimeError(f"atjauninātas {updated} no {len(ids)} — atceļu transakciju")
        left = db.execute(
            f"SELECT COUNT(*) FROM claims WHERE id IN ({marks}) "
            f"AND review_status IS NOT 'reviewed'", ids,
        ).fetchone()[0]
    except RuntimeError as e:
        print(f"KĻŪDA: {e}")
        return 1
    finally:
        db.close()

    print(f"izvērtētas {updated} no {len(ids)}; bez statusa «reviewed»: {left}. Rollback: {rb}")
    return 0 if left == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
