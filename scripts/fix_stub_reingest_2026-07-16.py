"""One-shot data fix: re-ingest full text for 8 truncated stub documents.

Background
---------
Eight reviewed documents were stored as truncated RSS/shortener stubs
(word_count 30-67), so claim extraction never saw the real article body. This
script re-fetches each by its existing `source_url` and updates ONLY
`content`, `title` (when the refreshed one is clearly better), and `word_count`.
`source_url` is NEVER touched — it is the claims-provenance key (idempotence
tuple `(opponent_id, source_url, topic)` + claim join).

Docs (all reviewed):
  52683 lsm.lv · 53312 pmo.ee→tvnet · 53313 lsm.lv · 65226 diena.lv (paywall,
  likely fails) · 66455 pmo.ee→tvnet · 66466 lsm.lv (LMT/Tet — high value) ·
  66471 lsm.lv (LMT/Tet) · 66502 jauns.lv

Fetch path
----------
Reuses ingest_url._default_fetch (the canonical project ingest contract:
httpx GET follow_redirects + trafilatura HTML extract / pypdf + title). pmo.ee
URLs redirect to the full tvnet.lv article, so follow_redirects recovers them.

Safety
------
- Writes a paired rollback (data/rollback_stub_reingest_2026-07-16.sql) with the
  OLD content/title/word_count/reviewed_at for every doc it would change, BEFORE
  any DB write.
- Only updates when the new content is substantially longer (>= MIN_GROWTH_FACTOR
  AND >= MIN_NEW_CHARS) so paywall stubs / error pages cannot overwrite the lede.
- For each doc that is substantially expanded AND does not look like a paywall
  fragment, sets reviewed_at=NULL so the evening routine re-picks it for
  extraction. Failed fetches / paywall stubs are left exactly as-is.
- Default is dry-run; a real run requires --apply.

Usage
-----
  .venv/Scripts/python.exe scripts/fix_stub_reingest_2026-07-16.py --dry-run
  .venv/Scripts/python.exe scripts/fix_stub_reingest_2026-07-16.py --apply
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.ingest_url import _default_fetch  # noqa: E402 — reuse canonical fetch
from src.db import DB_PATH, get_db  # noqa: E402

TARGET_IDS = [52683, 53312, 53313, 65226, 66455, 66466, 66471, 66502]

THROTTLE_S = 1.5
MIN_NEW_CHARS = 800       # absolute floor for the refreshed body
MIN_GROWTH_FACTOR = 2.0   # new must be >= 2x the old length

# Heuristic paywall / consent markers — if the refreshed body is short-ish AND
# contains one of these, treat as a paywall fragment: still record it (so we do
# not re-fetch forever) but do NOT clear reviewed_at.
PAYWALL_MARKERS = (
    "abonē",
    "abonement",
    "raksts pieejams tikai",
    "pieejams tikai abonentiem",
    "piekļuve rakstam",
    "kļūsti par abonentu",
    "lai turpinātu lasīt",
    "pierakstīties, lai lasītu",
)

ROLLBACK_PATH = ROOT / "data" / "rollback_stub_reingest_2026-07-16.sql"


def _sql_str(value: Optional[str]) -> str:
    if value is None:
        return "NULL"
    return "'" + value.replace("'", "''") + "'"


def _looks_paywall(text: str, new_len: int) -> bool:
    low = text.lower()
    if any(m in low for m in PAYWALL_MARKERS) and new_len < 1500:
        return True
    return False


def run(*, apply: bool, db_path: str) -> dict:
    db = get_db(db_path)
    planned: list[dict] = []   # rows to UPDATE (+ rollback data)
    report: list[dict] = []    # per-doc reporting

    total = len(TARGET_IDS)
    for i, did in enumerate(TARGET_IDS, 1):
        row = db.execute(
            "SELECT id, source_url, content, title, word_count, reviewed_at, "
            "length(content) AS clen FROM documents WHERE id=?",
            (did,),
        ).fetchone()
        if row is None:
            report.append({"id": did, "status": "NOT_FOUND", "old_wc": None,
                           "new_wc": None, "clear_reviewed": False})
            print(f"[{i}/{total}] id={did} NOT_FOUND", file=sys.stderr)
            continue

        url = row["source_url"]
        old_content, old_title = row["content"], row["title"]
        old_wc, old_reviewed, old_len = row["word_count"], row["reviewed_at"], row["clen"]

        parsed = _default_fetch(url)
        if i < total:
            time.sleep(THROTTLE_S)

        if parsed is None or not parsed.get("text"):
            report.append({"id": did, "status": "FETCH_FAILED", "old_wc": old_wc,
                           "new_wc": old_wc, "clear_reviewed": False})
            print(f"[{i}/{total}] id={did} FETCH_FAILED", file=sys.stderr)
            continue

        new_content = parsed["text"]
        new_len = len(new_content)
        new_wc = len(new_content.split())

        if new_len < MIN_NEW_CHARS or new_len < old_len * MIN_GROWTH_FACTOR:
            report.append({"id": did, "status": "SKIP_SHORT", "old_wc": old_wc,
                           "new_wc": new_wc, "clear_reviewed": False,
                           "note": f"{old_len}->{new_len} chars"})
            print(f"[{i}/{total}] id={did} SKIP_SHORT {old_len}->{new_len}",
                  file=sys.stderr)
            continue

        paywall = _looks_paywall(new_content, new_len)

        # Title: replace only when refreshed one is longer AND old looks truncated.
        new_title = old_title
        cand = (parsed.get("title") or "").strip()
        if cand and old_title and len(cand) > len(old_title) and (
            not old_title.rstrip().endswith((".", "!", "?", "…"))
        ):
            new_title = cand

        clear_reviewed = not paywall  # only re-queue genuine full articles
        planned.append({
            "id": did,
            "old_content": old_content,
            "old_title": old_title,
            "old_wc": old_wc,
            "old_reviewed": old_reviewed,
            "new_content": new_content,
            "new_title": new_title,
            "new_wc": new_wc,
            "clear_reviewed": clear_reviewed,
        })
        status = "UPDATE_PAYWALL" if paywall else "UPDATE"
        report.append({"id": did, "status": status, "old_wc": old_wc,
                       "new_wc": new_wc, "clear_reviewed": clear_reviewed,
                       "note": f"{old_len}->{new_len} chars"})
        rev_note = " reviewed->NULL" if clear_reviewed else " reviewed=KEEP(paywall)"
        title_note = " +title" if new_title != old_title else ""
        print(f"[{i}/{total}] id={did} {status} {old_len}->{new_len}"
              f"{title_note}{rev_note}", file=sys.stderr)

    if planned and apply:
        _write_rollback(planned)
        for p in planned:
            if p["clear_reviewed"]:
                db.execute(
                    "UPDATE documents SET content=?, title=?, word_count=?, "
                    "reviewed_at=NULL WHERE id=?",
                    (p["new_content"], p["new_title"], p["new_wc"], p["id"]),
                )
            else:
                db.execute(
                    "UPDATE documents SET content=?, title=?, word_count=? WHERE id=?",
                    (p["new_content"], p["new_title"], p["new_wc"], p["id"]),
                )
        db.commit()

    print("\nSUMMARY:", file=sys.stderr)
    for r in report:
        print(f"  id={r['id']:>6} {r['status']:<14} wc {r['old_wc']}->{r['new_wc']} "
              f"clear_reviewed={r['clear_reviewed']}", file=sys.stderr)
    if planned and apply:
        print(f"Rollback written: {ROLLBACK_PATH} ({len(planned)} rows)", file=sys.stderr)
    elif not apply:
        print("DRY-RUN: no DB writes, no rollback. Pass --apply.", file=sys.stderr)

    return {"report": report, "planned": len(planned)}


def _write_rollback(planned: list[dict]) -> None:
    lines = [
        "-- rollback_stub_reingest_2026-07-16.sql",
        "-- Reverts: scripts/fix_stub_reingest_2026-07-16.py",
        "-- Forward change applied: 2026-07-16",
        "--   Re-ingested full article text for 8 truncated stub documents,",
        "--   updating documents.content/title/word_count and clearing reviewed_at",
        "--   (to NULL) on the substantially-expanded, non-paywall docs so the",
        "--   evening routine re-extracts them. source_url untouched.",
        "-- This restores the original content/title/word_count/reviewed_at.",
        "BEGIN;",
    ]
    for p in planned:
        rev = _sql_str(p["old_reviewed"]) if p["old_reviewed"] is not None else "NULL"
        lines.append(
            f"UPDATE documents SET content={_sql_str(p['old_content'])}, "
            f"title={_sql_str(p['old_title'])}, word_count={p['old_wc']}, "
            f"reviewed_at={rev} WHERE id={p['id']};"
        )
    lines.append("COMMIT;")
    ROLLBACK_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: Optional[list[str]] = None) -> int:
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="commit DB writes")
    ap.add_argument("--dry-run", action="store_true", help="explicit dry-run")
    ap.add_argument("--db", default=DB_PATH, help="DB path (default: live)")
    args = ap.parse_args(argv)
    apply = args.apply and not args.dry_run
    run(apply=apply, db_path=args.db)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
