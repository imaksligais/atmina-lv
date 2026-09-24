"""Backfill truncated web documents — re-fetch the full text in place.

Scope (backlog/avoti.md § "lsm/diena/tvnet truncated doku backfill", measured
2026-09-23): ~2 678 ``documents`` rows with ``platform='web' AND word_count <
90`` (lsm 1078, diena 805, tvnet 451, nra 168, …), ~170 of them carrying
claims. The stored text is an extraction stub — RSS fetched only the lead —
while the live article is full-length. Re-fetching restores coverage AND makes
the junction rows checkable again (truncated text left names unverifiable —
doc-42838 class, T19).

Per document, in order:

  1. fetch via ``scripts.ingest_url._default_fetch`` (soft-404 guard +
     trafilatura default/recall variants already inside); ≥1 s between
     requests to the same domain; a failing URL is classified, never raised.
  2. accept ONLY when ALL hold: fetch produced text; not a soft-404;
     ``new_words > old_words * 1.5 AND new_words >= old_words + 40``; and the
     same-story proof (``_same_story``): the stored lede's first ~25 words
     appear in the new text, OR the fetched headline equals the stored one
     (site suffix stripped). Otherwise ``different_story`` — the doc-72446
     class — and the row is never overwritten. With a headline-only proof the
     stub is kept in front of the body (``_compose``) so the lede survives.
  3. write through ``insert_document``'s same-URL UPDATE branch with
     ``preserve_scraped_at=True`` — the doc keeps its historic day bucket
     while ``reviewed_at`` resets (the new text re-enters extraction) and
     ``_reconcile_junction_suspects`` flags junction rows the new text no
     longer justifies (flag, never delete — T19). The write is verified
     afterwards; a refused/unchanged row is ``update_failed``, not success.

Default is DRY-RUN: nothing is written. ``--apply`` requires
``--rollback-out PATH``; each accepted doc's rollback SQL (prior ``documents``
fields plus prior ``document_politicians.suspect_at``) is flushed+fsynced
before that doc's UPDATE, so a crash mid-run never leaves an unrollbackable
write.

Deliberately NOT done here: re-chunking/re-embedding of the new text is a
separate step — this script only repairs ``documents.content`` and reports
which updated docs carry claims (those need re-extraction).

Usage:
    python scripts/backfill_truncated_docs.py --report out.jsonl          # dry-run
    python scripts/backfill_truncated_docs.py --report out.jsonl --apply \
        --rollback-out data/rollback_truncated_backfill_YYYY-MM-DD.sql
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Callable, Optional
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.db import DB_PATH, get_db, insert_document, now_lv  # noqa: E402
import scripts.ingest_url as ingest_url  # noqa: E402

# Accept thresholds: the new text must be BOTH >1.5x the stored word count
# AND at least 40 words longer — a re-extraction of the same stub passes
# neither, a full article passes both.
GROWTH_RATIO = 1.5
GROWTH_MIN_WORDS = 40
# Same-story proof: this many normalized words of the OLD text must appear in
# the new one. 25 words is long enough that a different article cannot share
# the prefix by accident, short enough to survive a re-paragraphing.
PROBE_WORDS = 25
# Politeness: minimum seconds between two requests to the same domain.
MIN_INTERVAL_S = 1.0


def _domain_of(url: str) -> str:
    return urlparse(url).netloc.lower().removeprefix("www.")


def _norm(text: Optional[str]) -> str:
    return " ".join(html.unescape(text or "").lower().split())


# Site-name suffixes that <title> carries and documents.title does not
# (measured 2026-09-23 dry-run: diena "… — Diena", lsm "… / Raksts").
_TITLE_SUFFIX_RE = re.compile(
    r"(?:\s*[—–|/-]\s*(?:diena|raksts|nra\.lv|lsm\.lv|tvnet(?:\.lv)?|"
    r"delfi(?:\.lv)?|la\.lv|jauns\.lv))+\s*$",
    re.IGNORECASE,
)
# RSS-path stubs are stored as "<headline> — <RSS lede>".
_STUB_SEP = " — "


def _norm_title(title: Optional[str]) -> str:
    return _norm(_TITLE_SUFFIX_RE.sub("", html.unescape(title or "")))


def _stub_parts(old_content: Optional[str]) -> tuple[Optional[str], str]:
    """(headline, lede) of a stored RSS stub; (None, whole text) otherwise."""
    old = old_content or ""
    if _STUB_SEP in old:
        head, lede = old.split(_STUB_SEP, 1)
        return head, lede
    return None, old


def _same_story(row, new_text: str, new_title: Optional[str]) -> Optional[str]:
    """Proof that the fetched page is the SAME article, or None.

    ``'lede'``  — the stored lede's first PROBE_WORDS words are inside the
    new text (the new text already carries everything the stub had).
    ``'title'`` — the fetched headline equals the stored title or the stub's
    headline after stripping the site suffix. Needed because trafilatura
    routinely DROPS the lede on lsm.lv/diena.lv (2026-09-23 dry-run: 49/50
    failed the lede-only proof, 45 of them matched by title). A headline the
    publisher rewrote (Rosļikovs "pametis partiju" → "pamet … amatu") does
    NOT match — that is a changed fact, stop beats write.
    An empty probe proves nothing (T19).
    """
    head, lede = _stub_parts(row["content"])
    probe = " ".join(_norm(lede).split()[:PROBE_WORDS])
    if probe and probe in _norm(new_text):
        return "lede"
    nt = _norm_title(new_title)
    if nt and nt in {_norm_title(row["title"]), _norm_title(head)}:
        return "title"
    return None


def _compose(old_content: str, new_text: str, proof: str) -> str:
    """Content to store. With a title-only proof the fetched body lacks the
    stored lede, so the stub is KEPT in front of it — replacing would delete
    the lede (often the key quote) that claims may cite."""
    if proof == "lede":
        return new_text
    return old_content.rstrip() + "\n\n" + new_text


def _is_longer(new_words: int, old_words: int) -> bool:
    return (new_words > old_words * GROWTH_RATIO
            and new_words >= old_words + GROWTH_MIN_WORDS)


def select_candidates(
    db,
    *,
    max_words: int = 90,
    domain: Optional[str] = None,
    ids: Optional[list[int]] = None,
    limit: Optional[int] = None,
    include_paywall: bool = False,
) -> list:
    """Documents eligible for re-fetch. Docs WITH claims first, then id —
    those are the ones whose claims point at a stub."""
    where = [
        "d.platform = 'web'",
        "d.word_count IS NOT NULL",
        "d.word_count < ?",
        "d.source_url IS NOT NULL",
        "d.source_url != ''",
    ]
    params: list = [max_words]
    if domain:
        dom = domain.lower().removeprefix("www.")
        # source_domain is the stored netloc — may or may not carry www.
        where.append("lower(d.source_domain) IN (?, ?)")
        params += [dom, f"www.{dom}"]
    if ids is not None:
        if not ids:
            return []
        where.append("d.id IN (" + ",".join("?" * len(ids)) + ")")
        params += list(ids)
    if not include_paywall:
        where.append("COALESCE(d.is_paywall, 0) = 0")
    sql = f"""
        SELECT d.*, EXISTS(SELECT 1 FROM claims c WHERE c.document_id = d.id)
               AS had_claims
        FROM documents d
        WHERE {" AND ".join(where)}
        ORDER BY had_claims DESC, d.id
    """
    if limit:
        sql += " LIMIT ?"
        params.append(limit)
    return db.execute(sql, params).fetchall()


def _count_paywall_skipped(db, *, max_words, domain, ids) -> int:
    """Denominator honesty: how many otherwise-eligible rows the paywall
    filter excluded."""
    rows = select_candidates(
        db, max_words=max_words, domain=domain, ids=ids,
        limit=None, include_paywall=True,
    )
    return sum(1 for r in rows if r["is_paywall"])


class _DomainPacer:
    """≥ MIN_INTERVAL_S between requests to the same domain (www-folded)."""

    def __init__(
        self,
        min_interval: float = MIN_INTERVAL_S,
        sleep_fn: Callable[[float], None] = time.sleep,
        now_fn: Callable[[], float] = time.monotonic,
    ):
        self._min = min_interval
        self._sleep = sleep_fn
        self._now = now_fn
        self._last: dict[str, float] = {}

    def wait(self, domain: str) -> None:
        prev = self._last.get(domain)
        if prev is not None:
            gap = self._now() - prev
            if gap < self._min:
                self._sleep(self._min - gap)
        self._last[domain] = self._now()


def _sql_lit(v) -> str:
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, (int, float)):
        return repr(v)
    return "'" + str(v).replace("'", "''") + "'"


class _RollbackWriter:
    """Appends restore statements; each doc's block is flushed+fsynced before
    its UPDATE, so an interrupted run is still fully revertible."""

    def __init__(self, path: str):
        self._fh = open(path, "w", encoding="utf-8", newline="\n")
        self._fh.write(
            "-- Rollback: scripts/backfill_truncated_docs.py --apply, "
            f"run {now_lv()[:10]}\n"
            "-- Forward change: documents.content/content_hash/simhash/"
            "word_count/title/\n"
            "--   published_at/source_domain replaced by the re-fetched full "
            "text via\n"
            "--   insert_document's same-URL UPDATE (reviewed_at cleared; "
            "scraped_at\n"
            "--   preserved). document_politicians.suspect_at flags written by\n"
            "--   _reconcile_junction_suspects are restored per junction row.\n\n"
        )
        self._fsync()

    def _fsync(self) -> None:
        self._fh.flush()
        os.fsync(self._fh.fileno())

    def add_document(self, row, junction_rows) -> None:
        """Emit the restore for one doc's prior values. `row` is the
        documents row BEFORE the update; `junction_rows` its (document_id,
        politician_id, role, suspect_at) junction rows BEFORE the update."""
        cols = ("content", "content_hash", "simhash", "word_count",
                "scraped_at", "reviewed_at", "title", "published_at",
                "source_domain")
        sets = ", ".join(f"{c} = {_sql_lit(row[c])}" for c in cols)
        self._fh.write(
            f"UPDATE documents SET {sets} WHERE id = {row['id']};\n"
        )
        for j in junction_rows:
            self._fh.write(
                "UPDATE document_politicians "
                f"SET suspect_at = {_sql_lit(j['suspect_at'])} "
                f"WHERE document_id = {j['document_id']} "
                f"AND politician_id = {j['politician_id']} "
                f"AND role = {_sql_lit(j['role'])};\n"
            )
        self._fh.write("\n")
        self._fsync()

    def add_relinked(self, rows) -> None:
        """Emit DELETEs for junction rows the post-rewrite relink ADDED.
        Written after every doc's restore block, so a full replay restores the
        texts first and then removes the links the new texts produced."""
        if not rows:
            return
        self._fh.write("-- Junction rows added by the post-rewrite relink "
                       "(link_politicians_to_documents(doc_ids=...)):\n")
        for did, pid, role in rows:
            self._fh.write(
                "DELETE FROM document_politicians "
                f"WHERE document_id = {did} AND politician_id = {pid} "
                f"AND role = {_sql_lit(role)};\n"
            )
        self._fsync()

    def close(self) -> None:
        self._fh.close()


def _resolve_link_fn(db_path, link_fn):
    """The relink callable for this run, or None.

    ``link_politicians_to_documents`` always writes the PRODUCTION database
    (it opens ``get_db()`` and matches with the cached live name forms), so it
    is the default only when the run targets the live DB. Any other path gets
    no implicit relink — it must inject ``link_fn`` — rather than silently
    writing junctions into production.
    """
    if link_fn is not None:
        return link_fn
    if os.path.abspath(str(db_path)) != os.path.abspath(str(DB_PATH)):
        return None
    from src.matcher import link_politicians_to_documents

    def _live(doc_ids):
        return link_politicians_to_documents(doc_ids=doc_ids)
    _live.__wrapped_matcher__ = link_politicians_to_documents
    return _live


def _junction_set(db_path, doc_ids) -> set[tuple[int, int, str]]:
    if not doc_ids:
        return set()
    db = get_db(db_path)
    rows = db.execute(
        "SELECT document_id, politician_id, role FROM document_politicians "
        f"WHERE document_id IN ({','.join('?' * len(doc_ids))})",
        tuple(doc_ids),
    ).fetchall()
    db.close()
    return {(r[0], r[1], r[2]) for r in rows}


def _default_backfill_fetch(url: str) -> Optional[dict]:
    """The real fetch: ingest_url._default_fetch, with the soft-404 class
    recovered from its _LAST_FETCH_ERROR (a bare None cannot tell a dead
    article from a network failure)."""
    parsed = ingest_url._default_fetch(url)
    if parsed is not None:
        return parsed
    err = ingest_url._LAST_FETCH_ERROR or ""
    if err.startswith("soft_404:"):
        return {"soft_404": err}
    return None


def read_ids_file(path: str) -> list[int]:
    """One document id per line; blanks and `#` comments skipped."""
    ids: list[int] = []
    for n, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            ids.append(int(line))
        except ValueError:
            print(f"  SKIP bad ids line {n}: {line!r}", file=sys.stderr)
    return ids


def _apply_one(db_path, row, parsed, new_text, new_words, insert_fn, rollback):
    """Write one accepted doc through insert_document's UPDATE branch and
    verify it landed. Returns (class, suspects_flagged)."""
    # Rollback first: the restore block for THIS doc must be on disk before
    # its UPDATE runs.
    db = get_db(db_path)
    junction_rows = db.execute(
        "SELECT document_id, politician_id, role, suspect_at "
        "FROM document_politicians WHERE document_id = ?",
        (row["id"],),
    ).fetchall()
    db.close()
    rollback.add_document(row, junction_rows)

    try:
        new_id = insert_fn(
            content=new_text,
            source_id=row["source_id"],
            platform="web",
            language=row["language"] or "lv",
            source_url=row["source_url"],
            published_at=parsed.get("published_at"),
            title=parsed.get("title"),
            preserve_scraped_at=True,
            db_path=db_path,
        )
    except Exception as e:  # noqa: BLE001 — a failed write is one doc's class
        print(f"  ERR update doc {row['id']}: {e}", file=sys.stderr)
        return "update_failed", None

    # stored-count == intended-count: a refused (None) or silently unchanged
    # write is a reported failure, not a success.
    db = get_db(db_path)
    chk = db.execute(
        "SELECT content, word_count FROM documents WHERE id = ?", (row["id"],)
    ).fetchone()
    if new_id == row["id"] and chk and chk["content"] == new_text \
            and chk["word_count"] == new_words:
        flagged = db.execute(
            "SELECT COUNT(*) c FROM document_politicians "
            "WHERE document_id = ? AND suspect_at IS NOT NULL",
            (row["id"],),
        ).fetchone()["c"]
        db.close()
        return "updated", flagged
    db.close()
    return "update_failed", None


def run_backfill(
    *,
    db_path: str = DB_PATH,
    fetch_fn: Optional[Callable[[str], Optional[dict]]] = None,
    max_words: int = 90,
    domain: Optional[str] = None,
    ids: Optional[list[int]] = None,
    limit: Optional[int] = None,
    include_paywall: bool = False,
    apply: bool = False,
    rollback_path: Optional[str] = None,
    report_path: Optional[str] = None,
    sleep_fn: Callable[[float], None] = time.sleep,
    now_fn: Callable[[], float] = time.monotonic,
    insert_fn: Callable[..., Optional[int]] = insert_document,
    link_fn: Optional[Callable[[list[int]], object]] = None,
) -> dict:
    """Re-fetch every selected doc; classify each; write only on --apply.

    fetch_fn contract: ``url -> dict | None``. A dict carries ``text`` /
    ``title`` / ``published_at`` like ingest_url's; ``{"soft_404": reason}``
    marks the soft-404 class; None or missing/empty text is a fetch error.
    Returns a summary dict whose `records` list is the per-doc JSONL payload.
    """
    if apply and not rollback_path:
        raise ValueError("apply requires rollback_path — the rollback SQL "
                         "must exist before the first UPDATE")
    fetch = fetch_fn or _default_backfill_fetch

    db = get_db(db_path)
    candidates = select_candidates(
        db, max_words=max_words, domain=domain, ids=ids,
        limit=limit, include_paywall=include_paywall,
    )
    paywall_skipped = (
        _count_paywall_skipped(db, max_words=max_words, domain=domain, ids=ids)
        if not include_paywall else 0
    )
    db.close()

    pacer = _DomainPacer(sleep_fn=sleep_fn, now_fn=now_fn)
    report_fh = (
        open(report_path, "w", encoding="utf-8", newline="\n")
        if report_path else None
    )
    rollback: Optional[_RollbackWriter] = None
    junctions_added = 0
    counts: dict[str, int] = {}
    records: list[dict] = []
    try:
        for row in candidates:
            url = row["source_url"]
            dom = _domain_of(url)
            rec = {
                "doc_id": row["id"], "url": url, "domain": dom,
                "old_words": row["word_count"], "new_words": None,
                "class": None, "had_claims": bool(row["had_claims"]),
                "suspects_flagged": None, "proof": None,
            }

            pacer.wait(dom)
            try:
                parsed = fetch(url)
            except Exception as e:  # noqa: BLE001 — one bad URL never stops the run
                print(f"  ERR fetch {url[:80]}: {e}", file=sys.stderr)
                parsed = None

            if isinstance(parsed, dict) and parsed.get("soft_404"):
                rec["class"] = "soft_404"
            else:
                new_text = parsed.get("text") if isinstance(parsed, dict) else ""
                new_text = new_text or ""
                if not new_text.strip():
                    rec["class"] = "fetch_error"
                else:
                    counts["fetched_ok"] = counts.get("fetched_ok", 0) + 1
                    new_words = len(new_text.split())
                    rec["new_words"] = new_words
                    if not _is_longer(new_words, row["word_count"]):
                        rec["class"] = "not_longer"
                    elif not (proof := _same_story(
                            row, new_text, parsed.get("title"))):
                        rec["class"] = "different_story"
                    else:
                        rec["proof"] = proof
                        content = _compose(row["content"], new_text, proof)
                        if not apply:
                            rec["class"] = "would_update"
                        else:
                            if rollback is None:
                                rollback = _RollbackWriter(rollback_path)
                            rec["class"], rec["suspects_flagged"] = _apply_one(
                                db_path, row, parsed, content,
                                len(content.split()), insert_fn, rollback,
                            )
            counts[rec["class"]] = counts.get(rec["class"], 0) + 1
            records.append(rec)
            if report_fh:
                report_fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                report_fh.flush()

        # Relink the rewritten docs (2026-09-23). The UPDATE branch merges only
        # the caller's politician_links — none are passed above — and the
        # morning backstop scans only docs with NO junction rows, so a speaker
        # named only in the full text was never linked (batch 2: 24 pairs).
        updated_ids = [r["doc_id"] for r in records if r["class"] == "updated"]
        relink = _resolve_link_fn(db_path, link_fn) if apply else None
        if updated_ids and relink is not None:
            before = _junction_set(db_path, updated_ids)
            relink(updated_ids)
            added = sorted(_junction_set(db_path, updated_ids) - before)
            # A doc that already had a subject gets new pids as 'mentioned':
            # a subject role needs speaker evidence, and a full text that
            # merely NAMES someone is not that (first relink: 82 such rows).
            had_subject = {d for d, _p, r in before if r == "subject"}
            demote = [(d, p) for d, p, r in added
                      if r == "subject" and d in had_subject]
            if demote:
                db = get_db(db_path)
                db.executemany(
                    "UPDATE document_politicians SET role = 'mentioned' "
                    "WHERE document_id = ? AND politician_id = ? "
                    "AND role = 'subject'", demote)
                db.commit()
                db.close()
                added = sorted(_junction_set(db_path, updated_ids) - before)
            if rollback is not None:
                rollback.add_relinked(added)
            junctions_added = len(added)
        elif updated_ids and apply:
            print("  NB: relink skipped — non-live db_path and no link_fn",
                  file=sys.stderr)
    finally:
        if report_fh:
            report_fh.close()
        if rollback:
            rollback.close()

    updated_key = "updated" if apply else "would_update"
    return {
        "examined": len(candidates),
        "paywall_skipped": paywall_skipped,
        "fetched_ok": counts.get("fetched_ok", 0),
        "soft_404": counts.get("soft_404", 0),
        "fetch_error": counts.get("fetch_error", 0),
        "not_longer": counts.get("not_longer", 0),
        "different_story": counts.get("different_story", 0),
        updated_key: counts.get(updated_key, 0),
        "update_failed": counts.get("update_failed", 0),
        "junctions_added": junctions_added,
        "claims_docs": [r["doc_id"] for r in records
                        if r["class"] in ("updated", "would_update")
                        and r["had_claims"]],
        "failed_ids": [r["doc_id"] for r in records
                       if r["class"] == "update_failed"],
        "records": records,
    }


def main(argv: Optional[list[str]] = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # Latvian titles
    ap = argparse.ArgumentParser(
        description="Re-fetch truncated web documents in place (dry-run by "
                    "default; --apply writes through insert_document).",
    )
    ap.add_argument("--db", default=DB_PATH, help="DB path (default: live)")
    ap.add_argument("--max-words", type=int, default=90,
                    help="select docs with word_count below this (default 90)")
    ap.add_argument("--domain", help="only this domain (www. prefix ignored)")
    ap.add_argument("--ids-from", metavar="FILE",
                    help="file with document ids, one per line")
    ap.add_argument("--limit", type=int, default=None, help="cap docs examined")
    ap.add_argument("--include-paywall", action="store_true",
                    help="also process is_paywall=1 rows (skipped by default)")
    ap.add_argument("--apply", action="store_true",
                    help="write updates (default: dry-run)")
    ap.add_argument("--rollback-out", metavar="PATH",
                    help="rollback SQL path — REQUIRED with --apply")
    ap.add_argument("--report", metavar="PATH", required=True,
                    help="per-doc JSONL report path")
    args = ap.parse_args(argv)

    if args.apply and not args.rollback_out:
        print("error: --apply requires --rollback-out PATH", file=sys.stderr)
        return 2

    ids = read_ids_file(args.ids_from) if args.ids_from else None
    summary = run_backfill(
        db_path=args.db,
        max_words=args.max_words,
        domain=args.domain,
        ids=ids,
        limit=args.limit,
        include_paywall=args.include_paywall,
        apply=args.apply,
        rollback_path=args.rollback_out,
        report_path=args.report,
    )

    print(
        f"examined={summary['examined']} "
        f"paywall_skipped={summary['paywall_skipped']} "
        f"fetched_ok={summary['fetched_ok']} "
        f"soft_404={summary['soft_404']} "
        f"fetch_error={summary['fetch_error']} "
        f"not_longer={summary['not_longer']} "
        f"different_story={summary['different_story']} "
        f"{'updated' if args.apply else 'would_update'}="
        f"{summary['updated' if args.apply else 'would_update']} "
        f"update_failed={summary['update_failed']} "
        f"junctions_added={summary['junctions_added']}"
    )
    if summary["claims_docs"]:
        print(f"updated docs carrying claims (need re-extraction): "
              f"{summary['claims_docs']}")
    if summary["failed_ids"]:
        print(f"update_failed doc ids: {summary['failed_ids']}")
    if not args.apply:
        print("(dry-run — nekas nav rakstīts; --apply + --rollback-out lai rakstītu)")
    return 2 if summary["examined"] == 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
