import json
from datetime import date, datetime, timedelta
from typing import Optional

from src.db import (
    get_db,
    now_lv_dt,
    search_similar as db_search_similar,
    search_similar_claims as db_search_similar_claims,
    store_claim as db_store_claim,
    store_contradiction as db_store_contradiction,
    today_lv,
)
from src.embeddings import embed_text
from src.models import AnalysisResult, Claim, ContextNote, Contradiction
from src.quality import validate_lv_diacritics
from src.topic_map import normalize_topic


def _json_success(data: dict | None = None) -> str:
    result = {"status": "success"}
    if data:
        result.update(data)
    return json.dumps(result, default=str, ensure_ascii=False)


def _json_error(message: str) -> str:
    return json.dumps({"status": "error", "message": message}, ensure_ascii=False)


def retrieve_context(
    opponent_id: int,
    days: int = 1,
    query: str | None = None,
    max_results: int = 20,
) -> str:
    try:
        db = get_db()
        if query:
            query_vec = embed_text(query)
            results = db_search_similar(query_vec, top_k=max_results, opponent_id=opponent_id)
            # Enrich with document metadata
            docs = []
            seen_doc_ids = set()
            for r in results:
                doc_id = r["document_id"]
                if doc_id in seen_doc_ids:
                    continue
                seen_doc_ids.add(doc_id)
                doc = db.execute(
                    "SELECT * FROM documents WHERE id = ?", (doc_id,)
                ).fetchone()
                if doc:
                    d = dict(doc)
                    d["match_distance"] = r["distance"]
                    d["matched_chunk"] = r["content"]
                    docs.append(d)
        else:
            cutoff = (now_lv_dt() - timedelta(days=days)).isoformat()
            rows = db.execute(
                """SELECT d.* FROM documents d
                   JOIN document_politicians dp ON dp.document_id = d.id
                   WHERE dp.politician_id = ? AND d.scraped_at >= ?
                   ORDER BY d.scraped_at DESC LIMIT ?""",
                (opponent_id, cutoff, max_results),
            ).fetchall()
            docs = [dict(r) for r in rows]

        # Split long documents into ~800-word segments
        for doc in docs:
            content = doc.get("content", "")
            if content and len(content.split()) > 2000:
                words = content.split()
                segments = []
                for i in range(0, len(words), 800):
                    segments.append(" ".join(words[i : i + 800]))
                doc["content_segments"] = segments
                doc["content"] = f"[{len(segments)} segments, use content_segments]"

        db.close()
        return json.dumps(docs, default=str, ensure_ascii=False)
    except Exception as e:
        return _json_error(str(e))


