"""Manual ingest of Latvijas Vēstnesis JL feed.

Fetches https://www.vestnesis.lv/feed/JL, fetches each act detail page,
extracts body via trafilatura, runs politician matcher, stores documents,
and writes an extended log entry to wiki/log-ingest/.

Idempotent: dedup by act_id (extracted from /ta/id/<N> in URL) before
re-fetching detail pages, plus content_hash dedup on insert.

Not part of ingest_all() — designed for manual runs as part of the daily
routine, can be run multiple times per day.

Usage:
    python scripts/ingest_vestnesis.py [--limit N] [--dry-run] [--max-age-days D]
"""

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from src.db import get_db, insert_chunks, insert_document  # noqa: E402
from src.embeddings import embed_document  # noqa: E402
from src.ingest import _detect_language, _get_or_create_source  # noqa: E402
from src.ingest_log import _resolve_log_file, append_ingest_entry  # noqa: E402
from src.matcher import match_politicians  # noqa: E402
from src.vestnesis import (  # noqa: E402
    JL_FEED_URL,
    extract_signers,
    fetch_act_body,
    fetch_jl_feed,
)

VESTNESIS_SOURCE_CONFIG = {
    "url": JL_FEED_URL,
    "name": "Latvijas Vēstnesis JL",
    "tier": 1,
    "fetcher_mode": "fetcher",
    "rate_limit_seconds": 60,
    "legal_status": "approved",
    "legal_notes": (
        "Latvijas Vēstnesis oficiālais laidiens — JL (Jaunumi Laidienā) RSS, "
        "manuāls ingest via scripts/ingest_vestnesis.py"
    ),
    "last_tos_review": "2026-04-30",
}


def _existing_act_ids() -> set[str]:
    db = get_db()
    rows = db.execute(
        "SELECT source_url FROM documents "
        "WHERE source_url LIKE 'https://www.vestnesis.lv/ta/id/%'"
    ).fetchall()
    db.close()
    out: set[str] = set()
    for r in rows:
        m = re.search(r"/ta/id/(\d+)", r["source_url"] or "")
        if m:
            out.add(m.group(1))
    return out


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--limit", type=int, default=None, help="Max items this run")
    p.add_argument("--max-age-days", type=int, default=7,
                   help="Skip feed items older than N days (default 7)")
    p.add_argument("--dry-run", action="store_true",
                   help="Fetch and parse but do not write to DB or log")
    args = p.parse_args(argv)

    source_id = _get_or_create_source(VESTNESIS_SOURCE_CONFIG)
    if source_id is None:
        print("ERROR: failed to create or look up vestnesis source row",
              file=sys.stderr)
        return 1

    print(f"[fetch] {JL_FEED_URL}")
    items = fetch_jl_feed(max_age_days=args.max_age_days)
    print(f"[feed]  {len(items)} items in feed (≤ {args.max_age_days} days)")

    existing = _existing_act_ids()
    new_items = [it for it in items if it["act_id"] not in existing]
    print(f"[new]   {len(new_items)} new (after act_id dedup vs DB)")

    if args.limit is not None:
        new_items = new_items[: args.limit]
        print(f"[cap]   processing first {len(new_items)} (--limit)")

    stored_records: list[dict] = []
    skipped = 0
    failed = 0
    for it in new_items:
        url = it["url"]
        title = it["title"]
        print(f"[fetch] {it['act_id']} — {title[:70]}")
        body = fetch_act_body(url)
        if not body:
            print("  [skip] no body extracted (404 or trafilatura returned <200 chars)")
            skipped += 1
            continue
        signers = extract_signers(body)
        full_text = f"{title}\n\n{body}"
        politician_links = match_politicians(full_text)

        record = {
            "act_id": it["act_id"], "title": title, "url": url,
            "signers": signers, "n_politicians": len(politician_links or []),
        }

        if args.dry_run:
            stored_records.append(record)
            print(f"  [dry]  body={len(body)}c, signers={len(signers)}, "
                  f"politiķi={record['n_politicians']}")
            continue

        lang, _ = _detect_language(full_text)
        if lang not in ("lv", "ru", "en"):
            lang = "lv"

        doc_id = insert_document(
            full_text,
            source_id=source_id,
            platform="vestnesis",
            language=lang,
            source_url=url,
            published_at=it.get("published_at"),
            title=title,
            politician_links=politician_links or None,
        )
        if doc_id is None:
            print("  [skip] insert returned None (content_hash dedup)")
            skipped += 1
            continue
        chunks = embed_document(full_text)
        insert_chunks(doc_id, chunks)
        record["doc_id"] = doc_id
        stored_records.append(record)
        print(f"  [ok]   doc {doc_id}, body={len(body)}c, signers={len(signers)}, "
              f"politiķi={record['n_politicians']}")

    n_stored = len(stored_records)
    print(f"\n[done]  stored={n_stored} skipped={skipped} failed={failed} "
          f"(dry_run={args.dry_run})")

    if args.dry_run:
        return 0

    append_ingest_entry(
        source_name=VESTNESIS_SOURCE_CONFIG["name"],
        source_tier=VESTNESIS_SOURCE_CONFIG["tier"],
        documents_added=n_stored,
        documents_skipped=skipped,
        status="success" if failed == 0 else "partial",
        extra=f"manuāls ingest, {len(items)} feedā",
    )

    if stored_records:
        log_file = _resolve_log_file("wiki/log-ingest")
        with log_file.open("a", encoding="utf-8") as f:
            for r in stored_records:
                signers_str = ", ".join(r["signers"]) if r["signers"] else "—"
                title = r["title"]
                if len(title) > 110:
                    title = title[:107] + "…"
                f.write(
                    f"  - [{r['act_id']}]({r['url']}) — {title} "
                    f"(parakstītāji: {signers_str}; politiķi DB: {r['n_politicians']})\n"
                )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
