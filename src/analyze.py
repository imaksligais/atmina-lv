"""Dynamic analysis helpers for Claude Code-driven politician analysis.

Provides retrieval and storage functions that Claude Code calls interactively:
  1. get_pending_politicians() — who needs analysis?
  2. get_politician_documents() — what did they say/do?
  3. get_existing_claims() — what do we already know?
  4. save_analysis() — store analysis + claims + detect contradictions
"""

import json
import re
import sys
from datetime import timedelta
from typing import Optional

from src.db import _float_list_to_bytes, get_db, now_lv, now_lv_dt
from src.embeddings import embed_text
from src.tools import (
    store_analysis,
    store_claim,
)
from src.topic_map import normalize_topic

# Phrases that, when present in the extractor's own reasoning, strongly
# indicate the claim is about someone other than the subject politician OR
# that no first-person position exists. Added 2026-04-22 after a batch-drift
# diagnostic found that ~65% of low-confidence saves were docs the isolated
# extractor would correctly mark empty (see
# data/autoresearch/DIAGNOSTIC_SUMMARY.md). The gate is SOFT — we don't drop
# the claim, we prepend a NEEDS_REVIEW marker so @quality-reviewer can
# triage. Hard-dropping would false-positive on legitimate "netiešs citāts"
# (indirect citation) cases where the reasoning describes the quote path
# rather than invalidity.
_INDIRECT_MARKERS_LOWER = (
    "nav paša pozīcij",
    "nav pats formulēj",
    "nevis paša formulēt",
    "pašam nav ekstraktēj",
    "pašam nav pozīcij",
    "tieši nerunā",
    "tieši neizklāsta",
    "does not speak",
    "bare retweet",
    "pure retweet",
    "retvīts bez komentāra",
    "retweet without commentary",
    "tikai pieminē",
    "tikai minē",
    "is not quoted, mentioned",
)

# Negation tokens that, if present in the ~30-char window BEFORE a marker,
# indicate the extractor is denying the marker condition (e.g.
# "(nav bare retweet)" — the reasoning says it is NOT a bare retweet).
# 2026-04-23: added after #11286 false-positive where literal substring
# "bare retweet" inside "(nav bare retweet)" tripped the gate even though
# the extractor was explicitly negating it.
_NEGATIONS_BEFORE = (
    "nav ",
    "nevis ",
    "ne ir ",
    "neizskatās ",
    "nesatur ",
    "not ",
    "is not ",
    "isn't ",
    "doesn't ",
    "does not ",
)

# Negations that only count when they DIRECTLY abut the marker (the window
# ends with them). The Latvian "ne tikai / ne vien" ("not only") construction
# sits immediately before the marker: "ne tikai pieminēts" = NOT ONLY mentioned
# → the politician IS the speaker. A bare "ne " is too common to match anywhere
# in the 30-char window (would over-suppress), so we only treat it as a negation
# when it touches the marker. 2026-06-02 fix after "ne tikai pieminēts"
# false-tripped "tikai pieminē" twice (Kleinbergs, Rinkēvičs).
_NEGATIONS_ABUT = ("ne ",)

# Each marker is matched as a stem at a LEFT word boundary (Unicode-aware, so
# Latvian diacritics count as word chars). The right side stays open so the
# stem still matches inflections (e.g. "nav paša pozīcij" → "...pozīcijas").
# `(?<!\w)` stops a marker matching as a word-internal substring — e.g.
# "tikai minē" must not match inside "kritikai minēšana".
_MARKER_RES = tuple(
    (marker, re.compile(r"(?<!\w)" + re.escape(marker)))
    for marker in _INDIRECT_MARKERS_LOWER
)


def _indirect_marker_in(reasoning: str) -> str | None:
    """Return the first NON-NEGATED indirect-reference marker, else None.

    Markers match as stems at a left word boundary (``_MARKER_RES``). A match
    is skipped if a negation token from ``_NEGATIONS_BEFORE`` appears within 30
    chars before it (e.g. "(nav bare retweet)"), or if a ``_NEGATIONS_ABUT``
    token directly precedes it (e.g. "ne tikai pieminēts"). Lexical, not
    semantic; covers the common explicit-denial cases only.
    """
    if not reasoning:
        return None
    low = reasoning.lower()
    for marker, rx in _MARKER_RES:
        for match in rx.finditer(low):
            window = low[max(0, match.start() - 30): match.start()]
            if any(neg in window for neg in _NEGATIONS_BEFORE):
                continue
            if window.endswith(_NEGATIONS_ABUT):
                continue
            return marker
    return None


