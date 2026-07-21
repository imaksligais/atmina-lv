import hashlib
import json
import sqlite3
import struct
from datetime import datetime, timezone, timedelta, date
from pathlib import Path
from typing import Optional

from simhash import Simhash

from src.quality import validate_lv_diacritics

_SCHEMA_PATH = Path(__file__).parent / "schema.sql"

DB_PATH = "data/atmina.db"

# Latvia timezone: EET (UTC+2) winter, EEST (UTC+3) summer
# DST switches last Sunday of March (→ +3) and last Sunday of October (→ +2)
_LV_OFFSET = timedelta(hours=3)  # Current: EEST (summer 2026)

# Public stats cutoff: excludes the 2026-03-25..2026-04-04 testing era when the
# system was used as an MMN-party campaign tool (bulk MMN ingestion on 04-01,
# uneven per-politician coverage). Raw data stays in DB for audit, but public
# aggregates and leaderboards read from >= this date to avoid testing-bias.
CLEAN_START_DATE = "2026-04-05"


def now_lv() -> str:
    """Return current datetime as ISO string in Latvia time (EEST/EET)."""
    return (datetime.now(timezone.utc) + _LV_OFFSET).strftime("%Y-%m-%d %H:%M:%S")


def now_lv_dt() -> datetime:
    """Return current datetime as naive datetime in Latvia time (EEST/EET)."""
    return (datetime.now(timezone.utc) + _LV_OFFSET).replace(tzinfo=None)


def today_lv() -> date:
    """Return current date in Latvia time."""
    return now_lv_dt().date()


