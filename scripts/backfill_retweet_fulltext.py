"""Re-fetch truncated retweets so their stored text carries the full original.

WHY THIS EXISTS
`_tweet_text()` was fixed 2026-07-24 to expand `tweet.retweeted_tweet`, but
that fix is forward-only. History holds ~8900 `RT @` documents capped at X's
legacy 140-character cut. The cost is not extraction — a bare retweet is
nobody's first-party position — but LINKAGE: `link_politicians_to_documents`
text-scans `content`, so a politician named only past the cut was never linked
to the document. A silent coverage gap, not a visible error.
See BACKLOG § Vēsturisko retvītu backfill.

TWO TRAPS THIS SCRIPT IS BUILT AROUND

1. `insert_document()` cannot be used. Its update-in-place branch is gated to
   `platform='web'` ("X tweets have stable URL→content guarantees" — which is
   exactly the assumption the 140-char cut violates). Calling it for a tweet
   would fall through to INSERT and create a duplicate document, orphaning the
   original's claims and junctions. So the row is updated directly.

2. `scraped_at` must NOT be touched. `routine._check_analysis` compares
   `documents.scraped_at` against `analyses.created_at` to decide who is
   pending analysis; bumping it on thousands of historical rows would re-open
   their politicians as pending and corrupt the daily routine's status. The
   document was scraped when it was scraped; only its text is being repaired.

WHAT COUNTS AS TRUNCATED
`RT @` documents that end in an ellipsis or sit at the 139-152 char boundary.
Shorter retweets without an ellipsis are complete originals and are skipped —
measured 2026-07-25: 8910 truncated, 2335 already whole.

SAFETY
Read-only until `--apply`. Idempotent and resumable: a document whose re-fetched
text is not longer than what is stored is left alone, so re-running costs
requests but changes nothing. Tweets that are deleted, private or suspended
come back missing and keep their truncated text rather than being blanked.

Usage:
    .venv/Scripts/python.exe scripts/backfill_retweet_fulltext.py            # dry run, all
    .venv/Scripts/python.exe scripts/backfill_retweet_fulltext.py --limit 200
    .venv/Scripts/python.exe scripts/backfill_retweet_fulltext.py --apply
"""
from __future__ import annotations

import argparse
import asyncio
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.db import _compute_content_hash, _compute_simhash, get_db  # noqa: E402
from src.x_scraper import fetch_tweets_by_ids  # noqa: E402

BATCH_SIZE = 100  # X's TweetResultsByRestIds ceiling; ~1s per call
STATUS_RE = re.compile(r"/status/(\d+)")

# Truncated = ends in an ellipsis, or sits inside the legacy cut band. The
# band is BOUNDED at 152 on purpose: X cuts at 140 but the stored string runs
# to 152 once the `RT @handle: ` prefix is counted, and an unbounded floor
# (`length >= 139`) would re-select every document this script has ALREADY
# repaired. That is not merely wasteful — a second run would then regenerate
# the rollback file from the repaired text, quietly making the first run
# irreversible. Measured 2026-07-25 before any repair: max RT length was
# exactly 152, so nothing legitimate lives above the band.
TARGET_SQL = """
    SELECT id, source_url, content
    FROM documents
    WHERE platform = 'twitter'
      AND content LIKE 'RT @%'
      AND source_url LIKE '%/status/%'
      AND length(content) <= 152
      AND (content LIKE '%' || char(8230)
           OR content LIKE '%...'
           OR length(content) >= 139)
    ORDER BY id
"""


def select_targets(limit: int | None) -> list[dict]:
    db = get_db()
    rows = db.execute(TARGET_SQL).fetchall()
    db.close()
    out = []
    for r in rows:
        m = STATUS_RE.search(r["source_url"] or "")
        if not m:
            continue
        out.append({"doc_id": r["id"], "tweet_id": m.group(1),
                    "old": r["content"], "old_len": len(r["content"])})
        if limit and len(out) >= limit:
            break
    return out


def _sql_lit(text: str) -> str:
    return "'" + text.replace("'", "''") + "'"


