"""Hand-rolled migration ladder for the atmina SQLite DB.

Carved out of ``src.db.init_db`` on 2026-09-05 (plan
docs/plans/2026-09-05-strukturas-tirisanas-plans.md § 5.3). Pure move: the
statements, their ORDER, and every comment below are unchanged — the comments
are the design record for why each column/index/trigger exists, and several of
them are the only place a measurement lives.

Contract (unchanged from init_db): every step is IDEMPOTENT and SELF-HEALING.
It runs on every ``init_db()`` — fresh test DBs built from ``schema.sql`` and
the live DB alike — so each step must PRAGMA-check (or use
``IF NOT EXISTS`` / ``DROP ... IF EXISTS``) before writing. Nothing here
commits; the caller owns the transaction.

Why this ladder exists at all rather than living in ``schema.sql``:
``executescript()`` runs the static DDL first, so anything that must ALTER an
EXISTING production table (a column added to the live DB ahead of the schema
file) can only be applied afterwards.
"""

import sqlite3

from src.db import _REVIEW_STATUS_AT_EXPR, _REVIEW_STATUS_EXPR

# The trigger body both claims_review_status_* triggers share. Written once so
# the INSERT and UPDATE paths can never disagree — the same reason
# _REVIEW_STATUS_EXPR itself lives in src.db.
#
# review_status_at is stamped ONLY when the derived status actually changes.
# Inside an UPDATE's SET list SQLite evaluates every right-hand side against
# the row's PRE-update values, so the bare `review_status` in the CASE is the
# OLD status and the comparison is old-vs-new. `IS NOT` (not `<>`) because both
# sides are NULL for an ordinary claim. Consequence worth relying on: a purely
# stylistic edit to `reasoning` that leaves the marker in place does NOT reset
# the row's age — otherwise every touch would launder exactly what the 14-day
# gate measures.
_REVIEW_STATUS_SET = (
    f"review_status_at = CASE WHEN review_status IS NOT ({_REVIEW_STATUS_EXPR}) "
    f"THEN {_REVIEW_STATUS_AT_EXPR} ELSE review_status_at END, "
    f"review_status = {_REVIEW_STATUS_EXPR}"
)