def init_db(db_path: str | None = None) -> None:
    db = get_db(db_path)

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

    # Migration: add published_at if missing
    cols = [r[1] for r in db.execute("PRAGMA table_info(documents)").fetchall()]
    if "published_at" not in cols:
        db.execute("ALTER TABLE documents ADD COLUMN published_at TIMESTAMP")

    # Migration: add mention_classifications table
    tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    if "mention_classifications" not in tables:
        db.execute("""CREATE TABLE IF NOT EXISTS mention_classifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER REFERENCES documents(id),
            category TEXT NOT NULL,
            priority INTEGER DEFAULT 0,
            reply_draft TEXT,
            reply_status TEXT DEFAULT 'pending',
            notes TEXT,
            created_at TIMESTAMP
        )""")
        db.execute("CREATE INDEX IF NOT EXISTS idx_mention_class_doc ON mention_classifications(document_id)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_mention_class_status ON mention_classifications(reply_status)")

    # Migration: add reviewed_at to documents
    if "reviewed_at" not in cols:
        db.execute("ALTER TABLE documents ADD COLUMN reviewed_at TIMESTAMP")

    # Migration: brief_images table + visual_brief_json column on context_notes
    # (Phase 2 of featured images feature — see docs/superpowers/specs/2026-04-17-featured-images-design.md)
    tables_now = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    if "brief_images" not in tables_now:
        db.execute("""
            CREATE TABLE brief_images (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                note_id       INTEGER NOT NULL REFERENCES context_notes(id),
                image_path    TEXT    NOT NULL,
                prompt        TEXT    NOT NULL,
                model         TEXT    NOT NULL,
                seed          INTEGER,
                aspect        TEXT    NOT NULL DEFAULT '16:9',
                width         INTEGER,
                height        INTEGER,
                generated_at  TEXT    NOT NULL,
                cost_usd      REAL    NOT NULL DEFAULT 0.039,
                approved      INTEGER NOT NULL DEFAULT 0,
                error_message TEXT
            )
        """)
        db.execute(
            "CREATE INDEX IF NOT EXISTS idx_brief_images_note_approved "
            "ON brief_images(note_id, approved, id DESC)"
        )

    cn_cols = {r[1] for r in db.execute("PRAGMA table_info(context_notes)").fetchall()}
    if "visual_brief_json" not in cn_cols:
        db.execute("ALTER TABLE context_notes ADD COLUMN visual_brief_json TEXT")

    # Migration: add engagement columns + title to documents (twitter/x_mention
    # platforms). twikit already extracts these; we were dropping them at insert.
    # See docs/superpowers/specs/2026-04-18-x-tab-v1-design.md §1. title was
    # added to live DB before schema.sql was updated; init_db must add it via
    # ALTER TABLE so tests building from schema.sql also have it.
    doc_cols = {r[1] for r in db.execute("PRAGMA table_info(documents)").fetchall()}
    for col in ("reply_count", "retweet_count", "favorite_count"):
        if col not in doc_cols:
            db.execute(f"ALTER TABLE documents ADD COLUMN {col} INTEGER")
    if "title" not in doc_cols:
        db.execute("ALTER TABLE documents ADD COLUMN title TEXT")
    # summary + is_paywall were also added to the live DB ahead of schema.sql.
    # summary is written by ingest paths (no render reader since the 2026-07
    # zinas dedup); is_paywall is written by video_ingest. Both stay mirrored
    # here so fresh/test DBs match prod column-for-column.
    if "summary" not in doc_cols:
        db.execute("ALTER TABLE documents ADD COLUMN summary TEXT")
    if "is_paywall" not in doc_cols:
        db.execute("ALTER TABLE documents ADD COLUMN is_paywall BOOLEAN DEFAULT FALSE")

    # Migration: add negative_patterns to tracked_politicians for
    # name-collision rejection (e.g. pid=146 Andris Bērziņš ZZS deputy vs.
    # former president of same name).
    tp_cols = [r[1] for r in db.execute("PRAGMA table_info(tracked_politicians)").fetchall()]
    if "negative_patterns" not in tp_cols:
        db.execute("ALTER TABLE tracked_politicians ADD COLUMN negative_patterns TEXT DEFAULT '[]'")
    # x_handle is live in production via ad-hoc migration but predated schema.sql.
    # It is SELECTed unconditionally by render_personas/parties/politicians; a
    # fresh init_db DB without it crashes those pages. Several test files already
    # ALTER it in defensively (try/except) — those workarounds no-op once this
    # migration runs.
    if "x_handle" not in tp_cols:
        db.execute("ALTER TABLE tracked_politicians ADD COLUMN x_handle TEXT")

    # 2026-04-23 — feed_type on social_accounts distinguishes first-party
    # speaker accounts (politician's own X, commentator, individual journalist
    # posting opinions) from relay accounts (institutional media X accounts
    # that post third-party quotes — LTV Ziņas, Delfi, TVNET). Relay accounts
    # must NOT be marked as subject of their own tweets — see src/social.py::
    # _store_tweets and src/ingest.py::link_politicians_to_documents. Default
    # 'first_party' preserves all existing account behavior.
    _sa_cols = {row[1] for row in db.execute("PRAGMA table_info(social_accounts)").fetchall()}
    if "feed_type" not in _sa_cols:
        db.execute("ALTER TABLE social_accounts ADD COLUMN feed_type TEXT DEFAULT 'first_party'")
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_social_feed_type ON social_accounts(feed_type)"
    )

    # 2026-04-25 — external_profiles tabula glabā ne-X (Facebook, website, YouTube
    # u.c.) profilus, ko politiķim varam parādīt UI un, vēlāk, fetchot. Atdalīta
    # no social_accounts, jo (a) social_accounts no šī brīža ir TIKAI X, (b) FB
    # rindas social_accounts tabulā nekad nav fetchotas (last_fetched IS NULL
    # visiem 18 ierakstiem) un piesārņoja unikalitātes statistiku. Schēma ir
    # paralēla social_accounts + papildus 'url' lauks, lai website rindām
    # 'handle' var palikt None.
    db.execute("""
        CREATE TABLE IF NOT EXISTS external_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            opponent_id INTEGER NOT NULL REFERENCES tracked_politicians(id),
            platform TEXT NOT NULL,
            url TEXT NOT NULL,
            handle TEXT,
            display_label TEXT,
            last_fetched TIMESTAMP,
            last_post_id TEXT,
            active BOOLEAN DEFAULT TRUE,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(opponent_id, platform, url)
        )
    """)
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_external_profiles_opp "
        "ON external_profiles(opponent_id)"
    )

    # 2026-04-23 — speaker_id separates the author of a claim from its subject.
    # First-party claims: speaker_id IS NULL (or = opponent_id). Third-party
    # commentary (relationship_type='commentator' author tweeting about a
    # tracked politician): speaker_id = commentator's tracked_politicians.id,
    # opponent_id = mentioned politician's id. Idempotent: PRAGMA check first.
    _claims_cols = {row[1] for row in db.execute("PRAGMA table_info(claims)").fetchall()}
    if "speaker_id" not in _claims_cols:
        db.execute("ALTER TABLE claims ADD COLUMN speaker_id INTEGER REFERENCES tracked_politicians(id)")
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_claims_speaker ON claims(speaker_id)"
    )
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_claims_opponent_speaker "
        "ON claims(opponent_id, speaker_id)"
    )

    # 2026-07-02 — party_id attributes a claim to a PARTY rather than an
    # individual. Used for party election-program promises
    # (claim_type='program_promise'): party_id = the party, opponent_id = the
    # list leader. Program promises are grouped to the party by party_id and
    # kept out of the leader's personal positions via claim_type filtering.
    # NULL for all ordinary politician claims. Idempotent: PRAGMA check first
    # (recomputed because speaker_id may have just been added above).
    _claims_cols = {row[1] for row in db.execute("PRAGMA table_info(claims)").fetchall()}
    if "party_id" not in _claims_cols:
        db.execute("ALTER TABLE claims ADD COLUMN party_id INTEGER REFERENCES parties(id)")
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_claims_party ON claims(party_id)"
    )

    db.commit()


