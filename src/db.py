import hashlib
import json
import sqlite3
import struct
from datetime import datetime, timezone, timedelta, date
from pathlib import Path
from typing import Optional

from simhash import Simhash

from src.quality import check_quote_against_source, validate_lv_diacritics
from src.roles import enforce_subject_guards

_SCHEMA_PATH = Path(__file__).parent / "schema.sql"

DB_PATH = "data/atmina.db"

# Latvia timezone: EET (UTC+2) winter, EEST (UTC+3) summer
# DST switches last Sunday of March (→ +3) and last Sunday of October (→ +2)
#
# THE single definition of that offset. Public on purpose: until 2026-08-15 the
# same `timedelta(hours=3)` was re-typed in five other modules (ingest_log,
# social_agent/storage, wiki_writeback, wiki, render/_common), so the October
# DST switch meant finding six files — and five of them did not contain the
# string `now_lv`, which is what anyone would grep for. Import this (or better,
# the helpers below) instead of writing the number again.
LV_OFFSET = timedelta(hours=3)  # Current: EEST (summer 2026)

# Public stats cutoff: excludes the 2026-03-25..2026-04-04 testing era when the
# system was used as an MMN-party campaign tool (bulk MMN ingestion on 04-01,
# uneven per-politician coverage). Raw data stays in DB for audit, but public
# aggregates and leaderboards read from >= this date to avoid testing-bias.
CLEAN_START_DATE = "2026-04-05"

# Single definition of how `claims.review_status` is derived from `reasoning`.
# Shared by both triggers and the backfill in src/db_migrations.py (until
# 2026-09-05 they lived inline in init_db()) so the three can never disagree —
# a checker that reads different keys than the writer writes is the most
# repeated defect in this repo (CLAUDE.md § "A gate that cannot fail"). It
# stays HERE, in src.db, because store_* functions may reference it and
# db_migrations imports it back from this module.
#
# Order matters: resolution REPLACES the marker rather than sitting beside it
# (verified on the live DB — 0 rows carry both), so NEEDS_REVIEW is tested
# first and wins if a row ever carries both. All historical resolution
# spellings count: `Izvērtēts` is the runbook form (169 rows), `REVIEWED` the
# abandoned one (56 rows) that sessions kept drifting back to, `IZSKATĪTS`
# the 07-19/07-29 sweeps' form (31 rows that sat invisible to both queues
# until 2026-08-04). The match is GLOB, not LIKE, because it must be
# case-sensitive for EVERY letter: LIKE folds ASCII case, so the prose
# participle "izvērtēts" (ASCII `i`) and the column name `reviewed_at`
# resolved 3 of 700 rows on the live DB (2026-09-05: #17964, #20846,
# #709064). GLOB keeps "izskatīts"/"izvērtēts" prose out and only the
# marker spellings in. Pinned by tests/test_review_status_column.py.
_REVIEW_STATUS_EXPR = """
        CASE
            WHEN reasoning GLOB '*NEEDS_REVIEW*' THEN 'needs_review'
            WHEN reasoning GLOB '*Izvērtēts*' OR reasoning GLOB '*REVIEWED*'
                OR reasoning GLOB '*IZSKATĪTS*'
                THEN 'reviewed'
            ELSE NULL
        END"""

# `claims.review_status_at` — KAD `review_status` pēdējoreiz mainījās (2026-09-07,
# operatora verdikts 44). Līdz tam 14 dienu pārskatīšanas vārti mērīja vecumu no
# `claims.created_at` un tāpēc nešķīra «pūst rindā kopš aprīļa» no «vakar
# retro-marķēts»: 2026-08-22 tie ziņoja BAR BREACH par 19 rindām, kas rindā bija
# nokļuvušas iepriekšējā dienā (backlog/matcher.md § 14 dienu vārti).
#
# LV laiks, tāpat kā pašas `claims.created_at` (now_lv()) — trigeris nevar
# izsaukt Python, tāpēc nobīde ir SQL pusē. `datetime()` formāts ir tieši tas
# pats "YYYY-MM-DD HH:MM:SS", ko raksta now_lv(), tātad kolonnas ir salīdzināmas
# bez konversijas. Nobīde ir tā pati konstante, kas LV_OFFSET augšā: ja Latvija
# kādreiz atsakās no vasaras laika, abas vietas maināmas kopā.
_REVIEW_STATUS_AT_EXPR = "datetime('now', '+3 hours')"

# Vārtu formas vienīgā definīcija. Rindas bez zīmoga (visas pirms 2026-09-07)
# krīt atpakaļ uz `created_at` — konservatīvā puse: vecāks nozīmē, ka rinda
# drīzāk pārkāpj vārtus, nevis ka tā klusi attaisnojas ar šodienas datumu.
REVIEW_AGE_EXPR = "COALESCE(c.review_status_at, c.created_at)"

# Pārskatīšanas rindas slieksnis dienās (operatora lēmums 2026-08-03: rinda ir
# IEROBEŽOTA, ne tukša). Nesēji — @quality-reviewer § A un
# wiki/operations/quality-bars.md — lasa šo skaitli no šejienes.
REVIEW_QUEUE_AGE_DAYS = 14


def now_lv() -> str:
    """Return current datetime as ISO string in Latvia time (EEST/EET)."""
    return (datetime.now(timezone.utc) + LV_OFFSET).strftime("%Y-%m-%d %H:%M:%S")


def now_lv_dt() -> datetime:
    """Return current datetime as naive datetime in Latvia time (EEST/EET)."""
    return (datetime.now(timezone.utc) + LV_OFFSET).replace(tzinfo=None)