def apply_migrations(db: sqlite3.Connection) -> None:
    """Bring `db` up to the current schema. Idempotent; does not commit."""
    # Migration: add published_at if missing
    cols = [r[1] for r in db.execute("PRAGMA table_info(documents)").fetchall()]
    if "published_at" not in cols:
        db.execute("ALTER TABLE documents ADD COLUMN published_at TIMESTAMP")

    # Migration: add reviewed_at to documents
    if "reviewed_at" not in cols:
        db.execute("ALTER TABLE documents ADD COLUMN reviewed_at TIMESTAMP")

    # Migration: brief_images table + visual_brief_json column on context_notes
    # (Phase 2 of featured images feature — see docs/superpowers/specs/2026-04-17-featured-images-design.md)
    # DDL kanoniski dzīvo src/schema.sql (promovēts 2026-08-21 ar image_path +
    # approved domēna dokumentāciju pie kolonnām); šis bloks paliek kā
    # bezdarbības sargs vecākām DB, kuras veidotas pirms promovēšanas.
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

    # 2026-08-18 — publish_approvals: operatora EKSPLICĪTĀ publicēšanas atļauja
    # (T15 atlikums). Publish-gate v1 lasīja `brief_images.approved=1`, bet
    # attēla apstiprinājums pierāda tikai to, ka attēls ir izvēlēts — korektūra,
    # quality-reviewer un atļauja tur nav, tāpēc melnraksts ar apstiprinātu
    # attēlu vārtus izietu.
    #
    # Atslēga ir BLOG LAPAS SLUGS (`YYYY-MM-DD`, nedēļas pārskatam
    # `nedela-YYYY-MM-DD`) — nevis `context_notes.id`. Tās pašas dienas brief
    # tiek UPSERTots un vēsturiski arī pārrakstīts ar jaunu id; pie note id
    # sasieta atļauja tādā regenerācijā klusi pazustu (vai, sliktāk, paliktu
    # sasieta pie dzēsta ieraksta). Slugs ir tas pats fakts, uz kuru skatās
    # deploy vārti, tāpēc tie divi nevar aizdreifēt.
    db.execute("""
        CREATE TABLE IF NOT EXISTS publish_approvals (
            subject_key TEXT PRIMARY KEY,
            approved_at TEXT NOT NULL
        )
    """)

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

    # 2026-08-06 — contradictions.party_id spoguļo claims.party_id ŠAURAJAI
    # partiju pretrunu klasei (programmas solījums pret frakcijas balsojuma
    # vairākumu; plāns docs/plans/2026-08-06-partiju-pretrunu-saura-versija.md).
    # Aizpildīts TIKAI šai klasei; visām pārējām rindām NULL. Retorikas-pret-
    # balsojumiem plašā versija ir apzināti noraidīta — nelieto šo kolonnu tai.
    _contra_cols = {row[1] for row in db.execute("PRAGMA table_info(contradictions)").fetchall()}
    if "party_id" not in _contra_cols:
        db.execute("ALTER TABLE contradictions ADD COLUMN party_id INTEGER REFERENCES parties(id)")

    # 2026-08-03 — review_status makes the NEEDS_REVIEW queue queryable.
    #
    # The flag used to exist only as text inside `claims.reasoning`, which broke
    # in three independent ways: the marker FORM drifted (REVIEWED -> Izvērtēts
    # -> REVIEWED, so each query went blind in turn), the marker POSITION
    # drifted (measured 2026-08-03: 20 of 119 open rows prefixed, so the
    # anchored `LIKE 'NEEDS_REVIEW%'` that CLAUDE.md's escalation rule 2 implies
    # returned 17 % of the queue and silently dropped the rest), and nothing
    # could count or age the queue, so nothing did — 78 rows sat inside the
    # 7-day window unresolved. Choosing one marker spelling would have fixed
    # only the first of the three.
    #
    # DERIVED, never hand-written. Two triggers maintain it: one on INSERT, one
    # on UPDATE OF reasoning. The second is the load-bearing one — triage
    # resolves a flag with `UPDATE claims SET reasoning = REPLACE(...)` in
    # ad-hoc SQL that never passes through store_claim(), so a column
    # maintained only on the write path would be right at insert and wrong from
    # the first resolution onward. These are the repo's first triggers, and the
    # reason to accept that is the standing scar in CLAUDE.md § "Write through
    # the store_*() functions": a guardrail that lives in a function is one raw
    # INSERT away from being bypassed.
    _claims_cols = {row[1] for row in db.execute("PRAGMA table_info(claims)").fetchall()}
    if "review_status" not in _claims_cols:
        db.execute("ALTER TABLE claims ADD COLUMN review_status TEXT")
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_claims_review_status ON claims(review_status)"
    )
    # 2026-09-07 — review_status_at: WHEN the marker was applied (verdict 44).
    #
    # The 14-day review gate measured age from `claims.created_at`, so it could
    # not tell "rotting in the queue since April" from "retro-marked
    # yesterday". On 2026-08-22 it reported a BAR BREACH over 19 rows that had
    # entered the queue the previous day — a real piece of work named with the
    # wrong reason, and it would have repeated at every retro-marking pass
    # (backlog/matcher.md § "14 dienu vārti mēra created_at"). The rejected
    # alternative was parsing the `Izvērtēts` date back out of the prose, which
    # is exactly what the 2026-08-03 decision forbade.
    #
    # DERIVED like review_status itself — maintained by the SAME two triggers,
    # never hand-written. NO BACKFILL: nobody recorded when historical rows
    # were marked, so they stay NULL and readers use
    # `COALESCE(review_status_at, created_at)` (src.db.REVIEW_AGE_EXPR). NULL
    # falls back to the OLDER timestamp, i.e. the fail-loud side — a row that
    # should breach the gate keeps breaching it instead of being quietly
    # excused by today's date.
    if "review_status_at" not in _claims_cols:
        db.execute("ALTER TABLE claims ADD COLUMN review_status_at TIMESTAMP")
    # Recreated unconditionally so a schema change here reaches existing DBs;
    # CREATE TRIGGER has no "OR REPLACE", hence the drops.
    # FORMATTING CONSTRAINT — do not "tidy" these onto more lines. The body's
    # `; END` must stay on ONE line, because the schema baseline in
    # tests/test_schema.py round-trips sqlite_master by splitting on ";\n". A
    # trigger whose inner statement ends a line gets shredded into two
    # fragments, and the baseline then fails to re-assert after REGEN.
    db.execute("DROP TRIGGER IF EXISTS claims_review_status_ai")
    db.execute("DROP TRIGGER IF EXISTS claims_review_status_au")
    db.execute(f"""
        CREATE TRIGGER claims_review_status_ai AFTER INSERT ON claims
        BEGIN UPDATE claims SET {_REVIEW_STATUS_SET}
        WHERE id = NEW.id; END
    """)
    db.execute(f"""
        CREATE TRIGGER claims_review_status_au AFTER UPDATE OF reasoning ON claims
        BEGIN UPDATE claims SET {_REVIEW_STATUS_SET}
        WHERE id = NEW.id; END
    """)
    # Backfill: classify every row the triggers never saw. Cheap to re-run and
    # self-healing, so it is NOT gated on the ALTER above — a DB whose triggers
    # were dropped, or whose rows predate them, is repaired by the next
    # init_db() instead of drifting silently.
    #
    # It repairs review_status ONLY, and deliberately leaves review_status_at
    # alone: it can tell that a row's status is wrong, not WHEN the reasoning
    # that makes it wrong was written. Stamping "now" here would hand every
    # repaired row a fresh 14-day grace period on no evidence.
    db.execute(f"""
        UPDATE claims SET review_status = {_REVIEW_STATUS_EXPR}
        WHERE review_status IS NOT {_REVIEW_STATUS_EXPR}
    """)

    # 2026-08-04 — extracted_at padara ekstrakcijas rindu per-(dokuments,
    # politiķis), ne per-dokuments. `documents.reviewed_at` ir dokumenta
    # līmeņa: ja doks ar subject A un citētu mentioned B tiek apstrādāts A
    # slotā vispirms, doks pamet rindu un B citāti pazūd — junction inversijas
    # klase (docs/plans/2026-08-04-junction-inversion-queue-fix.md,
    # scripts/audit_junction_role_inversion.py). save_analysis() to zīmogo
    # analizētā politiķa junction rindām (gan claims, gan empty iznākumā);
    # mentioned josla filtrē pēc tā, subject joslas reviewed_at semantika
    # paliek neskarta. NAV schema.sql (executescript pirms ALTER — tas pats
    # paterns kā idx_claims_party).
    _dp_cols = {row[1] for row in db.execute("PRAGMA table_info(document_politicians)").fetchall()}
    if "extracted_at" not in _dp_cols:
        db.execute("ALTER TABLE document_politicians ADD COLUMN extracted_at TIMESTAMP")
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_dp_extracted "
        "ON document_politicians(politician_id, extracted_at)"
    )

    # 2026-08-03 — source_url index: keeps the partial-write safety check RUNNABLE.
    #
    # `store_vote()` commits the vote before generating its claims, so the query
    # "which votes have no claim at all" (NOT EXISTS ... c.source_url = v.url) is
    # the one check that proves a bulk load did not half-finish. Without an index
    # it is a full scan of `claims` per vote.
    #
    # Measured 2026-08-03 on the live DB (574 130 claims, 6 867 votes) — both
    # directions, because the write side is what made this a decision rather than
    # an obvious yes:
    #   read : 935.5 s -> 0.0 s
    #   write: 0.120 -> 0.133 ms/row (+10.8 %), i.e. ~2 s across the whole
    #          planned 140k-claim 2025 Saeima load
    #   size : +61 MB (1992.5 -> 2053.2 MB)
    # BACKLOG had this query recorded as ">120 s"; it had degraded to 15.6
    # minutes. A safety check that gets slower with the data is one that quietly
    # stops being run, which is exactly how a partial write would survive.
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_claims_source_url ON claims(source_url)"
    )

    # 2026-09-07 (verdikts 47b) — image_audit: VIENS saucējs attēlu mēneša
    # budžetam. DDL kanoniski dzīvo src/schema.sql; šis bloks ir sargs vecākām
    # DB, kas veidotas pirms tās promovēšanas, PLUS vienreizējais backfill no
    # `brief_images`.
    #
    # Backfill ir obligāts, ne kosmētisks: `monthly_cost_usd()` pēc šīs izmaiņas
    # lasa image_audit, tāpēc bez vēstures kopijas šī mēneša tēriņš klusi
    # nokristu uz 0,00 USD un budžeta vārti pārstātu kaut ko sargāt (2026-09-07
    # mērījums: 311 brief_images rindas, šis mēnesis 16 rindas / 0,6240 USD).
    # NOT EXISTS + unikālais (source_table, source_id) indekss to padara
    # idempotentu — atkārtots apply_migrations() dublikātus neražo.
    if "image_audit" not in tables_now:
        db.execute("""
            CREATE TABLE image_audit (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                generated_at  TEXT    NOT NULL,
                kind          TEXT    NOT NULL,
                model         TEXT    NOT NULL,
                aspect        TEXT    NOT NULL DEFAULT '16:9',
                prompt        TEXT    NOT NULL,
                cost_usd      REAL    NOT NULL DEFAULT 0.0,
                status        TEXT    NOT NULL DEFAULT 'ok',
                error_message TEXT,
                source_table  TEXT,
                source_id     INTEGER
            )
        """)
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_image_audit_generated "
        "ON image_audit(generated_at)"
    )
    db.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_image_audit_source "
        "ON image_audit(source_table, source_id) WHERE source_table IS NOT NULL"
    )
    # `brief_images` šajā punktā eksistē vienmēr — vai nu no schema.sql, vai no
    # augstākā bloka, kas to izveido vecākām DB.
    db.execute("""
        INSERT INTO image_audit
            (generated_at, kind, model, aspect, prompt, cost_usd, status,
             error_message, source_table, source_id)
        SELECT
            bi.generated_at,
            CASE WHEN bi.image_path LIKE 'images/synthesis/%'
                 THEN 'synthesis' ELSE 'brief' END,
            bi.model, bi.aspect, bi.prompt, bi.cost_usd,
            CASE WHEN bi.image_path = '' THEN 'error' ELSE 'ok' END,
            bi.error_message, 'brief_images', bi.id
        FROM brief_images bi
        WHERE NOT EXISTS (
            SELECT 1 FROM image_audit ia
            WHERE ia.source_table = 'brief_images' AND ia.source_id = bi.id
        )
    """)
