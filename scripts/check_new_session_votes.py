"""Check a titania sitting agenda for vote pages not yet in the DB.

Written 2026-08-21 for the airBaltic (1495/Lp14) 2. lasījuma balsojuma retry:
the bill card shows "2. lasījums / Likums / 20.08.2026", but the DK agenda
carries no voting page for it yet (LETA reports 54/21/1, unverified). titania
re-archives vote pages under new UNIDs (T8), so completeness is judged by
(vote_date, vote_time) — never by URL.

Usage:
    .venv/Scripts/python.exe scripts/check_new_session_votes.py [SITTING_UUID]

Default UUID = 886631a9-... (23.07 ārkārtas sesijas sēde, turpinājums 20.08).
Exit 0 + "NAV JAUNU" when nothing new; exit 2 + one line per genuinely new
vote (date, time, url, title) when the agenda holds votes the DB lacks.
Read-only — ingest stays with @saeima-tracker.
"""
import re
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from p3_backfill_year_urllib import SAEIMA_BASE, _extract_vote_urls_from_agenda, _fetch

DEFAULT_UUID = "886631a9-c2b2-4de0-9d9d-34adbcf3d4ae"


def main() -> int:
    uuid = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_UUID
    agenda = _fetch(f"{SAEIMA_BASE}/DK?ReadForm&nr={uuid}")
    urls = _extract_vote_urls_from_agenda(agenda)

    db = sqlite3.connect(REPO_ROOT / "data" / "atmina.db")
    have_urls = {r[0] for r in db.execute("SELECT url FROM saeima_votes")}
    have_keys = {(r[0], r[1]) for r in db.execute("SELECT vote_date, vote_time FROM saeima_votes")}

    missing = []
    for u in urls:
        if u in have_urls:
            continue
        try:
            page = _fetch(u)
        except Exception as e:  # noqa: BLE001 — report and keep scanning
            print(f"FETCH FAIL {u} {e}")
            continue
        m = re.search(
            r"(\d{2})\.(\d{2})\.(\d{4})[^\d]{0,10}(\d{2}:\d{2}:\d{2})",
            re.sub(r"<[^>]+>", " ", page),
        )
        if not m:
            print(f"BEZ DATUMA {u}")
            continue
        key = (f"{m.group(3)}-{m.group(2)}-{m.group(1)}", m.group(4))
        if key in have_keys:
            continue  # T8 re-archive duplicate of a stored vote
        title = re.search(r"<title>([^<]*)</title>", page)
        missing.append((key[0], key[1], u, (title.group(1) if title else "").strip()[:90]))

    print(f"darba kārtībā: {len(urls)} balsojumu URL; DB (date,time) atslēgas: {len(have_keys)}")
    if not missing:
        print("NAV JAUNU balsojumu.")
        return 0
    print(f"JAUNI balsojumi: {len(missing)}")
    for d, t, u, ti in missing:
        print(f"  {d} {t} {u} | {ti}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
