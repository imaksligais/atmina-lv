#!/usr/bin/env python
"""Apstiprināto `@stance-checker` labojumu piemērošana pozīcijām (`stance` / `stated_at` / `quote`).

Noklusējums: dry-run (tikai lasa DB). Kārtība (CLAUDE.md escalation 8 — rollback
commitē PIRMS izmaiņas):

    .venv/Scripts/python.exe scripts/apply_stance_fixes.py --fixes F.json                  # 1. dry-run
    .venv/Scripts/python.exe scripts/apply_stance_fixes.py --fixes F.json --write-rollback # 2. rollback
    git commit data/rollback_stance_<rutīnas-diena>_<tag>.sql                              # 3. commit
    .venv/Scripts/python.exe scripts/apply_stance_fixes.py --fixes F.json --apply          # 4. apply

`--fixes` = JSON saraksts `{"id": int, "stance": str|null, "stated_at": "YYYY-MM-DD"|null,
"quote": str|null}`; null vai trūkstošs = lauku neaiztikt. `quote` pieņem tikai tad, ja
tas BURTISKI ir pozīcijas dokumenta tekstā (CLAUDE.md: citāts ir verbatim) — citādi
atsaka visu partiju. Vārti pierāda tikai to, ka teksts ir dokumentā — ka tie ir
RUNĀTĀJA vārdi (ne žurnālista vai cita cilvēka), pārbaudi pats. Nekad neraksta `topic`, `review_status`. Pēc apply pārrēķina
vektorus rindām, kuru stance mainījās (`quote` vektorā neietilpst).
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

from src.briefs import current_routine_day  # noqa: E402
from src.db import get_db  # noqa: E402
from src.quality import restore_text_from_source  # noqa: E402

DATA_DIR = REPO / "data"
_ID_LINE = re.compile(r"WHERE id = (\d+);")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def rollback_path(day: str, tag: str) -> Path:
    return DATA_DIR / f"rollback_stance_{day}_{tag}.sql"


def is_git_tracked(path: Path) -> bool:
    if not path.resolve().is_relative_to(REPO):
        return False
    return subprocess.run(
        ["git", "ls-files", "--error-unmatch", path.resolve().relative_to(REPO).as_posix()],
        cwd=REPO, capture_output=True,
    ).returncode == 0


def reembed_ids(ids: list[int]) -> int:
    from scripts.reembed_claims import reembed
    return reembed(ids)


def _sql(value: str | None) -> str:
    return "NULL" if value is None else "'" + value.replace("'", "''") + "'"


def _short(text: str | None, n: int = 110) -> str:
    text = text or ""
    return text if len(text) <= n else text[: n - 1] + "…"


def load_fixes(path: str) -> list[dict]:
    fixes = json.loads(Path(path).read_text(encoding="utf-8"))
    ids = [int(f["id"]) for f in fixes]
    if len(ids) != len(set(ids)):
        raise ValueError("dublēti id fixes failā")
    for f in fixes:
        if all(f.get(k) is None for k in ("stance", "stated_at", "quote")):
            raise ValueError(f"id {f['id']}: nav ne stance, ne stated_at, ne quote")
        if f.get("quote") is not None and not str(f["quote"]).strip():
            raise ValueError(f"id {f['id']}: tukšs quote")
        if f.get("stance") is not None and not str(f["stance"]).strip():
            raise ValueError(f"id {f['id']}: tukša stance")
        if f.get("stated_at") is not None and not _DATE.match(f["stated_at"]):
            raise ValueError(f"id {f['id']}: stated_at nav YYYY-MM-DD")
    return fixes


def rollback_sql(fixes: list[dict], old: dict[int, dict], day: str) -> str:
    ids = " ".join(str(int(f["id"])) for f in fixes)
    lines = [
        f"-- Rollback: stance-checker labojumi {day} (scripts/apply_stance_fixes.py).",
        f"-- Forward: UPDATE claims SET stance/stated_at/quote šīm {len(fixes)} position rindām; "
        "topic/review_status netiek aiztikti.",
        f"-- Apply date: {day}. Atjauno veco stance, stated_at un quote.",
        f"-- Pēc rollback: .venv/Scripts/python.exe scripts/reembed_claims.py {ids}",
        "BEGIN;",
    ]
    for f in fixes:
        o = old[int(f["id"])]
        lines.append(f"UPDATE claims SET stance = {_sql(o['stance'])}, "
                     f"stated_at = {_sql(o['stated_at'])}, quote = {_sql(o['quote'])} "
                     f"WHERE id = {int(f['id'])};")
    lines.append("COMMIT;")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    ap = argparse.ArgumentParser(description="Stance labojumu piemērošana (noklusējums dry-run).")
    ap.add_argument("--fixes", required=True, help="JSON saraksts ar apstiprinātajiem labojumiem")
    ap.add_argument("--tag", default="fixes", help="rollback faila vārda daļa (noklusējums fixes)")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--write-rollback", action="store_true")
    g.add_argument("--apply", action="store_true")
    args = ap.parse_args(argv)

    try:
        fixes = load_fixes(args.fixes)
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as e:
        print(f"ATSAKU: nederīgs fixes fails: {e}")
        return 2
    if not fixes:
        print("Fixes saraksts tukšs — nekas nav darāms.")
        return 0
    ids = [int(f["id"]) for f in fixes]
    rb = rollback_path(current_routine_day(), args.tag)

    db = get_db()
    try:
        rows = db.execute(
            f"SELECT c.id, c.stance, c.stated_at, c.quote, d.content FROM claims c "
            f"LEFT JOIN documents d ON d.id = c.document_id WHERE c.claim_type = 'position' "
            f"AND c.id IN ({','.join('?' * len(ids))})", ids,
        ).fetchall()
        old = {r["id"]: dict(r) for r in rows}
        missing = [i for i in ids if i not in old]
        if missing:
            print(f"ATSAKU: nav position rindas id {missing}")
            return 2
        # Citāts ir verbatim: tikai precīzs avota fragments (diakritika un reģistrs
        # ieskaitot). Diakritiku zudums vai pārfrāze → atsaka visu partiju.
        bad = [int(f["id"]) for f in fixes if f.get("quote") is not None
               and restore_text_from_source(f["quote"], old[int(f["id"])]["content"]) != f["quote"]]
        if bad:
            print(f"ATSAKU: quote nav burtiski pozīcijas dokumentā id {bad} — "
                  "kopē teikumu no avota precīzi (arī garumzīmes).")
            return 2

        for f in fixes:
            o = old[int(f["id"])]
            print(f"#{f['id']}")
            if f.get("stance") is not None:
                print(f"  stance:    {_short(o['stance'])}\n        →    {_short(f['stance'])}")
            if f.get("stated_at") is not None:
                print(f"  stated_at: {o['stated_at']} → {f['stated_at']} 00:00:00")
            if f.get("quote") is not None:
                print(f"  quote:     {_short(o['quote'])}\n        →    {_short(f['quote'])}")

        if args.write_rollback:
            rb.parent.mkdir(parents=True, exist_ok=True)
            rb.write_text(rollback_sql(fixes, old, current_routine_day()), encoding="utf-8")
            print(f"Rollback uzrakstīts: {rb}\nCommitē to PIRMS --apply (CLAUDE.md escalation 8).")
            return 0
        if not args.apply:
            print(f"Dry-run (labojumu skaits: {len(fixes)}) — nekas nav rakstīts. Nākamais solis: --write-rollback.")
            return 0

        if not rb.exists():
            print(f"ATSAKU: nav rollback faila {rb}. Vispirms --write-rollback un commit.")
            return 2
        if not is_git_tracked(rb):
            print(f"ATSAKU: {rb.name} nav commitēts (git ls-files). Commitē to PIRMS --apply.")
            return 2
        planned = {int(i) for i in _ID_LINE.findall(rb.read_text(encoding="utf-8"))}
        if planned != set(ids):
            print(f"ATSAKU: rollback id kopa ({len(planned)}) nesakrīt ar fixes ({len(ids)}). "
                  "Pārraksti ar --write-rollback un commitē vēlreiz.")
            return 2

        changed = [int(f["id"]) for f in fixes
                   if f.get("stance") is not None and f["stance"] != old[int(f["id"])]["stance"]]
        updated = 0
        with db:  # viena transakcija: izņēmums → ROLLBACK
            for f in fixes:
                sets, params = [], []
                if f.get("stance") is not None:
                    sets.append("stance = ?")
                    params.append(f["stance"])
                if f.get("stated_at") is not None:
                    sets.append("stated_at = ?")
                    params.append(f"{f['stated_at']} 00:00:00")
                if f.get("quote") is not None:
                    sets.append("quote = ?")
                    params.append(f["quote"])
                cur = db.execute(
                    f"UPDATE claims SET {', '.join(sets)} WHERE id = ? AND claim_type = 'position'",
                    (*params, int(f["id"])),
                )
                updated += cur.rowcount
            if updated != len(fixes):
                raise RuntimeError(f"atjauninātas {updated} no {len(fixes)} — atceļu transakciju")
    except RuntimeError as e:
        print(f"KĻŪDA: {e}")
        return 1
    finally:
        db.close()

    try:
        reembedded = reembed_ids(changed) if changed else 0
    except Exception as e:  # DB jau atjaunināts — ziņo, ko palaist, nevis traceback
        print(f"DB atjaunināts ({updated}), pārrēķins NEIZDEVĀS: {e}. Palaid: "
              f".venv/Scripts/python.exe scripts/reembed_claims.py {' '.join(map(str, changed))}")
        return 1
    print(f"pieprasīts {len(fixes)} / atjaunināts {updated} / pārrēķināts {reembedded} "
          f"(stance mainījās {len(changed)}). Rollback: {rb}")
    return 0 if updated == len(fixes) and reembedded == len(changed) else 1


if __name__ == "__main__":
    raise SystemExit(main())