def store_analysis(
    opponent_id: int,
    period_start: str,
    period_end: str,
    analysis_json: str,
    db=None,
) -> str:
    """Insert an analysis row.

    ``db`` is an optional externally-managed connection — when provided, the
    function reuses it and does NOT commit or close. Caller owns the
    transaction lifecycle. Used by ``save_analysis`` to wrap the full
    analysis-plus-claims save in a single atomic transaction.
    """
    try:
        data = json.loads(analysis_json)
        data["opponent_id"] = opponent_id
        data["period_start"] = period_start
        data["period_end"] = period_end
        analysis = AnalysisResult(**data)

        # Diacritic guardrail — refuse stripped Latvian briefs (agent context drift)
        ok, reason = validate_lv_diacritics(analysis.brief_markdown)
        if not ok:
            return _json_error(
                f"brief_markdown failed diacritic validation "
                f"(opponent_id={opponent_id}): {reason}"
            )

        owns_connection = db is None
        if owns_connection:
            db = get_db()
        try:
            db.execute(
                """INSERT INTO analyses (opponent_id, period_start, period_end,
                   sentiment_score, key_topics, notable_quotes, position_shifts,
                   brief_markdown, confidence)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    analysis.opponent_id,
                    str(analysis.period_start),
                    str(analysis.period_end),
                    analysis.sentiment_score,
                    json.dumps(analysis.key_topics, ensure_ascii=False),
                    json.dumps(analysis.notable_quotes, ensure_ascii=False),
                    json.dumps(analysis.position_shifts) if analysis.position_shifts else None,
                    analysis.brief_markdown,
                    analysis.confidence,
                ),
            )
            analysis_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
            if owns_connection:
                db.commit()
            return _json_success({"analysis_id": analysis_id})
        finally:
            if owns_connection:
                db.close()
    except Exception as e:
        return _json_error(str(e))


def get_opponent_summary(opponent_id: int) -> str:
    try:
        db = get_db()
        politician = db.execute(
            "SELECT * FROM tracked_politicians WHERE id = ?", (opponent_id,)
        ).fetchone()
        if not politician:
            db.close()
            return _json_error(f"Politician {opponent_id} not found")

        summary = dict(politician)

        # Recent analyses
        analyses = db.execute(
            """SELECT * FROM analyses WHERE opponent_id = ?
               ORDER BY created_at DESC LIMIT 5""",
            (opponent_id,),
        ).fetchall()
        summary["recent_analyses"] = [dict(a) for a in analyses]

        # Counts
        summary["document_count"] = db.execute(
            "SELECT COUNT(DISTINCT dp.document_id) FROM document_politicians dp WHERE dp.politician_id = ?", (opponent_id,)
        ).fetchone()[0]

        summary["social_account_count"] = db.execute(
            "SELECT COUNT(*) FROM social_accounts WHERE opponent_id = ? AND active = TRUE",
            (opponent_id,),
        ).fetchone()[0]

        summary["claim_count"] = db.execute(
            "SELECT COUNT(*) FROM claims WHERE opponent_id = ?", (opponent_id,)
        ).fetchone()[0]

        summary["contradiction_count"] = db.execute(
            "SELECT COUNT(*) FROM contradictions WHERE opponent_id = ?", (opponent_id,)
        ).fetchone()[0]

        db.close()
        return json.dumps(summary, default=str, ensure_ascii=False)
    except Exception as e:
        return _json_error(str(e))


def get_context_notes(
    opponent_id: int | None = None,
    topic: str | None = None,
) -> str:
    try:
        db = get_db()
        query = "SELECT * FROM context_notes WHERE 1=1"
        params = []

        if opponent_id is not None:
            query += " AND opponent_id = ?"
            params.append(opponent_id)
        if topic is not None:
            query += " AND topic = ?"
            params.append(topic)

        # Filter out expired notes
        query += " AND (expires_at IS NULL OR expires_at >= ?)"
        params.append(today_lv().isoformat())

        query += " ORDER BY created_at DESC"

        rows = db.execute(query, params).fetchall()
        db.close()
        return json.dumps([dict(r) for r in rows], default=str, ensure_ascii=False)
    except Exception as e:
        return _json_error(str(e))


def _validate_brief_structure(content: str, note_type: str) -> None:
    """Validate that a daily/weekly brief has all mandatory sections.

    Raises ValueError with a list of missing elements if validation fails.
    Called before storing daily_brief or weekly_brief notes.
    """
    if note_type == "daily_brief":
        missing = []
        if not content.startswith("# "):
            missing.append("Jāsākas ar '# ' (H1, ne '##')")
        for section in [
            "## Aktīvākie politiķi",
            "## Galvenās tēmas",
            "## Koalīcija vs Opozīcija",
        ]:
            if section not in content:
                missing.append(f"Trūkst sekcija: {section}")
        if "| Politiķis |" not in content:
            missing.append("Trūkst Markdown tabula (| Politiķis |)")
        if len(content) < 4000:
            missing.append(f"Pārāk īss: {len(content)} chars (min 4000)")
        if missing:
            raise ValueError(
                "Dienas pārskats neatbilst formāta prasībām:\n- "
                + "\n- ".join(missing)
            )
    elif note_type == "weekly_brief":
        missing = []
        if not content.startswith("# "):
            missing.append("Jāsākas ar '# ' (H1, ne '##')")
        for section in ["## Nedēļas stāsts", "## Nedēļas galvenās tēmas"]:
            if section not in content:
                missing.append(f"Trūkst sekcija: {section}")
        if len(content) < 3000:
            missing.append(f"Pārāk īss: {len(content)} chars (min 3000)")
        if missing:
            raise ValueError(
                "Nedēļas pārskats neatbilst formāta prasībām:\n- "
                + "\n- ".join(missing)
            )


def store_context_note(
    opponent_id: int | None = None,
    topic: str | None = None,
    note_type: str = "context",
    content: str = "",
    source: str | None = None,
    expires_at: str | None = None,
    visual_brief: dict | None = None,
) -> str:
    try:
        if note_type in ("daily_brief", "weekly_brief"):
            _validate_brief_structure(content, note_type)
            # NEEDS_REVIEW is an internal triage marker for claim reasoning;
            # it must never reach a published brief. Briefs with the marker
            # mean an unreviewed claim leaked into the narrative — operator
            # must triage the underlying claim and rewrite the bullet first.
            if "NEEDS_REVIEW" in content:
                return _json_error(
                    f"brief contains NEEDS_REVIEW marker — triage the "
                    f"underlying claim and rewrite the bullet before storing "
                    f"(note_type={note_type}, topic={topic})"
                )

        # Auto-extract visual_brief from brief content if not provided
        if note_type in ("daily_brief", "weekly_brief") and visual_brief is None:
            from src.briefs import parse_visual_brief
            visual_brief = parse_visual_brief(content)

        note = ContextNote(
            opponent_id=opponent_id,
            topic=topic,
            note_type=note_type,
            content=content,
            source=source,
            expires_at=date.fromisoformat(expires_at) if expires_at else None,
        )

        # Diacritic guardrail — refuse stripped Latvian content
        ok, reason = validate_lv_diacritics(note.content)
        if not ok:
            return _json_error(
                f"content failed diacritic validation "
                f"(note_type={note_type}, topic={topic}): {reason}"
            )

        from src.db import now_lv
        db = get_db()
        vb_json = json.dumps(visual_brief, ensure_ascii=False) if visual_brief else None
        expires_str = str(note.expires_at) if note.expires_at else None

        # UPSERT for daily/weekly briefs: same (note_type, topic) overwrites
        # existing row in-place. Preserves context_notes.id (→ brief_images
        # FK stays valid) and updates created_at to reflect the "Atjaunots"
        # timestamp in the rendered footer. Context-type notes stay
        # INSERT-only per CLAUDE.md invariant #8 (historical accumulation).
        existing_id = None
        if note_type in ("daily_brief", "weekly_brief") and note.topic:
            row = db.execute(
                "SELECT id FROM context_notes WHERE note_type = ? AND topic = ?",
                (note.note_type, note.topic),
            ).fetchone()
            if row:
                existing_id = row[0] if not isinstance(row, dict) else row["id"]

        if existing_id is not None:
            db.execute(
                """UPDATE context_notes
                   SET opponent_id = ?, content = ?, source = ?, expires_at = ?,
                       created_at = ?, visual_brief_json = ?
                   WHERE id = ?""",
                (
                    note.opponent_id,
                    note.content,
                    note.source,
                    expires_str,
                    now_lv(),
                    vb_json,
                    existing_id,
                ),
            )
            note_id = existing_id
        else:
            db.execute(
                """INSERT INTO context_notes (opponent_id, topic, note_type, content, source, expires_at, created_at, visual_brief_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    note.opponent_id,
                    note.topic,
                    note.note_type,
                    note.content,
                    note.source,
                    expires_str,
                    now_lv(),
                    vb_json,
                ),
            )
            note_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        db.commit()
        db.close()
        return _json_success({"note_id": note_id})
    except Exception as e:
        return _json_error(str(e))


