"""P3 Phase 0 — Extract 14. Saeima session UUIDs from calendar snapshot.

Reads the Playwright accessibility snapshot of:
  https://titania.saeima.lv/LIVS14/SaeimaLIVS2_DK.nsf/DK?ReadForm&calendar=1

The page contains the full 2022-2026 calendar for the 14. Saeima.
Emits data/saeima_backfill_sessions.json with one entry per unique session:
  { "year": 2025, "month": 12, "day": 18,
    "session_type": "regular" | "jautajumi" | "arkartas",
    "uuid": "...", "url": "https://..." }

Window: 2022-09 → 2025-12 (skip 2026 — already in DB).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SNAPSHOT_PATH = Path(__file__).parent.parent / ".playwright-mcp" / "page-2026-05-26T20-41-58-153Z.yml"
OUT_PATH = Path(__file__).parent.parent / "data" / "saeima_backfill_sessions.json"

LV_MONTHS = {
    "Janvāris": 1, "Februāris": 2, "Marts": 3, "Aprīlis": 4,
    "Maijs": 5, "Jūnijs": 6, "Jūlijs": 7, "Augusts": 8,
    "Septembris": 9, "Oktobris": 10, "Novembris": 11, "Decembris": 12,
}

SAEIMA_BASE = "https://titania.saeima.lv/LIVS14/SaeimaLIVS2_DK.nsf"

# A row in the calendar table looks like (in accessibility tree):
#   - cell "Janvāris" [ref=eN]
#   - cell "15" [ref=eN]:
#     - link "15" [ref=eN] [cursor=pointer]:
#       - /url: ./DK?ReadForm&nr=UUID
#
# Some cells contain "15(J)" or "12 / 15" — the suffix matters:
#   bare number  → regular session
#   N(J)         → questions/jautājumi session
#   N(A)         → ārkārtas
#   "A / B"      → continued session (links to earlier UUID; skip dedup later)


def parse_calendar(snapshot_text: str) -> list[dict]:
    """Return one entry per unique (year, uuid)."""
    lines = snapshot_text.splitlines()
    sessions: list[dict] = []
    seen: set[tuple[int, str]] = set()

    current_year: int | None = None
    current_month: int | None = None

    # Match year markers: "- generic [ref=eN]: 2025. gads."
    year_re = re.compile(r"(\d{4})\.\s*gads")
    # Match month start: "- row \"Janvāris ...\""  or  "- cell \"Janvāris\""
    month_re = re.compile(r'cell\s+"(' + "|".join(LV_MONTHS) + r')"')
    # Cell with day label: "- cell \"15(J)\"" or "- cell \"15 / 22\""
    cell_re = re.compile(r'-\s*cell\s+"([^"]+)"\s*\[ref=')
    # URL pattern in next line
    url_re = re.compile(r"\./DK\?ReadForm&nr=([a-f0-9-]{36})")

    # We process line-by-line and track current year/month context.
    i = 0
    while i < len(lines):
        ln = lines[i]
        ym = year_re.search(ln)
        if ym:
            current_year = int(ym.group(1))
            current_month = None
            i += 1
            continue

        # Month label
        mm = month_re.search(ln)
        if mm:
            current_month = LV_MONTHS[mm.group(1)]

        # Cell with day(s)
        cm = cell_re.search(ln)
        if cm and current_year is not None and current_month is not None:
            cell_text = cm.group(1).strip()
            if cell_text in LV_MONTHS:
                # Month-name cell, not a day
                i += 1
                continue

            # Look ahead a few lines for a /url
            url_line = None
            for j in range(i + 1, min(i + 5, len(lines))):
                m = url_re.search(lines[j])
                if m:
                    url_line = m.group(1)
                    break
            if not url_line:
                i += 1
                continue

            uuid = url_line
            if (current_year, uuid) in seen:
                i += 1
                continue
            seen.add((current_year, uuid))

            # Classify session type by cell suffix and pick canonical day
            # "15(J)" → jautājumi; "30(A)" → ārkārtas; "15 / 22" → continued (skip — earlier UUID will appear in its own date row)
            session_type = "regular"
            day_text = cell_text
            if "(J)" in cell_text:
                session_type = "jautajumi"
                day_text = cell_text.replace("(J)", "").strip()
            elif "(A)" in cell_text:
                session_type = "arkartas"
                day_text = cell_text.replace("(A)", "").strip()

            # Skip "A / B" continued-session cells — those link to an earlier UUID
            # that we'll capture on its own date row.
            if "/" in day_text:
                i += 1
                continue

            try:
                day = int(day_text)
            except ValueError:
                i += 1
                continue

            sessions.append({
                "year": current_year,
                "month": current_month,
                "day": day,
                "session_type": session_type,
                "uuid": uuid,
                "url": f"{SAEIMA_BASE}/DK?ReadForm&nr={uuid}",
            })

        i += 1

    return sessions


def main() -> int:
    if not SNAPSHOT_PATH.exists():
        print(f"ERROR: snapshot not found at {SNAPSHOT_PATH}", file=sys.stderr)
        return 1

    text = SNAPSHOT_PATH.read_text(encoding="utf-8")
    sessions = parse_calendar(text)

    # Filter to backfill window: 2022-09-01 → 2025-12-31 (inclusive)
    window = [
        s for s in sessions
        if (s["year"], s["month"]) >= (2022, 9) and s["year"] <= 2025
    ]

    # Sort chronologically
    window.sort(key=lambda s: (s["year"], s["month"], s["day"], s["session_type"]))

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(
        json.dumps(window, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    by_year: dict[int, int] = {}
    by_type: dict[str, int] = {}
    for s in window:
        by_year[s["year"]] = by_year.get(s["year"], 0) + 1
        by_type[s["session_type"]] = by_type.get(s["session_type"], 0) + 1

    print(f"Total sessions in 2022-09 → 2025-12 window: {len(window)}")
    print("By year:")
    for y, n in sorted(by_year.items()):
        print(f"  {y}: {n}")
    print("By session_type:")
    for t, n in by_type.items():
        print(f"  {t}: {n}")
    print(f"\nWrote {OUT_PATH}")

    # Print first and last few sessions for sanity
    print("\nFirst 3 sessions:")
    for s in window[:3]:
        print(f"  {s['year']}-{s['month']:02d}-{s['day']:02d}  {s['session_type']:10s}  {s['uuid']}")
    print("Last 3 sessions:")
    for s in window[-3:]:
        print(f"  {s['year']}-{s['month']:02d}-{s['day']:02d}  {s['session_type']:10s}  {s['uuid']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