def today_lv() -> date:
    """Return current date in Latvia time."""
    return now_lv_dt().date()


def lv_cutoff(days: int) -> str:
    """Return the `days`-ago LV timestamp in the format timestamps are STORED.

    Every timestamp column we compare against holds ``"YYYY-MM-DD HH:MM:SS"``
    (``now_lv()`` above, and SQLite's ``CURRENT_TIMESTAMP``), and SQLite
    compares these as plain strings. ``datetime.isoformat()`` looks equivalent
    but separates with ``"T"`` — and ``" "`` (0x20) sorts BEFORE ``"T"``
    (0x54), so ``"2026-07-24 21:16:07" >= "2026-07-24T00:16:07"`` is FALSE.
    Rows landing on the cutoff's own DATE are therefore dropped whatever their
    clock time: a `days=7` window silently becomes six days plus a fraction.

    Latent since the queries were written; it surfaced 2026-07-24 as a red CI
    on the public mirror, because on a UTC runner between 21:00 and 24:00 the
    fixtures' machine-local date equals the LV cutoff date and EVERY document
    falls into the dropped band. On an LV machine the same code passes, which
    is why local `check.sh` stayed green. Use this helper for any comparison
    against a stored timestamp; never `.isoformat()`.
    """
    return (now_lv_dt() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")


def init_db(db_path: str | None = None) -> None:
    # _allow_empty: init_db is the one legitimate writer of an empty file
    # (fixtures do mkstemp → init_db); everyone else gets the 0-byte refusal.
    db = get_db(db_path, _allow_empty=True)

    import sqlite_vec
    db.enable_load_extension(True)
    sqlite_vec.load(db)
    db.enable_load_extension(False)

    # Static DDL lives in src/schema.sql.
    db.executescript(_SCHEMA_PATH.read_text(encoding="utf-8"))

    # Vec0 virtual tables stay as separate db.execute() calls so
    # tests/test_knab.py::_SafeConnection can intercept them when
    # sqlite_vec is mocked to a no-op (CI environments without the
    # native extension). Don't move this into schema.sql.
    db.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS document_vectors
        USING vec0(chunk_id INTEGER PRIMARY KEY, embedding float[384])
    """)
    db.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS claim_vectors
        USING vec0(claim_id INTEGER PRIMARY KEY, embedding float[384])
    """)

    # The hand-rolled migration ladder (ALTERs, guard-tables, the
    # claims_review_status triggers + backfill, indexes) lives in
    # src/db_migrations.py since 2026-09-05 — init_db was 297 lines of which
    # 269 were that ladder. Imported HERE, not at module top, because
    # db_migrations imports _REVIEW_STATUS_EXPR back from this module: a
    # top-level import would be a cycle. Every step in there is idempotent and
    # self-healing; it does not commit.
    from src.db_migrations import apply_migrations
    apply_migrations(db)

    db.commit()


def get_db(db_path: Optional[str] = None, _allow_empty: bool = False) -> sqlite3.Connection:
    # Resolve DB_PATH at CALL time, not def time. A default-argument
    # `db_path=DB_PATH` would bind the module global's value when this
    # function is defined, so a later `monkeypatch.setattr(db, "DB_PATH", ...)`
    # in a test would be a silent no-op and no-arg `get_db()` calls (e.g. the
    # matcher's `_load_politician_forms()`) would keep reading the live DB.
    # Resolving here makes DB_PATH overridable, which is what hermetic tests
    # rely on. Production never patches DB_PATH, so behaviour is unchanged.
    if db_path is None:
        db_path = DB_PATH
    # A 0-byte file is SQLite's canonical "valid new database", so nothing
    # downstream ever fails loudly — work just dies in the empty file. Eleven
    # such files (dead connects with wrong paths) existed until 2026-08-02;
    # only init_db() may write into one (_allow_empty).
    if not _allow_empty:
        _p = Path(db_path)
        if _p.exists() and _p.stat().st_size == 0:
            raise RuntimeError(
                f"Refusing to open 0-byte DB file: {db_path} — a valid atmina "
                "DB is never empty. This is almost always a wrong path or a "
                "leftover from a dead connect; delete the file, or run "
                "init_db() if a fresh DB is intended."
            )
    # timeout=30 and PRAGMA busy_timeout are belt-and-braces: Python's
    # sqlite3 driver sets the pragma from the timeout parameter, but we set
    # the pragma explicitly so the value survives driver-version churn. The
    # 2026-04-10 parallel backlog run hit silent store_claim failures that
    # were consistent with lock-wait timeouts under default 5s.
    db = sqlite3.connect(db_path, timeout=30.0)
    db.execute("PRAGMA foreign_keys = ON")
    db.execute("PRAGMA busy_timeout = 30000")
    db.row_factory = sqlite3.Row
    return db


def open_review_queue(db_path: Optional[str] = None) -> list[sqlite3.Row]:
    """Atvērtā `needs_review` rinda, kuras vecums mērīts no MARĶIERA, ne claim.

    Vienīgā vārtu forma (`REVIEW_AGE_EXPR`) — @quality-reviewer § A un
    quality-bars.md 14 dienu robeža lasa šo funkciju, nevis raksta savu SQL.
    Līdz 2026-09-07 vārti mērīja `created_at`, tāpēc retro-marķēšana uzreiz
    ražoja "pārkāpumu" par darbu, kas notika iepriekšējā dienā.

    Kolonnas: `id`, `name`, `topic`, `stance`, `reasoning`, `review_status_at`,
    `created_at`, `age_days` (dienas kopš marķiera, LV laikā).
    """
    db = get_db(db_path)
    try:
        return db.execute(
            f"""
            SELECT c.id, p.name, c.topic, c.stance, c.reasoning,
                   c.review_status_at, c.created_at,
                   CAST(julianday(?) - julianday({REVIEW_AGE_EXPR}) AS INT) AS age_days
            FROM claims c
            LEFT JOIN tracked_politicians p ON p.id = c.opponent_id
            WHERE c.review_status = 'needs_review'
            ORDER BY {REVIEW_AGE_EXPR}
            """,
            (now_lv(),),
        ).fetchall()
    finally:
        db.close()