def get_db(db_path: Optional[str] = None) -> sqlite3.Connection:
    # Resolve DB_PATH at CALL time, not def time. A default-argument
    # `db_path=DB_PATH` would bind the module global's value when this
    # function is defined, so a later `monkeypatch.setattr(db, "DB_PATH", ...)`
    # in a test would be a silent no-op and no-arg `get_db()` calls (e.g. the
    # matcher's `_load_politician_forms()`) would keep reading the live DB.
    # Resolving here makes DB_PATH overridable, which is what hermetic tests
    # rely on. Production never patches DB_PATH, so behaviour is unchanged.
    if db_path is None:
        db_path = DB_PATH
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
    db = get_db(db_path)
    content_hash = _compute_content_hash(content)

    # Check exact content_hash duplicate (same bytes already stored)
    existing = db.execute(
        "SELECT id FROM documents WHERE content_hash = ?", (content_hash,)
    ).fetchone()
    if existing:
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
            db.execute(
                """UPDATE documents
                   SET content=?, content_hash=?, simhash=?, word_count=?,
                       scraped_at=?, source_domain=COALESCE(source_domain, ?),
                       title=COALESCE(title, ?), published_at=COALESCE(published_at, ?)
                   WHERE id=?""",
                (content, content_hash, sim, word_count, now_lv(),
                 source_domain, title, published_at, existing_url["id"]),
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
    """Add a politician link to an existing document."""
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
    ``topic``, same ``stance``) — see BACKLOG.md § "SQLite write contention".
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

        # Diacritic guardrail — reject stripped Latvian text from agent context
        # drift. Skipped for saeima_vote claims because those are written by
        # generate_claims_from_votes() in src/saeima/votes.py with deterministic
        # template strings ("Saeimas balsojums DATE: NAME balsoja STANCE") that
        # legitimately contain politician names without diacritics — not
        # agent-stripped Latvian.
        if claim_type != "saeima_vote":
            for field_name, field_value in (
                ("stance", stance), ("quote", quote), ("reasoning", reasoning)
            ):
                ok, reason = validate_lv_diacritics(field_value)
                if not ok:
                    raise ValueError(
                        f"store_claim: {field_name} failed diacritic validation "
                        f"(opponent_id={opponent_id}): {reason}"
                    )

        # Defensive URL canonicalization — the document's source_url is
        # authoritative. If the caller passed a different URL (typically an
        # extractor agent that hallucinated a status ID or stripped a scheme),
        # silently override with the document's URL so that downstream dedup
        # and UI grouping use the canonical reference.
        doc_row = db.execute(
            "SELECT source_url FROM documents WHERE id = ?", (document_id,)
        ).fetchone()
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
        if embedding_bytes is None:
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


def delete_politician_data(politician_id: int, db_path: str | None = None) -> None:
    db = get_db(db_path)
    import sqlite_vec

    db.enable_load_extension(True)
    sqlite_vec.load(db)
    db.enable_load_extension(False)

    # Get documents exclusively owned by this politician (no other links)
    exclusive_doc_ids = [r[0] for r in db.execute("""
        SELECT dp.document_id FROM document_politicians dp
        WHERE dp.politician_id = ?
        AND NOT EXISTS (
            SELECT 1 FROM document_politicians dp2
            WHERE dp2.document_id = dp.document_id
            AND dp2.politician_id != ?
        )
    """, (politician_id, politician_id)).fetchall()]

    # Remove all junction rows for this politician
    db.execute("DELETE FROM document_politicians WHERE politician_id = ?", (politician_id,))

    # Get chunk IDs from exclusively-owned documents
    if exclusive_doc_ids:
        placeholders = ",".join("?" * len(exclusive_doc_ids))
        chunk_ids = [
            r["id"]
            for r in db.execute(
                f"SELECT id FROM document_chunks WHERE document_id IN ({placeholders})",
                exclusive_doc_ids,
            ).fetchall()
        ]
        # Delete vectors for those chunks
        for cid in chunk_ids:
            db.execute("DELETE FROM document_vectors WHERE chunk_id = ?", (cid,))
        # Delete chunks
        db.execute(
            f"DELETE FROM document_chunks WHERE document_id IN ({placeholders})",
            exclusive_doc_ids,
        )
        # Delete exclusively-owned documents
        db.execute(
            f"DELETE FROM documents WHERE id IN ({placeholders})",
            exclusive_doc_ids,
        )

    # Get claim IDs for this politician
    claim_ids = [
        r["id"]
        for r in db.execute(
            "SELECT id FROM claims WHERE opponent_id = ?", (politician_id,)
        ).fetchall()
    ]
    # Delete claim vectors
    for cid in claim_ids:
        db.execute("DELETE FROM claim_vectors WHERE claim_id = ?", (cid,))

    # Delete from all related tables
    db.execute("DELETE FROM claims WHERE opponent_id = ?", (politician_id,))
    db.execute("DELETE FROM contradictions WHERE opponent_id = ?", (politician_id,))
    db.execute("DELETE FROM analyses WHERE opponent_id = ?", (politician_id,))
    db.execute("DELETE FROM oppo_briefs WHERE opponent_id = ?", (politician_id,))
    db.execute("DELETE FROM context_notes WHERE opponent_id = ?", (politician_id,))
    db.execute("DELETE FROM social_accounts WHERE opponent_id = ?", (politician_id,))
    db.execute("DELETE FROM logs WHERE opponent_id = ?", (politician_id,))
    db.execute("DELETE FROM tracked_politicians WHERE id = ?", (politician_id,))

    db.commit()
    db.close()