def open_rollback(path: Path, count: int):
    """Start the paired rollback file BEFORE any row is touched.

    CLAUDE.md § Schema invariants: every hand-run data migration ships a
    rollback committed alongside it. Here the rollback cannot be hand-written
    because the prior text lives only in the rows being overwritten, so the
    script emits it row by row as it goes — each statement written and flushed
    before its forward UPDATE runs, never after.
    """
    first_run = not path.exists()
    # Append, never truncate: the script is meant to be run in pilots and
    # resumed, and each run's rollback rows are the ONLY record of the text it
    # overwrote. Truncating here would silently strand an earlier run.
    fh = path.open("a", encoding="utf-8")
    if first_run:
        fh.write("-- ROLLBACK: retvītu pilnteksta backfill\n")
        fh.write("-- Atceļ: scripts/backfill_retweet_fulltext.py --apply\n")
        fh.write("-- Piemērots (forward): 2026-07-25\n")
        fh.write("-- Atjauno apcirsto content/hash/simhash/word_count.\n")
        fh.write("-- scraped_at netika mainīts uz priekšu, tāpēc to neatjauno arī šeit.\n")
        fh.write("-- Katrs skrējiens pievieno savu transakciju; piemēro failu VESELU.\n")
    fh.write(f"\n-- skrējiens: {count} kandidāti\nBEGIN TRANSACTION;\n")
    return fh


def write_rollback_row(fh, doc_id: int, old_text: str) -> None:
    fh.write(
        f"UPDATE documents SET content = {_sql_lit(old_text)}, "
        f"content_hash = {_sql_lit(_compute_content_hash(old_text))}, "
        f"simhash = {_compute_simhash(old_text)}, "
        f"word_count = {len(old_text.split())} WHERE id = {doc_id};\n"
    )
    fh.flush()


def apply_update(doc_id: int, new_text: str) -> bool:
    """Rewrite one document's text in place, keeping identity and provenance.

    Updates only what the new text invalidates: content, its hash, its simhash
    and the word count. `scraped_at`, `source_url`, `published_at` and every
    junction and claim stay exactly as they were.

    Returns False without writing when the expanded text would collide with
    another document's `content_hash` (a UNIQUE column). That collision is not
    a defect but an honest consequence of the repair: when two tracked accounts
    retweeted the SAME original, expansion makes both documents literally
    identical, and the database is right to refuse the second. The sibling
    document keeps the full text and gets linked, so the mention is not lost —
    only this row stays truncated.
    """
    db = get_db()
    content_hash = _compute_content_hash(new_text)
    clash = db.execute(
        "SELECT id FROM documents WHERE content_hash = ? AND id != ?",
        (content_hash, doc_id),
    ).fetchone()
    if clash:
        db.close()
        return False
    db.execute(
        """UPDATE documents
           SET content = ?, content_hash = ?, simhash = ?, word_count = ?
           WHERE id = ?""",
        (new_text, content_hash, _compute_simhash(new_text),
         len(new_text.split()), doc_id),
    )
    db.commit()
    db.close()
    return True


def repaired_doc_ids() -> list[int]:
    """Every retweet document whose stored text is past the legacy cut.

    Used by `--relink-only`. Re-linking is the point of the whole backfill, and
    it runs at the END of a fetch pass, so any interruption leaves repaired
    text sitting unread. This lets the linking step be re-run on its own; it is
    idempotent (junction writes are INSERT OR IGNORE).
    """
    db = get_db()
    rows = db.execute(
        """SELECT id FROM documents
           WHERE platform = 'twitter' AND content LIKE 'RT @%'
             AND length(content) > 152
           ORDER BY id"""
    ).fetchall()
    db.close()
    return [r["id"] for r in rows]


def relink(doc_ids: list[int]) -> int:
    from src.matcher import link_politicians_to_documents

    before = _junction_count()
    linked = link_politicians_to_documents(doc_ids=doc_ids)
    after = _junction_count()
    print(f"Dokumenti ar atrastiem politiķiem: {len(linked)}")
    print(f"JAUNI junctions: {after - before} (kopā {after})")
    return after - before