def writeback_insight(
    politician_name: str | None = None,
    topic: str | None = None,
    insight: str = "",
    source: str = "analysis",
) -> str:
    """Write back an insight to a wiki person or topic page.

    At least one of politician_name or topic must be provided.
    """
    try:
        from src.wiki import _slugify
        from src.wiki_writeback import enrich_person_page, enrich_topic_page

        results = []
        if politician_name:
            slug = _slugify(politician_name)
            page_path = f"wiki/persons/{slug}.md"
            ok = enrich_person_page(page_path, insight, source)
            results.append(f"person/{slug}: {'written' if ok else 'skipped (duplicate or missing)'}")

        if topic:
            slug = _slugify(topic)
            ok = enrich_topic_page("wiki", slug, insight, source)
            results.append(f"topic/{slug}: {'written' if ok else 'skipped (duplicate or missing)'}")

        if not results:
            return _json_error("At least one of politician_name or topic required")

        return _json_success({"writeback": results})
    except Exception as e:
        return _json_error(str(e))


def store_claim(
    opponent_id: int,
    document_id: int,
    topic: str,
    stance: str,
    quote: str | None = None,
    confidence: float = 0.5,
    reasoning: str = "",
    salience: float = 0.5,
    source_url: str | None = None,
    stated_at: str | None = None,
    claim_type: str = "position",
    speaker_id: int | None = None,
    party_id: int | None = None,
    embedding_bytes: bytes | None = None,
    db=None,
) -> str:
    """Store a claim via the validated pydantic wrapper.

    ``claim_type`` defaults to ``'position'`` for media- or X-sourced first-
    person stances. Saeima voting records should pass ``'saeima_vote'``.

    ``speaker_id`` attributes authorship separately from the claim's subject.
    When ``None`` (default), the claim is first-party. When set, the claim
    is third-party commentary — typically paired with ``claim_type='commentary'``.
    Not part of the pydantic-validated ``Claim`` shape; forwarded to the db layer
    directly (same pattern as ``claim_type``). See ``src.db.store_claim``.

    ``party_id`` attributes the claim to a PARTY (party election-program
    promises, ``claim_type='program_promise'``): forwarded to the db layer
    directly. ``None`` (default) for ordinary politician claims.

    ``embedding_bytes`` (optional) is a precomputed e5-small embedding blob
    forwarded verbatim to ``db.store_claim`` so batch callers can compute the
    embedding outside a held write transaction. ``None`` (default) = the db
    layer computes it internally. See ``src.db.store_claim`` docstring.

    ``db`` is an optional externally-managed connection — see
    ``db.store_claim`` docstring. When provided, stated_at lookup and the
    INSERT both use this connection, enabling callers (``save_analysis``) to
    own a single atomic transaction across many claims.
    """
    try:
        topic = normalize_topic(topic)
        claim = Claim(
            opponent_id=opponent_id,
            document_id=document_id,
            topic=topic,
            stance=stance,
            quote=quote,
            confidence=confidence,
            reasoning=reasoning,
            salience=salience,
            source_url=source_url,
            stated_at=datetime.fromisoformat(stated_at) if stated_at else None,
        )

        # Auto-fill stated_at from document scraped_at if not provided
        if not claim.stated_at and document_id:
            owns_lookup_conn = db is None
            lookup_db = get_db() if owns_lookup_conn else db
            try:
                doc_row = lookup_db.execute(
                    "SELECT scraped_at FROM documents WHERE id = ?",
                    (document_id,),
                ).fetchone()
                if doc_row and doc_row["scraped_at"]:
                    claim.stated_at = datetime.fromisoformat(doc_row["scraped_at"])
            finally:
                if owns_lookup_conn:
                    lookup_db.close()

        claim_id = db_store_claim(
            opponent_id=claim.opponent_id,
            document_id=claim.document_id,
            topic=claim.topic,
            stance=claim.stance,
            quote=claim.quote,
            confidence=claim.confidence,
            reasoning=claim.reasoning,
            salience=claim.salience,
            source_url=claim.source_url,
            stated_at=str(claim.stated_at) if claim.stated_at else None,
            claim_type=claim_type,
            speaker_id=speaker_id,
            party_id=party_id,
            embedding_bytes=embedding_bytes,
            db=db,
        )
        return _json_success({"claim_id": claim_id})
    except Exception as e:
        return _json_error(str(e))


