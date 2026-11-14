"""Pretrunas faktu pārbaude pret avotiem (tikai lasa DB).

Lietošana:
    .venv/Scripts/python.exe scripts/check_contradiction.py --id 68
    .venv/Scripts/python.exe scripts/check_contradiction.py --draft melnraksts.json
    .venv/Scripts/python.exe scripts/check_contradiction.py --published

`--draft` JSON: {"opponent_id": 37, "claim_old_id": 1, "claim_new_id": 2,
"summary": "…", "headline": "…", "severity": "minor_shift",
"extra_sources": [{"url": "…", "text": "burtisks fragments"}]}.
`extra_sources` — tikai citātam no avota ārpus abu pozīciju dokumentiem un
balsojumu tabulas; URL obligāts.

Izdruka: faktu lapa (ko saka DB), tad atradumi. `KĻŪDA` = izejas kods 1;
`PĀRBAUDI` = salīdzini pats ar faktu lapu un atbildi atskaitē. Kad lietot:
`.claude/commands/dienas-rutina.md` 3. solis, `wiki/operations/quality-bars.md` § Pretruna.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.contradiction_check import ERROR, check_text, fact_sheet, render_sheet  # noqa: E402
from src.db import get_db  # noqa: E402
from src.models import Contradiction  # noqa: E402


def _model_problem(draft: dict) -> str | None:
    """Tie paši teksta vārti, ko piemēro `store_contradiction()`."""
    try:
        Contradiction(
            opponent_id=draft["opponent_id"], claim_old_id=draft["claim_old_id"], claim_new_id=draft["claim_new_id"],
            topic="x", severity=draft.get("severity") or "minor_shift", salience=0.5,
            summary=draft["summary"], headline=draft.get("headline"),
        )
    except Exception as e:  # pydantic ValidationError
        return str(e).splitlines()[-1].strip()
    return None


def check_one(db, draft: dict, quiet: bool = False) -> int:
    """Izdrukā faktu lapu un atradumus; atgriež KĻŪDU skaitu."""
    sheet = fact_sheet(db, draft["opponent_id"], draft["claim_old_id"], draft["claim_new_id"])
    problems = [str(p) for p in check_text(sheet, draft["summary"], draft.get("headline"), draft.get("extra_sources"), db=db)]
    for e in draft.get("extra_sources") or []:
        if not e.get("url"):
            problems.append(f"{ERROR} [avots] papildu avotam nav URL")
    model = _model_problem(draft)
    if model:
        problems.append(f"{ERROR} [modelis] {model}")
    errors = sum(p.startswith(ERROR) for p in problems)
    label = f"#{draft['id']}" if draft.get("id") else "melnraksts"
    if not quiet:
        print(render_sheet(sheet))
        print("\nVIRSRAKSTS:", draft.get("headline"))
        print("KOPSAVILKUMS:", draft["summary"])
        print()
    for p in problems:
        print(f"{label}: {p}" if quiet else p)
    print(f"{label}: REZULTĀTS {'LABO' if errors else 'MAŠĪNA NEKO NEATRADA' if not problems else 'IZLASI PĀRBAUDĀMOS'}"
          f" ({errors} kļūdas, {len(problems) - errors} pārbaudāmi)")
    return errors


def _stored(db, where: str, params: tuple = ()) -> list[dict]:
    rows = db.execute(
        f"SELECT id, opponent_id, claim_old_id, claim_new_id, summary, headline, severity FROM contradictions WHERE {where} ORDER BY id",
        params,
    ).fetchall()
    return [dict(r) for r in rows]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--id", type=int, nargs="+", help="glabātas pretrunas id")
    g.add_argument("--draft", type=Path, help="melnraksta JSON pirms glabāšanas")
    g.add_argument("--published", action="store_true", help="visas publicētās (confirmed=1), īsā izdruka")
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    db = get_db()
    try:
        if args.draft:
            drafts = [json.loads(args.draft.read_text(encoding="utf-8"))]
        elif args.published:
            drafts = _stored(db, "confirmed = 1")
        else:
            drafts = _stored(db, f"id IN ({','.join('?' * len(args.id))})", tuple(args.id))
            missing = set(args.id) - {d["id"] for d in drafts}
            if missing:
                print(f"KĻŪDA: pretrunas {sorted(missing)} nav DB")
                return 1
        errors = sum(check_one(db, d, quiet=args.published) for d in drafts)
        print(f"\nPārbaudītas {len(drafts)} pretrunas, ar kļūdām: {errors}")
        return 1 if errors else 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
