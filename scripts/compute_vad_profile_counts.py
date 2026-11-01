"""Compute profile-style VAD counts for all active politicians.

T6 of VAD analīze sanācija. Counts come straight from the profile renderer
(`src.render.vad.latest_annual_counts`): the latest annual declaration,
deltas vs the CHRONOLOGICALLY previous declaration (yearless start
declarations included) — the number the profile section header shows.
Output is tab-separated: pid<TAB>name<TAB>party<TAB>year<TAB>kind<TAB>section<TAB>count
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from src.db import get_db  # noqa: E402
from src.render.vad import latest_annual_counts  # noqa: E402

SECTIONS = ["real_estate", "companies"]


def main() -> None:
    db = get_db()
    politicians = db.execute(
        "SELECT id, name, party FROM tracked_politicians "
        "WHERE relationship_type != 'inactive' ORDER BY id"
    ).fetchall()
    counts = latest_annual_counts(db, [p["id"] for p in politicians], SECTIONS)

    print("pid	name	party	year	kind	section	count")
    for p in politicians:
        for section in SECTIONS:
            c = counts[section].get(p["id"])
            if c is not None:
                print(f"{p['id']}	{p['name']}	{p['party']}	{c.year}	annual	{section}	{c.total}")


if __name__ == "__main__":
    main()