def query_claims(
    opponent_id: int,
    topic: str | None = None,
) -> str:
    try:
        db = get_db()
        if topic:
            rows = db.execute(
                """SELECT * FROM claims WHERE opponent_id = ? AND topic = ?
                   ORDER BY stated_at DESC, created_at DESC""",
                (opponent_id, topic),
            ).fetchall()
        else:
            rows = db.execute(
                """SELECT * FROM claims WHERE opponent_id = ?
                   ORDER BY stated_at DESC, created_at DESC""",
                (opponent_id,),
            ).fetchall()
        db.close()
        return json.dumps([dict(r) for r in rows], default=str, ensure_ascii=False)
    except Exception as e:
        return _json_error(str(e))


def search_similar_claims(
    opponent_id: int,
    claim_text: str,
    top_k: int = 10,
    claim_type_filter: Optional[list[str]] = None,
    speaker_scope: str = "first_party",
) -> str:
    """Vector-search claims by semantic similarity, optionally filtered by
    claim_type. See ``db.search_similar_claims`` docstring for the filter
    semantics and the directional usage pattern contradictions callers
    should follow.

    ``speaker_scope`` (CLAUDE.md #7): ``'first_party'`` (default) excludes
    third-party commentary; pass ``'commentary'`` for commentator
    self-consistency or ``'all'`` for legacy behavior.
    """
    try:
        query_vec = embed_text(claim_text)
        results = db_search_similar_claims(
            query_vec,
            opponent_id,
            top_k=top_k,
            claim_type_filter=claim_type_filter,
            speaker_scope=speaker_scope,
        )
        return json.dumps(results, default=str, ensure_ascii=False)
    except Exception as e:
        return _json_error(str(e))