def mark_documents_reviewed(doc_ids: list[int], db=None) -> int:
    """Mark documents as reviewed (with or without claims). Returns count updated.

    ``db`` is an optional externally-managed connection — when provided, the
    function reuses it and does NOT commit or close, letting the caller run
    this as part of a larger atomic transaction (see ``save_analysis``).
    """
    if not doc_ids:
        return 0
    owns_connection = db is None
    if owns_connection:
        db = get_db()
    try:
        now = now_lv()
        placeholders = ",".join("?" for _ in doc_ids)
        cur = db.execute(
            f"UPDATE documents SET reviewed_at = ? WHERE id IN ({placeholders}) AND reviewed_at IS NULL",
            [now] + doc_ids,
        )
        updated = cur.rowcount
        if owns_connection:
            db.commit()
        return updated
    finally:
        if owns_connection:
            db.close()


def get_pending_politicians(days: int = 1) -> list[dict]:
    """Return politicians that have truly actionable documents for analysis.

    A politician is "pending" iff there exists at least one document where:
      - the junction role is 'subject' (the politician is the document's subject,
        not merely mentioned or a mention target)
      - ``documents.reviewed_at IS NULL`` (not yet human-reviewed)
      - ``documents.scraped_at`` is within the ``days`` window
      - the politician's ``relationship_type`` is not 'inactive' (excludes
        sentinel entries like 'Nepareizais' or 'Kas Notiek Latvijā')

    Each entry: {id, name, party, role, relationship_type, doc_count,
    last_analyzed}. Sorted by doc_count descending.

    History note: earlier versions of this query ignored ``reviewed_at`` and
    ``role='subject'``, causing a ~100% false-positive rate — politicians kept
    appearing as pending even after their subject docs had been processed, and
    sentinel entities were counted as work. See ``get_politician_documents``
    for the downstream filter that this now mirrors.
    """
    db = get_db()
    cutoff = (now_lv_dt() - timedelta(days=days)).isoformat()

    # platform='vestnesis' rows are excluded from claim-extractor queue
    # (added 2026-05-06 after SA-3 batch found 24/33 docs procedural ministerial
    # signatures with no first-party position). Vestnesis content reaches
    # `wiki/log-ingest` and the brief's "Šodien izsludināts" section via
    # document_politicians junction; the rare substantive cases (Saeimas
    # stenogrammas with direct citations) must be processed manually.
    rows = db.execute(
        """SELECT tp.id, tp.name, tp.party, tp.role, tp.relationship_type,
                  COUNT(DISTINCT d.id) AS doc_count,
                  (SELECT MAX(created_at) FROM analyses WHERE opponent_id = tp.id)
                      AS last_analyzed
           FROM tracked_politicians tp
           JOIN document_politicians dp
                ON dp.politician_id = tp.id AND dp.role = 'subject'
           JOIN documents d
                ON d.id = dp.document_id
                AND d.reviewed_at IS NULL
                AND d.scraped_at >= ?
                AND d.platform != 'vestnesis'
           WHERE tp.relationship_type != 'inactive'
           GROUP BY tp.id, tp.name, tp.party, tp.role, tp.relationship_type
           HAVING doc_count > 0
           ORDER BY doc_count DESC""",
        (cutoff,),
    ).fetchall()

    db.close()
    return [dict(r) for r in rows]


