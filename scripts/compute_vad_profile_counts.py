"""Compute profile-style VAD counts for all active politicians.

T6 of VAD analīze sanācija. Mirrors src/render/vad.py::get_vad_data_for_politicians
logic so the analīze top-N tables can match the politician profile pages.

For each politician:
1. Load all declarations sorted by year DESC, published_at DESC
2. For each annual declaration, compute deltas vs the next-older declaration
   in the sorted list (this is what the renderer does per i+1)
3. The "count" shown in the profile is len(this_year_unique_keys + removed_from_prev)
4. Output is tab-separated: pid<TAB>name<TAB>party<TAB>year<TAB>section<TAB>count
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from src.db import get_db  # noqa: E402
from src.vad.diff import compute_section_deltas  # noqa: E402

SECTION_TABLES = {
    "real_estate": "vad_real_estate",
    "companies": "vad_companies",
}


def main() -> None:
    db = get_db()
    politicians = db.execute(
        "SELECT id, name, party FROM tracked_politicians "
        "WHERE relationship_type != 'inactive' ORDER BY id"
    ).fetchall()

    print("pid\tname\tparty\tyear\tkind\tsection\tcount")

    for p in politicians:
        pid = p["id"]
        decls = db.execute(
            "SELECT id, declaration_year, declaration_kind FROM vad_declarations "
            "WHERE opponent_id = ? "
            "ORDER BY COALESCE(declaration_year, 0) DESC, published_at DESC",
            (pid,),
        ).fetchall()
        if not decls:
            continue

        # Pre-fetch section rows for all this politician's declarations
        decl_ids = [d["id"] for d in decls]
        rows_by_section: dict[str, dict[int, list[dict]]] = {
            s: defaultdict(list) for s in SECTION_TABLES
        }
        if decl_ids:
            placeholders = ",".join("?" * len(decl_ids))
            for section, table in SECTION_TABLES.items():
                rows = db.execute(
                    f"SELECT * FROM {table} WHERE declaration_id IN ({placeholders})",
                    decl_ids,
                ).fetchall()
                for r in rows:
                    d = dict(r)
                    rows_by_section[section][d["declaration_id"]].append(d)

        # Find the latest annual declaration index in the sorted list.
        # This is the one whose count appears in the analīze.
        for i, decl in enumerate(decls):
            if decl["declaration_kind"] != "annual":
                continue
            decl_id = decl["id"]
            year = decl["declaration_year"]
            # prev_decl is decls[i+1] if exists
            prev_id = decls[i + 1]["id"] if i + 1 < len(decls) else None

            for section in SECTION_TABLES:
                this_rows = rows_by_section[section].get(decl_id, [])
                prev_rows = rows_by_section[section].get(prev_id, []) if prev_id else []
                deltas = compute_section_deltas(section, prev_rows, this_rows)
                count = len(deltas)
                print(f"{pid}\t{p['name']}\t{p['party']}\t{year}\t{decl['declaration_kind']}\t{section}\t{count}")
            # Only the LATEST annual matters for analīze top-N
            break


if __name__ == "__main__":
    main()
