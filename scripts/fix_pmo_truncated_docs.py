"""One-shot data fix: reload truncated pmo.ee document content.

Background
---------
`documents` holds ~1027 rows with `source_url LIKE '%pmo.ee%'`; ~1010 of them
have `length(content) < 600` because the TVNet RSS shortener saved only the
headline + lede. A pmo.ee URL redirects to the full TVNet article
(`https://pmo.ee/8477763` -> `https://www.tvnet.lv/8477763/...`), so re-fetching
recovers the full body. This script re-fetches each truncated doc and updates
ONLY `content` (and `title`, when trafilatura yields a clearly better title over
a truncated one). `source_url` is NEVER touched — it is the claims-provenance key
(idempotence tuple `(opponent_id, source_url, topic)` + claim join).

Safety
------
- Always emits a paired rollback (`data/rollback_pmo_truncated_docs_2026-06-11.sql`)
  with the OLD content/title for every doc it would change, BEFORE any DB write.
- Only updates when the new content is substantially longer (>= 2x AND >= 800
  chars) so paywall stubs / error pages cannot overwrite the existing lede.
- Default is dry-run; a real run requires `--apply`.

Usage
-----
  python scripts/fix_pmo_truncated_docs.py --dry-run --limit 3
  python scripts/fix_pmo_truncated_docs.py --doc-id 42437 --apply
  python scripts/fix_pmo_truncated_docs.py --apply            # full run (operator)
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.db import DB_PATH, get_db  # noqa: E402

# Reuse ingest_url.py's fetch contract (httpx GET -> trafilatura + title).
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "lv,en;q=0.5",
}

THROTTLE_S = 1.5
MIN_NEW_CHARS = 800       # absolute floor for the refreshed body
MIN_GROWTH_FACTOR = 2.0   # new must be >= 2x the old length

ROLLBACK_PATH = ROOT / "data" / "rollback_pmo_truncated_docs_2026-06-11.sql"
SELECT_SQL = (
    "SELECT id, source_url, length(content) AS clen "
    "FROM documents WHERE source_url LIKE '%pmo.ee%' AND length(content) < 600 "
    "ORDER BY id"
)


def _fetch(url: str) -> Optional[dict]:
    """httpx GET -> {text, title}. None on any error. Mirrors ingest_url._default_fetch."""
    import httpx
    import trafilatura

    from src.title_extract import extract_title

    try:
        with httpx.Client(timeout=20.0, follow_redirects=True, headers=HEADERS) as client:
            resp = client.get(url)
            resp.raise_for_status()
    except Exception as e:  # noqa: BLE001
        print(f"  ERR fetch {url[:80]}: {e}", file=sys.stderr)
        return None
    text = trafilatura.extract(
        resp.text, include_comments=False, include_tables=False, deduplicate=True
    )
    return {"text": text, "title": extract_title(resp.text)}


def _sql_str(value: Optional[str]) -> str:
    """Render a Python value as a SQLite string literal (or NULL), single-quotes escaped."""
    if value is None:
        return "NULL"
    return "'" + value.replace("'", "''") + "'"


def _select_targets(db, *, doc_id: Optional[int], limit: Optional[int]) -> list:
    if doc_id is not None:
        rows = db.execute(
            "SELECT id, source_url, length(content) AS clen FROM documents WHERE id=?",
            (doc_id,),
        ).fetchall()
        if rows and "pmo.ee" not in (rows[0]["source_url"] or ""):
            print(
                f"  WARN doc {doc_id} source_url is not pmo.ee: "
                f"{rows[0]['source_url']!r}",
                file=sys.stderr,
            )
        return rows
    rows = db.execute(SELECT_SQL).fetchall()
    if limit is not None:
        rows = rows[:limit]
    return rows


def run(*, apply: bool, doc_id: Optional[int], limit: Optional[int], db_path: str) -> dict:
    db = get_db(db_path)
    targets = _select_targets(db, doc_id=doc_id, limit=limit)
    total = len(targets)
    print(f"Targets: {total} document(s) (apply={apply})", file=sys.stderr)

    # Collect planned updates first; rollback file is written before any DB write.
    planned: list[dict] = []  # {id, old_content, old_title, new_content, new_title}
    updated = skipped_short = fetch_failed = 0

    for i, row in enumerate(targets, 1):
        did, url, old_len = row["id"], row["source_url"], row["clen"]
        full = db.execute(
            "SELECT content, title FROM documents WHERE id=?", (did,)
        ).fetchone()
        old_content, old_title = full["content"], full["title"]

        parsed = _fetch(url)
        if i < total:
            time.sleep(THROTTLE_S)

        if parsed is None or not parsed.get("text"):
            fetch_failed += 1
            print(f"[{i}/{total}] id={did} FETCH_FAILED", file=sys.stderr)
            continue

        new_content = parsed["text"]
        new_len = len(new_content)
        if new_len < MIN_NEW_CHARS or new_len < old_len * MIN_GROWTH_FACTOR:
            skipped_short += 1
            print(
                f"[{i}/{total}] id={did} SKIP_SHORT {old_len}->{new_len} "
                f"(need >={MIN_NEW_CHARS} and >={MIN_GROWTH_FACTOR}x)",
                file=sys.stderr,
            )
            continue

        # Only replace title if existing looks truncated (ends mid-word, no
        # sentence end) AND the fetched one is longer + non-empty. Conservative:
        # default keep the old title.
        new_title = old_title
        cand_title = (parsed.get("title") or "").strip()
        if cand_title and old_title and len(cand_title) > len(old_title) and (
            not old_title.rstrip().endswith((".", "!", "?", "…"))
        ):
            new_title = cand_title

        planned.append({
            "id": did,
            "old_content": old_content,
            "old_title": old_title,
            "new_content": new_content,
            "new_title": new_title,
        })
        updated += 1
        title_note = " +title" if new_title != old_title else ""
        print(f"[{i}/{total}] id={did} UPDATE {old_len}->{new_len}{title_note}",
              file=sys.stderr)

    # Write rollback BEFORE touching the DB.
    if planned and apply:
        _write_rollback(planned)

    if apply:
        for p in planned:
            # word_count is read by render_news (word_count > 30 filter) and
            # analyze.py — keep it in sync with the refreshed body. On content
            # rollback, re-derive it the same way (it is not in the rollback SQL).
            db.execute(
                "UPDATE documents SET content=?, title=?, word_count=? WHERE id=?",
                (p["new_content"], p["new_title"], len(p["new_content"].split()), p["id"]),
            )
        db.commit()

    print(
        f"\nSUMMARY: updated={updated} skipped_short={skipped_short} "
        f"fetch_failed={fetch_failed} (apply={apply})",
        file=sys.stderr,
    )
    if planned and apply:
        print(f"Rollback written: {ROLLBACK_PATH} ({len(planned)} statements)",
              file=sys.stderr)
    elif not apply:
        print("DRY-RUN: no DB writes, no rollback file written. Pass --apply to commit.",
              file=sys.stderr)

    return {
        "updated": updated,
        "skipped_short": skipped_short,
        "fetch_failed": fetch_failed,
        "planned": len(planned),
    }


def _write_rollback(planned: list[dict]) -> None:
    # APPEND, never overwrite: each --apply run adds its own BEGIN..COMMIT
    # block. Earlier runs' statements (e.g. the doc 42437 verification run)
    # would otherwise be lost — those docs are no longer < 600 chars, so a
    # later full run's planned set does not include them.
    header = [
        "-- Rollback for fix_pmo_truncated_docs.py",
        "-- Forward change reverted: re-fetched full TVNet article body for "
        "truncated pmo.ee documents,",
        "--   updating documents.content (and title where the old one was "
        "truncated). source_url untouched.",
        "-- Apply date of forward change: 2026-06-11",
    ]
    lines = []
    if not ROLLBACK_PATH.exists():
        lines += header
    lines.append(f"-- Run block: {len(planned)} row(s).")
    lines.append("BEGIN;")
    for p in planned:
        lines.append(
            f"UPDATE documents SET content={_sql_str(p['old_content'])}, "
            f"title={_sql_str(p['old_title'])} WHERE id={p['id']};"
        )
    lines.append("COMMIT;")
    with ROLLBACK_PATH.open("a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main(argv: Optional[list[str]] = None) -> int:
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true",
                    help="commit DB writes (default: dry-run)")
    ap.add_argument("--dry-run", action="store_true",
                    help="explicit dry-run (default behavior; no DB writes)")
    ap.add_argument("--limit", type=int, default=None,
                    help="process only the first N candidates")
    ap.add_argument("--doc-id", type=int, default=None,
                    help="process exactly one document by id")
    ap.add_argument("--db", default=DB_PATH, help="DB path (default: live)")
    args = ap.parse_args(argv)

    apply = args.apply and not args.dry_run
    run(apply=apply, doc_id=args.doc_id, limit=args.limit, db_path=args.db)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