def get_politician_documents(
    pid: int, days: int = 1, max_results: int = 20
) -> list[dict]:
    """Return recent documents for a politician as structured dicts.

    Each entry: {id, content, source_url, source_domain, platform, language,
                 scraped_at, word_count, is_auto_caption}
    Content is truncated to ~2000 words if very long.
    """
    db = get_db()
    cutoff = (now_lv_dt() - timedelta(days=days)).isoformat()

    # platform='vestnesis' filtered out — see get_pending_politicians comment.
    rows = db.execute(
        """SELECT d.id, d.content, d.source_url, d.source_domain, d.platform, d.language,
                  d.scraped_at, d.published_at, d.word_count, d.is_auto_caption, dp.role
           FROM documents d
           JOIN document_politicians dp ON dp.document_id = d.id
           WHERE dp.politician_id = ? AND d.scraped_at >= ?
           AND d.reviewed_at IS NULL
           AND d.platform != 'vestnesis'
           AND dp.role = 'subject'
           ORDER BY d.scraped_at DESC LIMIT ?""",
        (pid, cutoff, max_results),
    ).fetchall()

    docs = []
    for r in rows:
        d = dict(r)
        # Truncate very long content
        content = d.get("content", "")
        if content and len(content.split()) > 2000:
            words = content.split()
            d["content"] = " ".join(words[:2000])
            d["truncated"] = True
            d["total_words"] = len(words)
        docs.append(d)

    db.close()
    return docs


def get_existing_claims(
    pid: int,
    days: int = 90,
    claim_types: Optional[tuple[str, ...]] = ("position", "commentary"),
) -> list[dict]:
    """Return recent claims for a politician (feeds extractor-agent context).

    Each entry: {id, topic, stance, quote, confidence, salience, stated_at,
    source_url, claim_type}

    ``claim_types`` filters the returned rows by ``claim_type``. The default
    ``("position", "commentary")`` EXCLUDES ``saeima_vote``: the ~520k-row
    Saeima vote corpus (2026-05-27 bulk import) all has ``created_at`` inside
    any reasonable ``days`` window, so vote-heavy politicians would otherwise
    return thousands of rows (~98% vote noise) into every claim-extractor
    subagent's context. Contradiction detection against votes runs separately
    via ``search_similar_claims`` with its own ``claim_type_filter`` — this
    function only supplies the "what do we already know" context list. Pass
    ``claim_types=None`` to return ALL claim types (legacy behavior).
    """
    db = get_db()
    cutoff = (now_lv_dt() - timedelta(days=days)).isoformat()

    sql = (
        "SELECT id, topic, stance, quote, confidence, salience, stated_at, "
        "source_url, claim_type "
        "FROM claims WHERE opponent_id = ? AND created_at >= ?"
    )
    params: list = [pid, cutoff]
    if claim_types is not None:
        placeholders = ",".join("?" for _ in claim_types)
        sql += f" AND claim_type IN ({placeholders})"
        params.extend(claim_types)
    sql += " ORDER BY stated_at DESC, created_at DESC"

    rows = db.execute(sql, params).fetchall()

    db.close()
    return [dict(r) for r in rows]


