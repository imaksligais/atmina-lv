"""Vienreizēja migrācija 2026-08-21: pārparsē visus vad_declarations.raw_html
ar izlaboto parseri un atjauno laukus, ko skāra divi robi:

(a) _REG_NUMBER_RE paplašināts ar 5-sēriju ([49] → [459]) — 600 neizgūtu numuru
    visi ar 5-prefiksu; sekas: entity/source/holder/creditor_reg_number +
    is_individual karogi vairākās tabulās.
(b) §13 saturs <table> formā tagad nonāk vad_declarations.other_info.

Pāra rollback: data/rollback_vad_parser_reparse_2026-08-21.sql (rakstīts PRIES
apply, katram UPDATE ar vecajām vērtībām). Bez --apply tikai DRY-RUN atskaite.

Lietojums:
    .venv/Scripts/python.exe scripts/reparse_vad_sections_2026-08-21.py            # dry-run
    .venv/Scripts/python.exe scripts/reparse_vad_sections_2026-08-21.py --apply
"""

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from src.db import get_db  # noqa: E402
from src.vad.parsing import parse_declaration_html  # noqa: E402

ROLLBACK_PATH = REPO_ROOT / "data" / "rollback_vad_parser_reparse_2026-08-21.sql"

# (tabula, lauki, parse-attribūtu ceļš)
TABLE_SPECS = {
    "vad_positions": ("positions", ["entity_reg_number", "entity_address", "is_individual"]),
    "vad_companies": ("companies", ["reg_number", "address"]),
    "vad_savings": ("savings", ["holder_reg_number", "holder_address"]),
    "vad_debts": ("debts", ["creditor_reg_number", "creditor_address"]),
}
INCOME_FIELDS = ["source_reg_number", "is_individual"]


def _norm(v):
    """DB NULL vs Pydantic None salīdzināšanai; bool → int kā DB."""
    if isinstance(v, bool):
        return int(v)
    return v


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="raksta DB + rollback failu")
    args = ap.parse_args()

    db = get_db()
    decls = db.execute("SELECT id, other_info, raw_html FROM vad_declarations ORDER BY id").fetchall()
    print(f"[scan] {len(decls)} deklarāciju")

    updates: list[tuple[str, int, dict, dict]] = []  # (table, row_id, new_vals, old_vals)
    other_info_updates: list[tuple[int, str | None, str | None]] = []
    mismatches: list[str] = []

    for decl in decls:
        parsed = parse_declaration_html(decl["raw_html"] or "")

        if _norm(parsed.other_info) != decl["other_info"]:
            other_info_updates.append((decl["id"], decl["other_info"], parsed.other_info))

        for table, (attr, fields) in TABLE_SPECS.items():
            db_rows = db.execute(
                f"SELECT * FROM {table} WHERE declaration_id=? ORDER BY id", (decl["id"],)
            ).fetchall()
            new_rows = getattr(parsed, attr)
            if len(db_rows) != len(new_rows):
                mismatches.append(
                    f"{table} decl={decl['id']}: DB {len(db_rows)} vs parse {len(new_rows)} rindas — izlaista"
                )
                continue
            for db_row, new_row in zip(db_rows, new_rows):
                new_vals, old_vals = {}, {}
                for f in fields:
                    nv = _norm(getattr(new_row, f))
                    if nv != db_row[f]:
                        new_vals[f] = nv
                        old_vals[f] = db_row[f]
                if new_vals:
                    updates.append((table, db_row["id"], new_vals, old_vals))

        inc_rows = db.execute(
            "SELECT * FROM vad_income WHERE declaration_id=? ORDER BY id", (decl["id"],)
        ).fetchall()
        if len(inc_rows) != len(parsed.income):
            mismatches.append(
                f"vad_income decl={decl['id']}: DB {len(inc_rows)} vs parse {len(parsed.income)} rindas — izlaista"
            )
        else:
            for db_row, new_row in zip(inc_rows, parsed.income):
                new_vals, old_vals = {}, {}
                for f in INCOME_FIELDS:
                    nv = _norm(getattr(new_row, f))
                    if nv != db_row[f]:
                        new_vals[f] = nv
                        old_vals[f] = db_row[f]
                if new_vals:
                    updates.append(("vad_income", db_row["id"], new_vals, old_vals))

    # Denominatoru atskaite
    by_table: dict[str, int] = {}
    for table, _rid, _nv, _ov in updates:
        by_table[table] = by_table.get(table, 0) + 1
    print(f"[diff] other_info mainīsies: {len(other_info_updates)}")
    print(f"[diff] rindu UPDATE pa tabulām: {by_table}")
    print(f"[diff] kopā UPDATE rindu: {len(updates)}")
    if mismatches:
        print(f"[warn] rindu-skaita nesakritības (izlaistas): {len(mismatches)}")
        for m in mismatches[:10]:
            print("   ", m)

    if not args.apply:
        print("\n[dry-run] nekas nav rakstīts. Lieto --apply, lai izpildītu.")
        return 0

    # Rollback PRIESS apply
    lines = [
        "-- Rollback priekš: scripts/reparse_vad_sections_2026-08-21.py --apply (2026-08-21)",
        "-- Atgriež vecās vērtības visām rindām, ko migrācija mainīja.",
        "-- Pirms palaišanas pārliecinies, ka fails sedz TO PAŠU migrācijas skrējienu",
        "-- (fails tika pārrakstīts pie apply).",
        "",
    ]
    for did, old, _new in other_info_updates:
        if old is None:
            lines.append(f"UPDATE vad_declarations SET other_info=NULL WHERE id={did};")
        else:
            esc = old.replace("'", "''")
            lines.append(f"UPDATE vad_declarations SET other_info='{esc}' WHERE id={did};")
    for table, rid, _new, old in updates:
        sets = ", ".join(
            f"{f}=NULL" if v is None else f"{f}='{v}'" if isinstance(v, str) else f"{f}={int(v)}"
            for f, v in old.items()
        )
        lines.append(f"UPDATE {table} SET {sets} WHERE id={rid};")
    ROLLBACK_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    n_rollback_updates = len(other_info_updates) + len(updates)
    print(f"[rollback] uzrakstīts {ROLLBACK_PATH.name}: {n_rollback_updates} UPDATE")

    # Apply vienā transakcijā
    try:
        with db:
            for did, _old, new in other_info_updates:
                db.execute(
                    "UPDATE vad_declarations SET other_info=? WHERE id=?", (new, did)
                )
            for table, rid, new_vals, _old in updates:
                sets = ", ".join(f"{f}=?" for f in new_vals)
                db.execute(
                    f"UPDATE {table} SET {sets} WHERE id=?",
                    (*new_vals.values(), rid),
                )
        print(
            f"[done] other_info={len(other_info_updates)}, rindas={len(updates)} "
            f"(nesakritības izlaistas: {len(mismatches)})"
        )
        return 0
    except Exception as e:
        print(f"[fail] transakcija atcelta: {type(e).__name__}: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
