"""Citātu triāža 2026-09-30 (BACKLOG § Atliktais 50/55): `claims.quote` labojumi pa rindām.

Ievade: `docs/audits/2026-09-30-citatu-triaza/<set>.json` — katrai rindai orķestratora pārbaudīts
lēmums `REVERT` (jauns citāts = burtiska avota apakšvirkne) vai `NULL`. Citas rindas
(`KEEP`, `OPERATOR`) skripts neaiztiek. `claims.quote` ir VERBATIM (CLAUDE.md § LV gate):
labojums ir tikai atgriešanās pie avota teksta vai NULL, nekad pārrakstīšana.

Re-embed nav vajadzīgs: `store_claim()` iegulst `topic: stance`, ne `quote`.
Rollback tiek uzrakstīts PIRMS UPDATE: `data/rollback_quotes_<set>_2026-09-30.sql`.

    .venv/Scripts/python.exe scripts/_fix_quotes_2026_09_30.py <set>           # dry-run
    .venv/Scripts/python.exe scripts/_fix_quotes_2026_09_30.py <set> --apply
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.db import get_db  # noqa: E402


def q(s):
    return "NULL" if s is None else "'" + s.replace("'", "''") + "'"


def main(set_name: str, apply: bool) -> None:
    src = ROOT / f"docs/audits/2026-09-30-citatu-triaza/{set_name}.json"
    rollback = ROOT / f"data/rollback_quotes_{set_name}_2026-09-30.sql"
    rows = [r for r in json.loads(src.read_text(encoding="utf-8")) if r["decision"] in ("REVERT", "NULL")]
    db = get_db(None)
    plan = []
    for r in rows:
        cur = db.execute(
            "SELECT c.quote, coalesce(d.title,'') || char(10) || coalesce(d.content,'') "
            "FROM claims c JOIN documents d ON d.id = c.document_id WHERE c.id = ?", (r["id"],)
        ).fetchone()
        if cur is None:
            sys.exit(f"STOP: claim {r['id']} nav atrasts")
        old, text = cur
        if old != r["old_quote"]:
            sys.exit(f"STOP: claim {r['id']} quote mainījies kopš triāžas")
        new = r["new_quote"] if r["decision"] == "REVERT" else None
        if new is not None and new not in text and not r.get("verified_live"):
            sys.exit(f"STOP: claim {r['id']} jaunais citāts nav burtiska avota apakšvirkne")
        plan.append((r["id"], old, new))

    print(f"{set_name}: {len(plan)} labojumi ({sum(n is None for _, _, n in plan)} NULL, "
          f"{sum(n is not None for _, _, n in plan)} REVERT) no {len(rows)} ievades rindām")
    if not apply:
        return

    lines = [f"-- Rollback: scripts/_fix_quotes_2026_09_30.py {set_name} (apply 2026-09-30).",
             f"-- Atjauno claims.quote {len(plan)} rindām no {src.name}. Re-embed nav vajadzīgs.",
             "BEGIN;"]
    lines += [f"UPDATE claims SET quote = {q(old)} WHERE id = {cid};" for cid, old, _ in plan]
    lines.append("COMMIT;")
    rollback.write_text("\n".join(lines) + "\n", encoding="utf-8")

    with db:
        for cid, _, new in plan:
            db.execute("UPDATE claims SET quote = ? WHERE id = ?", (new, cid))
    got = sum(
        db.execute("SELECT quote IS ? FROM claims WHERE id = ?", (new, cid)).fetchone()[0]
        for cid, _, new in plan
    )
    print(f"pārbaude: {got}/{len(plan)} rindas sakrīt ar plānu; rollback {rollback.relative_to(ROOT)}")
    if got != len(plan):
        sys.exit("STOP: saglabāto skaits != plānotais")


if __name__ == "__main__":
    main(sys.argv[1], "--apply" in sys.argv)