def save_analysis(
    pid: int,
    analysis_date: str,
    sentiment: float,
    topics: list[str],
    quotes: list[str],
    brief: str,
    confidence: float,
    claims: Optional[list[dict]] = None,
    position_shifts: Optional[dict] = None,
    empty_doc_ids: Optional[list[int]] = None,
) -> dict:
    """Store analysis + claims + detect contradictions. Single call to do it all.

    Args:
        pid: politician ID
        analysis_date: ISO date string (e.g. "2026-03-26")
        sentiment: deprecated — always pass 0.0 (sentiment analysis removed)
        topics: list of key topic strings
        quotes: list of notable quote strings
        brief: markdown analysis text
        confidence: 0.0 to 1.0
        claims: list of claim dicts, each with keys:
            document_id, topic, stance, quote (optional), confidence, reasoning,
            salience, source_url (optional)
        position_shifts: optional dict of position changes
        empty_doc_ids: optional list of document IDs the analyst looked at
            but judged empty (ceremonial, duplicate, off-topic, third-party
            only). These are marked reviewed alongside claim-bearing docs,
            which prevents them from reappearing in the backlog on the next
            routine run. Required whenever the analyst wants to say "I read
            this doc and there is nothing to extract"; previously the daily-
            routine docs suggested `save_analysis(claims=[])` for that case,
            but the old code never actually marked anything reviewed without
            a claims entry (2026-04-10 backlog audit finding).

    Returns:
        dict with analysis_id, claim_ids, contradiction_ids, failures,
        and status ("success" | "partial")
    """
    # Store the analysis
    analysis_json = json.dumps({
        "sentiment_score": sentiment,
        "key_topics": topics,
        "notable_quotes": quotes,
        "position_shifts": position_shifts,
        "brief_markdown": brief,
        "confidence": confidence,
    }, ensure_ascii=False)

    failures: list[dict] = []
    claim_ids: list[int] = []
    contradiction_ids: list[int] = []
    analysis_id = None

    # Collect document IDs to mark reviewed: any doc that contributed a claim,
    # plus any doc the caller explicitly flagged as empty. The old code only
    # collected from claims, so docs judged "ceremonial" reappeared in the
    # backlog every day — the 2026-04-10 audit traced the bogus 209 "backlog"
    # to this.
    reviewed_doc_ids: set[int] = set()
    if claims:
        reviewed_doc_ids.update(
            c["document_id"] for c in claims if c.get("document_id")
        )
    if empty_doc_ids:
        reviewed_doc_ids.update(int(d) for d in empty_doc_ids)

    # S10 atomicity: own a single connection and wrap the whole analysis +
    # claims + reviewed-docs update in one transaction. If anything raises
    # mid-batch, the ``with db:`` context manager rolls back and no half-saved
    # state persists. Individual claim-level skips (missing source_url,
    # store_claim returning status='error') are recorded in ``failures`` and
    # do NOT raise — they remain best-effort drops so one bad claim doesn't
    # nuke the whole batch. The transaction rollback only triggers on truly
    # unexpected exceptions (DB lock timeout, schema error, disk full, etc.)
    # that would otherwise leave mixed state across analyses/claims/documents.
    db = get_db()
    try:
        # Precompute claim embeddings BEFORE the write transaction. store_claim
        # otherwise computes an e5-small embedding (100ms-10s) per claim UNDER
        # the single ``with db:`` write lock held across the whole batch,
        # summing N embedding costs into the lock-hold window and blowing past
        # the 30s busy_timeout under parallel extraction fan-out ("database is
        # locked"). The connection is open here but no transaction has begun,
        # so no lock is held. Inside the try so a malformed claim dict (missing
        # topic/stance) still returns the structured status="failed" response
        # instead of raising. The embedded text MUST be byte-identical to
        # db.store_claim's internal computation, which embeds
        # ``f"{topic}: {stance}"`` where ``topic`` has already passed through
        # normalize_topic (applied in tools.store_claim) and the pydantic Claim
        # model. The Claim model does NOT transform topic/stance (no
        # validators, no str-strip config), so replicating the normalization is
        # sufficient. See BACKLOG.md § "SQLite write contention".
        precomputed_embeddings: list[bytes] = []
        if claims:
            for c in claims:
                norm_topic = normalize_topic(c["topic"])
                precomputed_embeddings.append(
                    _float_list_to_bytes(embed_text(f"{norm_topic}: {c['stance']}"))
                )

        with db:
            analysis_result = json.loads(
                store_analysis(pid, analysis_date, analysis_date, analysis_json, db=db)
            )
            analysis_id = analysis_result.get("analysis_id")
            if analysis_id is None:
                err = analysis_result.get("message", "unknown store_analysis error")
                failures.append({
                    "type": "store_analysis_failed",
                    "opponent_id": pid,
                    "analysis_date": analysis_date,
                    "error": err,
                })
                print(
                    f"[save_analysis] store_analysis failed for pid={pid} "
                    f"date={analysis_date}: {err}",
                    file=sys.stderr,
                )

            if claims:
                # Always derive source_url from the claim's document — never
                # trust the caller's source_url field. Earlier extractor
                # sessions occasionally passed hallucinated or truncated URLs
                # (e.g. profile URL instead of status URL, scheme-stripped
                # paths, fake status IDs ending in zeros), which caused 121
                # claim/document URL drifts in production. The document is
                # the authoritative source — its URL was set at ingest time
                # and is stable. See post-launch debt resolution log.
                doc_url_cache: dict[int, str | None] = {}

                for idx, c in enumerate(claims):
                    doc_id = c["document_id"]
                    if doc_id not in doc_url_cache:
                        row = db.execute(
                            "SELECT source_url FROM documents WHERE id = ?",
                            (doc_id,),
                        ).fetchone()
                        doc_url_cache[doc_id] = row["source_url"] if row else None
                    source_url = doc_url_cache[doc_id]

                    if not source_url:
                        # Skip claims without any source URL — record as a
                        # failure so callers see that the claim was dropped
                        # instead of silently losing it in claim_ids.
                        failures.append({
                            "type": "missing_source_url",
                            "opponent_id": pid,
                            "document_id": doc_id,
                            "topic": c.get("topic"),
                            "error": "document has no source_url; claim dropped",
                        })
                        print(
                            f"[save_analysis] dropping claim pid={pid} "
                            f"doc={doc_id} topic={c.get('topic')!r}: "
                            f"document has no source_url",
                            file=sys.stderr,
                        )
                        continue

                    reasoning = c.get("reasoning", "")
                    marker = _indirect_marker_in(reasoning)
                    if marker:
                        # Prepend NEEDS_REVIEW tag so @quality-reviewer sees
                        # the flag during triage; do not drop the claim — a
                        # false-positive hard-drop would kill legitimate
                        # saves where "netiešs citāts" just describes the
                        # quote path. See DIAGNOSTIC_SUMMARY.md.
                        reasoning = (
                            f"NEEDS_REVIEW: reasoning contains indirect-reference "
                            f"phrase {marker!r}; verify subject politician is "
                            f"actually the speaker before publishing. "
                            f"Original reasoning: {reasoning}"
                        )
                        print(
                            f"[save_analysis] indirect-reference gate tripped "
                            f"pid={pid} doc={doc_id} marker={marker!r}",
                            file=sys.stderr,
                        )

                    claim_result = json.loads(store_claim(
                        opponent_id=pid,
                        document_id=c["document_id"],
                        topic=c["topic"],
                        stance=c["stance"],
                        quote=c.get("quote"),
                        confidence=c.get("confidence", 0.5),
                        reasoning=reasoning,
                        salience=c.get("salience", 0.5),
                        source_url=source_url,
                        stated_at=c.get("stated_at"),
                        claim_type=c.get("claim_type", "position"),
                        speaker_id=c.get("speaker_id"),
                        party_id=c.get("party_id"),
                        embedding_bytes=precomputed_embeddings[idx],
                        db=db,
                    ))
                    new_claim_id = claim_result.get("claim_id")
                    if new_claim_id:
                        claim_ids.append(new_claim_id)

                        # Contradiction detection placeholder. Claude Code
                        # analyzes the similar-claims list and calls
                        # store_contradiction directly; nothing to persist
                        # here. (Kept as a hook for future in-process detection.)
                        if c.get("confidence", 0.5) >= 0.6:
                            pass
                    else:
                        # store_claim returned no claim_id — surface the
                        # error instead of silently dropping it. Prior to
                        # 2026-04-10 these failures were invisible to
                        # callers and only caught by post-hoc DB diffing.
                        err = claim_result.get("message", "unknown store_claim error")
                        failures.append({
                            "type": "store_claim_failed",
                            "opponent_id": pid,
                            "document_id": doc_id,
                            "topic": c.get("topic"),
                            "error": err,
                        })
                        print(
                            f"[save_analysis] store_claim failed pid={pid} "
                            f"doc={doc_id} topic={c.get('topic')!r}: {err}",
                            file=sys.stderr,
                        )

            # Mark reviewed documents (inside the same transaction)
            if reviewed_doc_ids:
                mark_documents_reviewed(list(reviewed_doc_ids), db=db)
        # ``with db:`` has committed at this point. If any exception bubbled
        # out of the block it has already rolled back the whole transaction
        # and ``failures`` / ``claim_ids`` from this call are no longer
        # persisted — the except clause below converts that to a structured
        # failure response.
    except Exception as e:
        # Catastrophic failure: DB write error, lock timeout, disk full, etc.
        # The ``with db:`` context already rolled back; we surface a single
        # structured failure and clear any IDs we thought we had (since they
        # were rolled back).
        print(
            f"[save_analysis] transaction rolled back for pid={pid} "
            f"date={analysis_date}: {e}",
            file=sys.stderr,
        )
        return {
            "status": "failed",
            "analysis_id": None,
            "claim_ids": [],
            "contradiction_ids": [],
            "failures": [
                *failures,
                {
                    "type": "transaction_rolled_back",
                    "opponent_id": pid,
                    "analysis_date": analysis_date,
                    "error": str(e),
                },
            ],
        }
    finally:
        db.close()

    return {
        "status": "partial" if failures else "success",
        "analysis_id": analysis_id,
        "claim_ids": claim_ids,
        "contradiction_ids": contradiction_ids,
        "failures": failures,
    }