def _junction_count() -> int:
    db = get_db()
    n = db.execute("SELECT COUNT(*) FROM document_politicians").fetchone()[0]
    db.close()
    return n


async def run(limit: int | None, apply: bool) -> int:
    targets = select_targets(limit)
    print(f"Apcirstie RT dokumenti: {len(targets)}")
    if not targets:
        return 0
    print(f"Režīms: {'PIEMĒRO IZMAIŅAS' if apply else 'DRY RUN (nekas netiek rakstīts)'}")
    print(f"Batch: {BATCH_SIZE} ID / pieprasījums\n")

    updated: list[int] = []
    unchanged = missing = duplicate = 0
    grew_total = 0
    t0 = time.time()

    rollback_path = (Path(__file__).resolve().parent.parent / "data"
                     / "rollback_retweet_fulltext_backfill_2026-07-25.sql")
    rollback = open_rollback(rollback_path, len(targets)) if apply else None

    for start in range(0, len(targets), BATCH_SIZE):
        chunk = targets[start:start + BATCH_SIZE]
        by_tweet = {c["tweet_id"]: c for c in chunk}
        fetched = await fetch_tweets_by_ids([c["tweet_id"] for c in chunk])

        for tweet_id, item in by_tweet.items():
            got = fetched.get(tweet_id)
            if got is None:
                missing += 1
                continue
            new_text = got.get("text") or ""
            # Only ever grow. A shorter or equal answer means the original was
            # already whole, or X gave us less than we hold — either way the
            # stored text is not worse, and overwriting could only lose data.
            if len(new_text) <= item["old_len"]:
                unchanged += 1
                continue
            if apply:
                # Rollback statement first, flushed to disk, THEN the update:
                # a crash mid-run must never leave a rewritten row whose prior
                # text was not recorded.
                write_rollback_row(rollback, item["doc_id"], item["old"])
                if not apply_update(item["doc_id"], new_text):
                    duplicate += 1
                    continue
            grew_total += len(new_text) - item["old_len"]
            updated.append(item["doc_id"])

        done = min(start + BATCH_SIZE, len(targets))
        print(f"  {done}/{len(targets)} — atjaunoti {len(updated)}, "
              f"nemainīti {unchanged}, nesasniedzami {missing}, "
              f"dublikāti {duplicate} ({time.time() - t0:.0f}s)")

    if rollback is not None:
        rollback.write("\nCOMMIT;\n")
        rollback.close()
        print(f"\nRollback uzrakstīts: {rollback_path.name} ({len(updated)} rindas)")

    print(f"\nIzgūti: atjaunojami {len(updated)} · nemainīti {unchanged} · "
          f"nesasniedzami {missing}")
    if updated:
        print(f"Vidējais pieaugums: +{grew_total // len(updated)} zīmes/dok.")

    if not apply:
        print("\nDRY RUN — nekas nav rakstīts. Palaid ar --apply.")
        return 0

    if not updated:
        print("Nekas nav atjaunots, linkošana izlaista.")
        return 0

    # Re-link ONLY the rewritten documents. The whole point of the backfill is
    # the politician named past the old cut; without this step the repaired
    # text sits in the database unread.
    print(f"\nPārlinkoju {len(updated)} atjaunotos dokumentus…")
    from src.matcher import link_politicians_to_documents
    linked = link_politicians_to_documents(doc_ids=updated)
    print(f"Dokumenti ar atrastiem politiķiem: {len(linked)}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--limit", type=int, default=None,
                    help="apstrādāt tikai pirmos N dokumentus (pilotam)")
    ap.add_argument("--apply", action="store_true",
                    help="tiešām rakstīt izmaiņas (bez tā — dry run)")
    ap.add_argument("--relink-only", action="store_true",
                    help="neko nefetčot, tikai pārlinkot visus jau salabotos RT dokumentus")
    args = ap.parse_args()
    if args.relink_only:
        ids = repaired_doc_ids()
        print(f"Jau salaboti RT dokumenti: {len(ids)}")
        relink(ids)
        return 0
    return asyncio.run(run(args.limit, args.apply))


if __name__ == "__main__":
    raise SystemExit(main())