def _compute_content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _compute_simhash(content: str) -> int:
    # Truncate to 10k chars for simhash — the library has overflow bugs
    # on large texts with certain Unicode characters. 10k is more than
    # enough for near-duplicate detection. Some inputs (e.g. Vēstneša MK
    # sēžu protokoli with dense LV diacritic clusters) overflow uint8 in
    # `Simhash.build_by_features` even at 10k; fall back to progressively
    # smaller windows so ingest never blocks. Loss: only the first ~2k
    # chars contribute, which is still adequate for dedup of header+lead.
    for window in (10000, 5000, 2500, 1500):
        try:
            v = Simhash(content[:window]).value
            break
        except OverflowError:
            continue
    else:
        # Last-resort deterministic fallback derived from the content hash.
        # Near-dupe detection effectively disabled for this doc, but ingest
        # proceeds.
        v = int(_compute_content_hash(content)[:16], 16)
    # Convert to signed 64-bit int for SQLite compatibility
    if v >= (1 << 63):
        v -= 1 << 64
    return v


def _hamming_distance(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def insert_document(
    content: str,
    source_id: Optional[int],
    platform: str = "web",
    language: str = "lv",
    is_auto_caption: bool = False,
    source_url: Optional[str] = None,
    published_at: Optional[str] = None,
    reply_count: Optional[int] = None,
    retweet_count: Optional[int] = None,
    favorite_count: Optional[int] = None,
    politician_links: Optional[list[tuple[int, str]]] = None,
    title: Optional[str] = None,
    db_path: str | None = None,
) -> Optional[int]:
    """Store a document, deduplicating first by content hash and then by URL.

    Three outcomes:

    * **Identical bytes already stored** → returns ``None`` (caller skips
      re-embed); junctions merge onto the existing row only when the URL matches.
    * **Same URL, different content, ``platform='web'``** → the existing row is
      UPDATEd in place (URL is canonical, content is mutable) and its id is
      returned.
    * **Otherwise** → a new row is INSERTed and its id returned.

    The in-place UPDATE branch (LETA / doc-72446 class, operator decision
    2026-08-17): a publisher can put a *different story* behind an already
    ingested URL. Two consequences are handled explicitly there:

    * ``title`` takes the incoming value whenever one is supplied — the previous
      ``COALESCE(title, ?)`` kept the OLD headline over the NEW body, which is
      the signature that hid the class. A fetch with ``title=None`` still keeps
      the stored title.
    * ``reviewed_at`` is reset to ``NULL``. **This is deliberate and its point is
      the side effect**: the document re-enters the extraction queue
      (``analyze.get_pending_politicians`` and every other ``reviewed_at IS
      NULL`` reader), because the new text has never been reviewed while the
      claims extracted from the old text still point at it. An unchanged
      re-fetch cannot trigger this — identical bytes short-circuit at the
      content_hash lookup above and never reach the UPDATE — so review stamps
      are not churned by routine re-scrapes.

    Both behaviours are web-only, matching the existing URL-first invariant: X
    and vestnesis URLs have stable URL→content guarantees from the source.

    ``politician_links`` passes through ``roles.enforce_subject_guards()``
    first (2026-09-07, operatora verdikti 36 + 38): a relay media slot and the
    retweeter of an office voice are demoted to ``mentioned``. This is the one
    choke point every non-matcher writer shares — ``ingest.fetch_source``,
    ``social._store_tweets``, ``social.fetch_x_mentions`` — so the rule cannot
    be forgotten at a call site. Roles arriving already as ``mentioned`` are
    untouched, and no link is ever dropped.
    """
    db = get_db(db_path)
    politician_links = enforce_subject_guards(db, politician_links, content)
    content_hash = _compute_content_hash(content)

    # Check exact content_hash duplicate (same bytes already stored)
    existing = db.execute(
        "SELECT id, source_url FROM documents WHERE content_hash = ?", (content_hash,)
    ).fetchone()
    if existing:
        # Merge any new junctions onto the existing doc IF this is the same
        # canonical post (same source_url). The same-URL gate is deliberate:
        # identical text under a DIFFERENT url (copypasta tweets by different
        # authors) must NOT graft its links onto the first doc. This closes the
        # doc-72542 hole where a cross-feed author's 'subject' junction was
        # permanently lost — content_hash dedup returned None and dropped the
        # caller's politician_links. Still return None so callers skip re-embed.
        if politician_links and source_url and existing["source_url"] == source_url:
            for pid, role in politician_links:
                db.execute(
                    """INSERT OR IGNORE INTO document_politicians
                       (document_id, politician_id, role) VALUES (?, ?, ?)""",
                    (existing["id"], pid, role),
                )
            db.commit()
        db.close()
        return None

    sim = _compute_simhash(content)

    # URL-first dedup (added 2026-05-13): if the same URL already has a row
    # but with different content_hash, the source publisher edited the
    # article between fetches. Update the existing row in place — same
    # URL = same canonical article, only the latest content is authoritative.
    # Prevents the 2026-05-13 Delfi case where a 4h re-scrape of an edited
    # article (979→892 chars) created a duplicate doc row. URL is canonical;
    # content is mutable. Limited to platform='web' since X tweets and
    # vestnesis docs have stable URL→content guarantees from the source.
    if source_url and platform == "web":
        existing_url = db.execute(
            "SELECT id FROM documents WHERE source_url = ? AND platform = 'web'",
            (source_url,),
        ).fetchone()
        if existing_url:
            word_count = len(content.split())
            from urllib.parse import urlparse
            try:
                source_domain = urlparse(source_url).netloc
                if source_domain == "pmo.ee":
                    source_domain = "tvnet.lv"
            except Exception:
                source_domain = None
            # `title` takes the NEW value when the fetch carries one (only
            # falling back to the stored title when the caller passes None) and
            # `reviewed_at` is cleared — both operator decisions of 2026-08-17,
            # see the docstring's "LETA/doc-72446 class" note. This branch runs
            # ONLY when the content actually changed: identical bytes are caught
            # by the content_hash lookup above and never reach here, so an
            # unchanged re-fetch cannot un-review a document.
            db.execute(
                """UPDATE documents
                   SET content=?, content_hash=?, simhash=?, word_count=?,
                       scraped_at=?, source_domain=COALESCE(source_domain, ?),
                       title=COALESCE(?, title), published_at=COALESCE(published_at, ?),
                       reviewed_at=NULL
                   WHERE id=?""",
                (content, content_hash, sim, word_count, now_lv(),
                 source_domain, title, published_at, existing_url["id"]),
            )
            # Merge the caller's junctions onto the updated row. Until 2026-08-15
            # this branch returned without them, so a politician newly named in an
            # EDITED article was never linked: the later mention scan
            # (matcher.py::link_politicians_to_documents) only offers documents with
            # NO junction rows at all, so the miss was permanent and silent. The
            # same-URL gate that guards the content_hash branch above is satisfied
            # here by construction — the SELECT matched on source_url.
            if politician_links:
                for pid, role in politician_links:
                    db.execute(
                        """INSERT OR IGNORE INTO document_politicians
                           (document_id, politician_id, role) VALUES (?, ?, ?)""",
                        (existing_url["id"], pid, role),
                    )
            db.commit()
            db.close()
            return existing_url["id"]

    # Skip near-dupe check for x_mention (same tweet, different targets)
    near_dupe_of = None
    if platform != "x_mention":
        rows = db.execute("SELECT id, simhash FROM documents WHERE simhash IS NOT NULL").fetchall()
        for row in rows:
            if _hamming_distance(sim, row["simhash"]) <= 3:
                near_dupe_of = row["id"]
                break

    word_count = len(content.split())
    # Extract domain from source_url
    source_domain = None
    if source_url:
        try:
            from urllib.parse import urlparse
            source_domain = urlparse(source_url).netloc
            # pmo.ee is the Postimees Group shortener used by TVNet RSS feed.
            # Content is Latvian TVNet/Apollo material; show as tvnet.lv in UI.
            if source_domain == "pmo.ee":
                source_domain = "tvnet.lv"
        except Exception:
            pass

    db.execute(
        """INSERT INTO documents (content, content_hash, simhash, source_id,
           platform, is_auto_caption, near_dupe_of, source_domain, source_url, word_count, language,
           published_at, scraped_at, reply_count, retweet_count, favorite_count, title)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (content, content_hash, sim, source_id, platform,
         is_auto_caption, near_dupe_of, source_domain, source_url, word_count, language,
         published_at, now_lv(), reply_count, retweet_count, favorite_count, title),
    )
    doc_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]

    if politician_links:
        for pid, role in politician_links:
            db.execute(
                """INSERT OR IGNORE INTO document_politicians
                   (document_id, politician_id, role) VALUES (?, ?, ?)""",
                (doc_id, pid, role),
            )

    db.commit()
    db.close()
    return doc_id


def link_politician_to_document(document_id: int, politician_id: int, role: str = "subject") -> None:
    """Add a politician link to an existing document.

    Deliberately NOT routed through ``roles.enforce_subject_guards()`` (2026-09-07):
    this takes an explicit pid and role, so it is the escape hatch for linking a
    relay slot on purpose — the same exemption ``src/scope.py`` grants
    ``analyze.get_politician_documents``. The guards belong on the bulk writers
    (``insert_document``, ``matcher.link_politicians_to_documents``), where the
    role is DERIVED from string presence and nobody chose it.
    """
    db = get_db()
    db.execute(
        "INSERT OR IGNORE INTO document_politicians (document_id, politician_id, role) VALUES (?, ?, ?)",
        (document_id, politician_id, role),
    )
    db.commit()
    db.close()


def _float_list_to_bytes(vec: list[float]) -> bytes:
    return struct.pack(f"{len(vec)}f", *vec)


def insert_chunks(
    document_id: int,
    chunks: list[tuple[int, str, list[float]]],
    db_path: str | None = None,
) -> None:
    db = get_db(db_path)
    import sqlite_vec

    db.enable_load_extension(True)
    sqlite_vec.load(db)
    db.enable_load_extension(False)

    # REPLACE, never append. insert_document's URL-first branch returns the
    # EXISTING doc id when a re-scrape brings a changed body (src/db.py:334-367),
    # and every caller then re-embeds the full text and lands here — so a plain
    # INSERT stacked a second full set of chunks on the same document. Measured
    # 2026-08-02: 586 documents carrying duplicate (document_id, chunk_index),
    # 690 surplus rows, each with a live document_vectors embedding, so
    # semantic search ranked and returned text the article no longer contained.
    #
    # document_vectors is a vec0 virtual table and does NOT cascade from the
    # document_chunks delete, so its rows must go first, by chunk_id.
    old_ids = [
        r[0]
        for r in db.execute(
            "SELECT id FROM document_chunks WHERE document_id = ?", (document_id,)
        )
    ]
    if old_ids:
        db.executemany(
            "DELETE FROM document_vectors WHERE chunk_id = ?",
            [(cid,) for cid in old_ids],
        )
        db.execute("DELETE FROM document_chunks WHERE document_id = ?", (document_id,))

    for chunk_index, chunk_text, embedding in chunks:
        db.execute(
            "INSERT INTO document_chunks (document_id, chunk_index, content) VALUES (?, ?, ?)",
            (document_id, chunk_index, chunk_text),
        )
        chunk_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        db.execute(
            "INSERT INTO document_vectors (chunk_id, embedding) VALUES (?, ?)",
            (chunk_id, _float_list_to_bytes(embedding)),
        )
    db.commit()
    db.close()


def search_similar(
    query_embedding: list[float],
    top_k: int = 10,
    politician_id: Optional[int] = None,
    db_path: str | None = None,
) -> list[dict]:
    db = get_db(db_path)
    import sqlite_vec

    db.enable_load_extension(True)
    sqlite_vec.load(db)
    db.enable_load_extension(False)

    query_bytes = _float_list_to_bytes(query_embedding)

    rows = db.execute(
        """SELECT dv.chunk_id, dv.distance, dc.document_id, dc.content
           FROM document_vectors dv
           JOIN document_chunks dc ON dc.id = dv.chunk_id
           WHERE dv.embedding MATCH ? AND k = ?
           ORDER BY dv.distance""",
        (query_bytes, top_k),
    ).fetchall()

    results = []
    if politician_id is not None:
        linked_doc_ids = {
            r[0] for r in db.execute(
                "SELECT document_id FROM document_politicians WHERE politician_id = ?",
                (politician_id,),
            ).fetchall()
        }

    for row in rows:
        if politician_id is not None and row["document_id"] not in linked_doc_ids:
            continue
        results.append({
            "chunk_id": row["chunk_id"],
            "document_id": row["document_id"],
            "distance": row["distance"],
            "content": row["content"],
        })

    db.close()
    return results[:top_k]


def search_similar_claims(
    query_embedding: list[float],
    opponent_id: int,
    top_k: int = 10,
    claim_type_filter: Optional[list[str]] = None,
    speaker_scope: str = "first_party",
    db_path: str | None = None,
) -> list[dict]:
    """Vector-search claims for a politician, optionally restricted by claim_type.

    ``claim_type_filter``:
        - ``None`` (default) — no type filter, returns any matching claim.
        - list of type strings (e.g. ``['position']`` or
          ``['position', 'saeima_vote']``) — only claims whose ``claim_type``
          is in the list are returned.

    Contradiction callers should apply this filter directionally per
    call-site: position → candidates should include both types,
    saeima_vote → candidates should include position only (vote-vs-vote is
    procedural noise, see the 2026-04-11 audit). Generic similarity lookups
    should pass ``None``.

    ``speaker_scope`` restricts matches by speaker relationship:

    - ``'first_party'`` (default): only claims the politician made themselves
      (``speaker_id IS NULL OR speaker_id = opponent_id``). This is what
      contradiction detectors want — "did Pūpols contradict himself?".
    - ``'commentary'``: only third-party commentary claims about this politician
      (``speaker_id IS NOT NULL AND speaker_id != opponent_id``). Useful for
      future commentator-self-consistency analysis.
    - ``'all'``: pre-Komentētāji behavior, returns everything. Rarely what you
      want; only use when you explicitly don't care who said it.

    All three filters (``opponent_id``, ``claim_type_filter``,
    ``speaker_scope``) are pushed INSIDE the k-NN query via a
    ``claim_id IN (subquery)`` constraint (``claim_vectors`` is a vec0 table
    whose ``claim_id`` is the rowid alias; the ``rowid IN`` constraint is
    supported by the pinned sqlite-vec v0.1.9). ``top_k`` is therefore the
    budget WITHIN this politician's own filtered claims, not against the full
    ~553k-vector index — so callers no longer need to inflate ``top_k`` to
    compensate (the old workaround was ``top_k=400``). Without the pushdown,
    a politician's relevant claims are squeezed out when they fall outside the
    global nearest ``top_k`` (2026-07-23 squeeze-out; BACKLOG § kNN izspiešana).
    The Python post-filter loop below re-checks the same conditions as
    defense-in-depth.
    """
    db = get_db(db_path)
    import sqlite_vec

    db.enable_load_extension(True)
    sqlite_vec.load(db)
    db.enable_load_extension(False)

    query_bytes = _float_list_to_bytes(query_embedding)

    # An EMPTY claim_type_filter means "no types" — the post-filter loop would
    # return nothing, so short-circuit rather than emit a degenerate IN () SQL.
    if claim_type_filter is not None and len(claim_type_filter) == 0:
        db.close()
        return []

    # Build the pushdown subquery: restrict the k-NN candidate set to this
    # politician's relevant claims BEFORE the k budget is spent (see docstring).
    sub_clauses = ["c.opponent_id = ?"]
    sub_params: list = [opponent_id]
    if claim_type_filter is not None:
        placeholders = ",".join("?" for _ in claim_type_filter)
        sub_clauses.append(f"c.claim_type IN ({placeholders})")
        sub_params.extend(claim_type_filter)
    if speaker_scope == "first_party":
        sub_clauses.append("(c.speaker_id IS NULL OR c.speaker_id = c.opponent_id)")
    elif speaker_scope == "commentary":
        sub_clauses.append("(c.speaker_id IS NOT NULL AND c.speaker_id != c.opponent_id)")
    # speaker_scope == "all" → no speaker clause

    subquery = f"SELECT c.id FROM claims c WHERE {' AND '.join(sub_clauses)}"

    rows = db.execute(
        f"""SELECT cv.claim_id, cv.distance
           FROM claim_vectors cv
           WHERE cv.embedding MATCH ? AND k = ?
             AND cv.claim_id IN ({subquery})
           ORDER BY cv.distance""",
        (query_bytes, top_k, *sub_params),
    ).fetchall()

    results = []
    for row in rows:
        claim = db.execute(
            "SELECT * FROM claims WHERE id = ? AND opponent_id = ?",
            (row["claim_id"], opponent_id),
        ).fetchone()
        if claim:
            if claim_type_filter is not None and claim["claim_type"] not in claim_type_filter:
                continue
            # 2026-04-23: scope claims by speaker relationship. 'first_party' is
            # the safe default — contradiction detectors compare a politician's
            # own positions, not allegations against them. 'commentary' flips it
            # (commentator-vs-self over time, future). 'all' preserves legacy
            # any-speaker behavior for callers that explicitly opt in.
            is_first_party = claim["speaker_id"] is None or claim["speaker_id"] == claim["opponent_id"]
            if speaker_scope == "first_party" and not is_first_party:
                continue
            if speaker_scope == "commentary" and is_first_party:
                continue
            # speaker_scope == "all" → no filter
            results.append({**dict(claim), "distance": row["distance"]})

    db.close()
    return results


def store_claim(
    opponent_id: int,
    document_id: Optional[int],
    topic: str,
    stance: str,
    quote: Optional[str],
    confidence: float,
    reasoning: str,
    salience: float,
    source_url: Optional[str],
    stated_at: Optional[str],
    claim_type: str = "position",
    speaker_id: Optional[int] = None,
    party_id: Optional[int] = None,
    embedding_bytes: Optional[bytes] = None,
    db_path: str | None = None,
    db: Optional[sqlite3.Connection] = None,
) -> int:
    """Insert a claim with URL-level idempotency and inactive-politician guard.

    If a claim already exists for the same ``(opponent_id, source_url, topic)``
    triple, the existing claim_id is returned and no new row is inserted.
    This protects against scraper-induced duplicate extraction when the same
    bill page, article, or tweet gets re-ingested with a fresh document_id
    (see src/saeima/votes.py::store_vote). First-write-wins semantics preserve historical
    accuracy; callers that need to refresh fields should UPDATE explicitly.

    Raises ``ValueError`` if ``opponent_id`` does not exist in
    ``tracked_politicians``, or if the target politician is marked inactive.
    Sentinel entries ('Nepareizais', 'Kas Notiek Latvijā', etc.) are inactive
    by design — they exist only for document linking and must never receive
    claims. A loud error is preferred over silent skip so that miswired
    extraction flows are caught immediately.

    ``claim_type`` defaults to ``'position'`` for media- or X-sourced first-
    person stances. Saeima voting records must pass ``'saeima_vote'``; the
    set is open for future values (``'ep_vote'``, ``'committee_vote'``, etc.)
    but downstream consumers only recognize the two today.

    ``speaker_id`` attributes authorship separately from the claim's subject.
    When ``None`` (default), the claim is first-party — the speaker IS the
    opponent (legacy behavior; consumers should ``COALESCE(speaker_id, opponent_id)``
    when they need a concrete speaker). When set to a different
    ``tracked_politicians.id``, the claim is third-party commentary — typically
    pair this with ``claim_type='commentary'``. Does NOT affect idempotency:
    one source_url has one author, so ``(opponent_id, source_url, topic)``
    stays unique per politician-about-whom.

    ``party_id`` attributes a claim to a PARTY. Used for party election-program
    promises (``claim_type='program_promise'``): ``party_id`` = the party,
    ``opponent_id`` = the list leader who carries the program. Renders group
    such claims to the party by ``party_id`` and exclude them from the leader's
    personal positions by ``claim_type``. ``None`` (default) for all ordinary
    politician claims. Not part of idempotency.

    ``saeima_vote`` claims are NOT auto-embedded (2026-08-21 operator verdict):
    mechanical vote rows were 98% of ``claim_vectors`` (~953 MB) while every
    kNN reader filters them out (T10) and T9 bars embeddings from
    rhetoric-vs-vote detection anyway. Historical vectors are kept;
    ``party_contradictions.rank_candidates`` counts missing vectors as
    ``skipped_missing_vector``. An explicitly passed ``embedding_bytes`` is
    still stored, so kNN type-filter mechanics remain testable.

    ``db`` is an optional externally-managed connection — when provided, the
    function reuses it and does NOT commit or close. Caller owns the
    transaction lifecycle. This enables ``save_analysis`` to wrap a whole
    analysis + claims + reviewed-docs update in a single atomic transaction
    so a mid-batch failure rolls back everything rather than leaving half the
    claims persisted. When ``db`` is ``None`` (default) the function opens
    its own connection, commits, and closes — legacy behavior.

    ``embedding_bytes`` lets a caller supply a precomputed e5-small embedding
    blob (as produced by ``_float_list_to_bytes(embed_text(f"{topic}: {stance}"))``)
    so the ~100ms–10s ``embed_text`` cost happens BEFORE the write transaction
    is entered rather than under a held write lock. When ``None`` (default) the
    embedding is computed internally — unchanged behavior. This exists because
    ``save_analysis`` wraps a whole claim batch in ONE ``with db:`` transaction:
    computing each claim's embedding under that held lock summed N embedding
    costs into the lock-hold window, exceeding the 30s busy_timeout under
    parallel extraction fan-out ("database is locked"). Batch callers precompute
    outside the lock and pass the bytes here. The provided bytes must be
    byte-identical to the internal computation (same ALREADY-NORMALIZED
    ``topic``, same ``stance``) — the point is to keep slow embedding work
    outside the held SQLite write transaction (write-contention design).
    """
    owns_connection = db is None
    if owns_connection:
        db = get_db(db_path)

    try:
        # Guard: the target politician must exist and be active.
        politician_row = db.execute(
            "SELECT relationship_type, name FROM tracked_politicians WHERE id = ?",
            (opponent_id,),
        ).fetchone()
        if politician_row is None:
            raise ValueError(
                f"store_claim: opponent_id={opponent_id} not found in "
                f"tracked_politicians"
            )
        # Inactive guard: blocks rhetoric/position attribution to retired
        # politicians or sentinel entries. saeima_vote claims are exempt
        # because they are HISTORICAL vote-ledger records — a deputy who later
        # resigns still has a real voting trail worth preserving, and the
        # P3 backfill (2026-05-27) explicitly adds historic 14. Saeima
        # deputies as 'inactive' so their vote rows attribute correctly.
        if politician_row["relationship_type"] == "inactive" and claim_type != "saeima_vote":
            name = politician_row["name"]
            raise ValueError(
                f"store_claim: opponent_id={opponent_id} ('{name}') is inactive. "
                f"Claims must target active politicians only — sentinel entries "
                f"('Nepareizais', 'Kas Notiek Latvijā', retired deputies) must "
                f"not receive claims."
            )

        # Provenance guard: every claim type except saeima_vote must name the
        # document it came from. Vote claims are the sole exception — their
        # provenance runs saeima_individual_votes.politician_id → parent
        # saeima_votes.url, so there is no document row to point at (CLAUDE.md
        # Data Contract #6).
        #
        # This is the ONLY layer that can enforce it: the Pydantic ``Claim``
        # model does not carry claim_type, so it cannot tell a legal NULL from
        # a lost one. Live data agrees with the rule exactly — of 518 285 rows,
        # all 512 918 saeima_vote claims are NULL and position / commentary /
        # program_promise are 0 % NULL — so this codifies the existing invariant
        # rather than introducing a new constraint.
        if claim_type != "saeima_vote" and document_id is None:
            raise ValueError(
                f"store_claim: claim_type='{claim_type}' requires a document_id. "
                f"Only 'saeima_vote' claims may store NULL (provenance comes "
                f"from saeima_individual_votes instead). A claim with no "
                f"document has no re-fetchable provenance."
            )

        # The source document backs two checks below (quote verification and
        # URL canonicalization), so it is read once, here, before either.
        doc_row = db.execute(
            "SELECT source_url, content FROM documents WHERE id = ?", (document_id,)
        ).fetchone()

        # Diacritic guardrail — reject stripped Latvian text from agent context
        # drift. Skipped for saeima_vote claims because those are written by
        # generate_claims_from_votes() in src/saeima/votes.py with deterministic
        # template strings ("Saeimas balsojums DATE: NAME balsoja STANCE") that
        # legitimately contain politician names without diacritics — not
        # agent-stripped Latvian.
        #
        # `quote` is NOT in this loop. CLAUDE.md makes claims.quote VERBATIM and
        # scopes the diacritic gate to OUR words ("Correcting a quote is
        # misquoting"), so a ratio test on a citation was answering the wrong
        # question in both directions — it refused authentic low-diacritic
        # Latvian (#555664, where refusing meant storing NO quote and thereby
        # silently dropping provenance) while passing a diacritic-rich sentence
        # with one damaged word. Quotes go through the source comparison below.
        if claim_type != "saeima_vote":
            for field_name, field_value in (
                ("stance", stance), ("reasoning", reasoning)
            ):
                ok, reason = validate_lv_diacritics(field_value)
                if not ok:
                    raise ValueError(
                        f"store_claim: {field_name} failed diacritic validation "
                        f"(opponent_id={opponent_id}): {reason}"
                    )

            # Verbatim guardrail — the quote must be what the document says.
            # Refuses only the provable case (present after folding, absent
            # before). `cannot_verify` does NOT block, because 30 % of live
            # quotes are legitimately unlocatable character-exactly (English,
            # elisions, typographic quotes, re-fetched bodies) — but since
            # 2026-08-24 it is its own verdict, not a pass, so nothing here may
            # report it as one (`QuoteCheck` docstring carries the incident).
            check = check_quote_against_source(
                quote, doc_row["content"] if doc_row else None
            )
            if check.blocks:
                raise ValueError(
                    f"store_claim: quote failed source verification "
                    f"(opponent_id={opponent_id}): {check.reason}"
                )

        # Defensive URL canonicalization — the document's source_url is
        # authoritative. If the caller passed a different URL (typically an
        # extractor agent that hallucinated a status ID or stripped a scheme),
        # silently override with the document's URL so that downstream dedup
        # and UI grouping use the canonical reference.
        if doc_row and doc_row["source_url"]:
            source_url = doc_row["source_url"]

        # URL-level dedup — see docstring. Only enforced when source_url is
        # present; claims without a URL bypass the check (legacy behavior).
        if source_url:
            existing = db.execute(
                """SELECT id FROM claims
                   WHERE opponent_id = ? AND source_url = ? AND topic = ?
                   LIMIT 1""",
                (opponent_id, source_url, topic),
            ).fetchone()
            if existing:
                if owns_connection:
                    db.close()
                return existing["id"]

        # Compute embedding BEFORE opening the write transaction. Previously the
        # embedding ran between the claims INSERT and the claim_vectors INSERT,
        # which held the SQLite write lock across the 100ms-10s embedding cost
        # and caused silent store_claim timeouts under 6-way parallel extraction
        # (see 2026-04-10 backlog run diagnosis). Computing it first keeps the
        # write transaction short. Batch callers (save_analysis) that hold a
        # single transaction across N claims pass the precomputed blob via
        # embedding_bytes so even this per-call cost lands outside the lock.
        # 2026-08-21 operatora verdikts: saeima_vote claims vairs NETIEK
        # auto-embedoti (detaļas store_claim docstringā). Eksplikīti padots
        # embedding_bytes tiek saglabāts arī balsojuma claimam.
        if embedding_bytes is None and claim_type != "saeima_vote":
            from src.embeddings import embed_text

            embedding_bytes = _float_list_to_bytes(embed_text(f"{topic}: {stance}"))

        import sqlite_vec

        db.enable_load_extension(True)
        sqlite_vec.load(db)
        db.enable_load_extension(False)

        db.execute(
            """INSERT INTO claims (opponent_id, document_id, topic, stance, quote,
               confidence, reasoning, salience, source_url, stated_at, claim_type,
               speaker_id, party_id, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (opponent_id, document_id, topic, stance, quote, confidence,
             reasoning, salience, source_url, stated_at, claim_type,
             speaker_id, party_id, now_lv()),
        )
        claim_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]

        if embedding_bytes is not None:
            db.execute(
                "INSERT INTO claim_vectors (claim_id, embedding) VALUES (?, ?)",
                (claim_id, embedding_bytes),
            )
        if owns_connection:
            db.commit()
        return claim_id
    finally:
        if owns_connection:
            db.close()


def store_contradiction(
    opponent_id: int,
    old_claim_id: int,
    new_claim_id: int,
    topic: str,
    summary: str,
    severity: str,
    salience: float,
    db_path: str | None = None,
) -> int:
    db = get_db(db_path)
    db.execute(
        """INSERT INTO contradictions (opponent_id, claim_old_id, claim_new_id,
           topic, summary, severity, salience, detected_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (opponent_id, old_claim_id, new_claim_id, topic, summary, severity, salience, now_lv()),
    )
    cid = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    db.commit()
    db.close()
    return cid


def store_tension(source_pid: int, target_pid: int, topic: str, description: str,
                  tension_type: str = "spriedze", source_url: str = None,
                  target_url: str = None, db_path: str | None = None) -> int:
    """Store a political tension between two politicians.

    Raises ``ValueError`` if:
      - ``description`` fails the diacritic guardrail (agent context drift).
      - ``source_url`` is missing or does not reference a row in ``documents``.
        Catches hallucinated URLs (e.g. guessed tweet status IDs, wrong article
        slugs). Tension sources must always point to a scraped document.
      - ``target_url`` is set but does not reference a row in ``documents``.
    """
    ok, reason = validate_lv_diacritics(description)
    if not ok:
        raise ValueError(
            f"store_tension: description failed diacritic validation "
            f"(source_pid={source_pid}, target_pid={target_pid}): {reason}"
        )
    if not source_url:
        raise ValueError(
            f"store_tension: source_url is required "
            f"(source_pid={source_pid}, target_pid={target_pid})"
        )
    db = get_db(db_path)
    known = db.execute(
        "SELECT 1 FROM documents WHERE source_url = ? LIMIT 1", (source_url,)
    ).fetchone()
    if not known:
        db.close()
        raise ValueError(
            f"store_tension: source_url not found in documents table — "
            f"likely hallucinated. Look up the real URL from documents.source_url "
            f"before storing. source_pid={source_pid}, target_pid={target_pid}, "
            f"source_url={source_url!r}"
        )
    if target_url:
        known_t = db.execute(
            "SELECT 1 FROM documents WHERE source_url = ? LIMIT 1", (target_url,)
        ).fetchone()
        if not known_t:
            db.close()
            raise ValueError(
                f"store_tension: target_url not found in documents table — "
                f"likely hallucinated. source_pid={source_pid}, "
                f"target_pid={target_pid}, target_url={target_url!r}"
            )
    cursor = db.execute(
        """INSERT INTO political_tensions (source_pid, target_pid, topic, description, tension_type, source_url, target_url)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (source_pid, target_pid, topic, description, tension_type, source_url, target_url),
    )
    db.commit()
    tension_id = cursor.lastrowid
    db.close()
    return tension_id


def log_action(
    action: str,
    source_id: Optional[int] = None,
    opponent_id: Optional[int] = None,
    status: str = "success",
    duration_ms: Optional[int] = None,
    error_message: Optional[str] = None,
    details: Optional[dict] = None,
    claude_model: Optional[str] = None,
    prompt_hash: Optional[str] = None,
    db_path: str | None = None,
) -> None:
    db = get_db(db_path)
    db.execute(
        """INSERT INTO logs (timestamp, action, source_id, opponent_id, status, duration_ms,
           error_message, details, claude_model, prompt_hash)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (now_lv(), action, source_id, opponent_id, status, duration_ms, error_message,
         json.dumps(details) if details else None, claude_model, prompt_hash),
    )
    db.commit()
    db.close()


def get_last_log(
    action: Optional[str] = None,
    db_path: str | None = None,
) -> Optional[dict]:
    db = get_db(db_path)
    if action:
        row = db.execute(
            "SELECT * FROM logs WHERE action = ? ORDER BY timestamp DESC LIMIT 1",
            (action,),
        ).fetchone()
    else:
        row = db.execute(
            "SELECT * FROM logs ORDER BY timestamp DESC LIMIT 1"
        ).fetchone()
    db.close()
    return dict(row) if row else None