def store_contradiction(
    opponent_id: int,
    old_claim_id: int,
    new_claim_id: int,
    topic: str,
    summary: str,
    severity: str,
    salience: float,
) -> str:
    try:
        topic = normalize_topic(topic)
        contradiction = Contradiction(
            opponent_id=opponent_id,
            claim_old_id=old_claim_id,
            claim_new_id=new_claim_id,
            topic=topic,
            summary=summary,
            severity=severity,
            salience=salience,
        )

        cid = db_store_contradiction(
            opponent_id=contradiction.opponent_id,
            old_claim_id=contradiction.claim_old_id,
            new_claim_id=contradiction.claim_new_id,
            topic=contradiction.topic,
            summary=contradiction.summary,
            severity=contradiction.severity,
            salience=contradiction.salience,
        )
        return _json_success({"contradiction_id": cid})
    except Exception as e:
        return _json_error(str(e))


def get_contradictions(
    opponent_id: int,
    confirmed_only: bool = False,
    min_salience: float = 0.0,
) -> str:
    try:
        db = get_db()
        query = """SELECT c.*,
                   co.stance AS old_stance, co.topic AS old_topic, co.quote AS old_quote,
                   cn.stance AS new_stance, cn.topic AS new_topic, cn.quote AS new_quote
                   FROM contradictions c
                   LEFT JOIN claims co ON c.claim_old_id = co.id
                   LEFT JOIN claims cn ON c.claim_new_id = cn.id
                   WHERE c.opponent_id = ? AND c.salience >= ?"""
        params: list = [opponent_id, min_salience]

        if confirmed_only:
            query += " AND c.confirmed = TRUE"

        query += " ORDER BY c.salience DESC, c.detected_at DESC"

        rows = db.execute(query, params).fetchall()
        db.close()
        return json.dumps([dict(r) for r in rows], default=str, ensure_ascii=False)
    except Exception as e:
        return _json_error(str(e))


def last_log(action: str | None = None) -> str:
    try:
        from src.db import get_last_log

        entry = get_last_log(action=action)
        if entry:
            return json.dumps(entry, default=str, ensure_ascii=False)
        return json.dumps(None)
    except Exception as e:
        return _json_error(str(e))
