"""
DB Migration: politracker.db → atmina.db

Copies the source database, strips all campaign-specific artefacts,
fixes the saeima_votes schema, adds missing Saeima deputies, and
re-matches individual votes to politician records.
"""

import json
import re
import shutil
import sqlite3
from pathlib import Path

SRC_DB = Path.home() / "OppTracker/politracker/politracker.db"
DST_DIR = Path(__file__).parent.parent / "data"
DST_DB = DST_DIR / "atmina.db"

# ---------------------------------------------------------------------------
# Keyword → topic mapping for saeima_votes.motif backfill
# ---------------------------------------------------------------------------
TOPIC_KEYWORDS: list[tuple[list[str], str]] = [
    (["aizsardzīb", "drošīb", "NATO", "militār"], "Aizsardzība un drošība"),
    (["Ukrain"], "Ukraina un Krievija"),
    (["budžet", "nodokl"], "Budžets un finanses"),
    (["izglītīb"], "Izglītība"),
    (["enerģ"], "Degviela un enerģētika"),
    (["imigrāc"], "Imigrācija"),
    (["vēlēšan"], "Vēlēšanas"),
    (["pašvaldīb"], "Pašvaldības"),
    (["transport"], "Transports"),
    (["meža"], "Mežsaimniecība"),
    (["vide"], "Vide"),
    (["tieslietu", "Kriminal"], "Tieslietas"),
    (["veselīb"], "Sociālā politika"),
    (["likumprojekt", "Saeimas kārtīb"], "Valsts pārvalde"),
]
DEFAULT_TOPIC = "Valsts pārvalde"

# ---------------------------------------------------------------------------
# Faction → party + relationship mapping
# ---------------------------------------------------------------------------
FACTION_PARTY: dict[str, str] = {
    "JV": "Jaunā Vienotība",
    "ZZS": "Zaļo un Zemnieku savienība",
    "NA": "Nacionālā apvienība",
    "PRO": "Progresīvie",
    "LPV": "Latvija Pirmajā Vietā",
    "AS": "Apvienotais saraksts",
    "LA": "Latvijas attīstībai",
    "K": "Konservatīvie",
}

FACTION_RELATIONSHIP: dict[str, str] = {
    "JV": "coalition_partner",
    "ZZS": "coalition_partner",
    "PRO": "coalition_partner",
    "NA": "opponent",
    "AS": "opponent",
    "LPV": "opponent",
}

# Campaign language patterns to purge from context_notes (case-insensitive)
CAMPAIGN_PATTERNS: list[str] = [
    r"MMN perspektīva",
    r"uzbrukuma leņķ",
    r"Mēs mainām noteikumus",
    r"kampaņas",
    r"Ieteikumi kampaņai",
    r"campaign_voice",
    r"party_ideology",
    r"MMN perspektīvā",
    r"pīlār",
]
CAMPAIGN_REGEX = re.compile(
    "|".join(CAMPAIGN_PATTERNS),
    re.IGNORECASE,
)


def infer_topic(motif: str | None) -> str:
    if not motif:
        return DEFAULT_TOPIC
    for keywords, topic in TOPIC_KEYWORDS:
        for kw in keywords:
            if kw.lower() in motif.lower():
                return topic
    return DEFAULT_TOPIC


def build_name_forms(full_name: str) -> list[str]:
    """Return [full_name, surname, 'Surname, Firstname'] variants."""
    parts = full_name.strip().split()
    forms = [full_name]
    if len(parts) >= 2:
        surname = parts[-1]
        firstname = parts[0]
        forms.append(surname)
        forms.append(f"{surname}, {firstname}")
    return forms


def name_matches(deputy_name: str, name_forms_json: str | None) -> bool:
    """Case-insensitive match of deputy_name against stored name_forms JSON."""
    if not name_forms_json:
        return False
    try:
        forms = json.loads(name_forms_json)
    except (json.JSONDecodeError, TypeError):
        return False
    deputy_lower = deputy_name.strip().lower()
    return any(deputy_lower == f.lower() for f in forms)


# ---------------------------------------------------------------------------
# Step 1 — Copy database
# ---------------------------------------------------------------------------
def step_copy() -> None:
    print(f"[1] Copying {SRC_DB} → {DST_DB}")
    DST_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SRC_DB, DST_DB)
    print(f"    Done. Size: {DST_DB.stat().st_size:,} bytes")


# ---------------------------------------------------------------------------
# Step 2-7 — Purge campaign artefacts
# ---------------------------------------------------------------------------
def step_purge(conn: sqlite3.Connection) -> None:
    c = conn.cursor()

    # 2. oppo_briefs
    c.execute("DELETE FROM oppo_briefs")
    print(f"[2] Deleted oppo_briefs: {c.rowcount} rows")

    # 3. mention_classifications
    c.execute("DELETE FROM mention_classifications")
    print(f"[3] Deleted mention_classifications: {c.rowcount} rows")

    # 4. context_notes — brief types
    c.execute(
        "DELETE FROM context_notes WHERE note_type IN ('daily_brief', 'weekly_brief')"
    )
    print(f"[4] Deleted daily_brief/weekly_brief context_notes: {c.rowcount} rows")

    # 5. context_notes — campaign language
    c.execute("SELECT id, content FROM context_notes")
    rows = c.fetchall()
    campaign_ids = [row[0] for row in rows if CAMPAIGN_REGEX.search(row[1] or "")]
    if campaign_ids:
        placeholders = ",".join("?" * len(campaign_ids))
        c.execute(
            f"DELETE FROM context_notes WHERE id IN ({placeholders})", campaign_ids
        )
    print(f"[5] Deleted campaign-language context_notes: {len(campaign_ids)} rows")

    # 6. documents — partijaMMN source URLs
    c.execute("DELETE FROM documents WHERE source_url LIKE '%partijaMMN%'")
    print(f"[6] Deleted partijaMMN documents: {c.rowcount} rows")

    # 7. social_accounts — partijaMMN handle
    c.execute("DELETE FROM social_accounts WHERE handle LIKE '%partijaMMN%'")
    print(f"[7] Deleted partijaMMN social_accounts: {c.rowcount} rows")

    conn.commit()


# ---------------------------------------------------------------------------
# Step 8 — Fix saeima_votes schema
# ---------------------------------------------------------------------------
def step_fix_schema(conn: sqlite3.Connection) -> None:
    c = conn.cursor()
    c.execute("PRAGMA table_info(saeima_votes)")
    existing_cols = {row[1] for row in c.fetchall()}

    added = []
    for col, col_type in [
        ("topic", "TEXT"),
        ("summary", "TEXT"),
        ("document_nr", "TEXT"),
        ("document_url", "TEXT"),
    ]:
        if col not in existing_cols:
            c.execute(f"ALTER TABLE saeima_votes ADD COLUMN {col} {col_type}")
            added.append(col)

    conn.commit()
    if added:
        print(f"[8] Added columns to saeima_votes: {added}")
    else:
        print("[8] saeima_votes schema already up-to-date — skipped")


# ---------------------------------------------------------------------------
# Step 9 — Backfill topic + summary for saeima_votes
# ---------------------------------------------------------------------------
def step_backfill_topics(conn: sqlite3.Connection) -> None:
    c = conn.cursor()
    c.execute("SELECT id, motif FROM saeima_votes WHERE topic IS NULL OR topic = ''")
    rows = c.fetchall()

    updated = 0
    for vote_id, motif in rows:
        topic = infer_topic(motif)
        summary = (motif or "")[:200]
        c.execute(
            "UPDATE saeima_votes SET topic = ?, summary = ? WHERE id = ?",
            (topic, summary, vote_id),
        )
        updated += 1

    conn.commit()
    print(f"[9] Backfilled topic/summary for {updated} saeima_votes rows")


# ---------------------------------------------------------------------------
# Step 10 — Add missing Saeima deputies
# ---------------------------------------------------------------------------
def step_add_deputies(conn: sqlite3.Connection) -> None:
    c = conn.cursor()

    # Collect existing names (from both name and name_forms)
    c.execute("SELECT name, name_forms FROM tracked_politicians")
    existing_rows = c.fetchall()
    existing_names_lower: set[str] = set()
    for name, name_forms_json in existing_rows:
        existing_names_lower.add(name.strip().lower())
        if name_forms_json:
            try:
                for f in json.loads(name_forms_json):
                    existing_names_lower.add(f.strip().lower())
            except (json.JSONDecodeError, TypeError):
                pass

    # Get distinct unmatched deputies
    c.execute(
        "SELECT DISTINCT deputy_name, faction "
        "FROM saeima_individual_votes WHERE politician_id IS NULL"
    )
    deputies = c.fetchall()

    inserted = 0
    skipped_dupe = 0

    for deputy_name, faction in deputies:
        deputy_lower = deputy_name.strip().lower()
        if deputy_lower in existing_names_lower:
            skipped_dupe += 1
            continue

        party = FACTION_PARTY.get(faction or "", "Nezināms")
        relationship = FACTION_RELATIONSHIP.get(faction or "", "neutral")
        name_forms = build_name_forms(deputy_name)
        name_forms_json = json.dumps(name_forms, ensure_ascii=False)

        c.execute(
            """
            INSERT INTO tracked_politicians
                (name, name_forms, party, role, relationship_type, created_at)
            VALUES (?, ?, ?, 'Saeimas deputāts', ?, datetime('now'))
            """,
            (deputy_name, name_forms_json, party, relationship),
        )

        # Track so we don't double-insert within this run
        for f in name_forms:
            existing_names_lower.add(f.strip().lower())

        inserted += 1

    conn.commit()
    print(
        f"[10] Deputies: inserted {inserted}, skipped (already exists) {skipped_dupe}"
    )


# ---------------------------------------------------------------------------
# Step 11 — Re-match saeima_individual_votes to politician_id
# ---------------------------------------------------------------------------
def step_rematch(conn: sqlite3.Connection) -> None:
    c = conn.cursor()

    # Load all politicians with their name_forms
    c.execute("SELECT id, name, name_forms FROM tracked_politicians")
    politicians = c.fetchall()

    # Build lookup: lowercase form → politician_id
    form_to_id: dict[str, int] = {}
    for pol_id, name, name_forms_json in politicians:
        # Always add the canonical name
        form_to_id[name.strip().lower()] = pol_id
        if name_forms_json:
            try:
                for f in json.loads(name_forms_json):
                    form_to_id[f.strip().lower()] = pol_id
            except (json.JSONDecodeError, TypeError):
                pass

    # Get all unmatched votes
    c.execute(
        "SELECT id, deputy_name FROM saeima_individual_votes WHERE politician_id IS NULL"
    )
    unmatched = c.fetchall()

    matched = 0
    still_unmatched = 0

    for vote_id, deputy_name in unmatched:
        deputy_lower = deputy_name.strip().lower()
        pol_id = form_to_id.get(deputy_lower)
        if pol_id is not None:
            c.execute(
                "UPDATE saeima_individual_votes SET politician_id = ? WHERE id = ?",
                (pol_id, vote_id),
            )
            matched += 1
        else:
            still_unmatched += 1

    conn.commit()
    print(
        f"[11] Re-matched votes: {matched} matched, {still_unmatched} still unmatched"
    )


# ---------------------------------------------------------------------------
# Step 12 — VACUUM
# ---------------------------------------------------------------------------
def step_vacuum(conn: sqlite3.Connection) -> None:
    print("[12] Running VACUUM...")
    conn.execute("VACUUM")
    print("     Done.")


# ---------------------------------------------------------------------------
# Step 13 — Verification stats
# ---------------------------------------------------------------------------
def step_verify(conn: sqlite3.Connection) -> None:
    c = conn.cursor()

    def count(table: str, where: str = "") -> int:
        sql = f"SELECT COUNT(*) FROM {table}"
        if where:
            sql += f" WHERE {where}"
        c.execute(sql)
        return c.fetchone()[0]

    print("\n=== Verification ===")
    print(f"  tracked_politicians:     {count('tracked_politicians')}")
    print(f"  documents:               {count('documents')}")
    print(f"  claims:                  {count('claims')}")
    print(f"  contradictions:          {count('contradictions')}")
    print(f"  saeima_votes:            {count('saeima_votes')}")
    print(f"  oppo_briefs:             {count('oppo_briefs')}")
    print(f"  mention_classifications: {count('mention_classifications')}")

    # Campaign-framed context_notes remaining
    c.execute("SELECT id, content FROM context_notes")
    rows = c.fetchall()
    campaign_remaining = sum(
        1 for row in rows if CAMPAIGN_REGEX.search(row[1] or "")
    )
    print(f"  campaign context_notes:  {campaign_remaining}")

    # partijaMMN accounts
    c.execute("SELECT COUNT(*) FROM social_accounts WHERE handle LIKE '%partijaMMN%'")
    print(f"  partijaMMN accounts:     {c.fetchone()[0]}")

    # saeima_votes topic column check
    c.execute("PRAGMA table_info(saeima_votes)")
    cols = {row[1] for row in c.fetchall()}
    print(f"  saeima_votes has topic:  {'topic' in cols}")

    # Unmatched deputies
    c.execute(
        "SELECT COUNT(DISTINCT deputy_name) FROM saeima_individual_votes "
        "WHERE politician_id IS NULL"
    )
    unmatched = c.fetchone()[0]
    print(f"  unmatched deputies:      {unmatched}")

    # Assertions
    assert count("oppo_briefs") == 0, "oppo_briefs not empty!"
    assert count("mention_classifications") == 0, "mention_classifications not empty!"
    assert campaign_remaining == 0, f"{campaign_remaining} campaign context_notes remain!"
    c.execute("SELECT COUNT(*) FROM social_accounts WHERE handle LIKE '%partijaMMN%'")
    assert c.fetchone()[0] == 0, "partijaMMN account still present!"
    assert count("tracked_politicians") >= 100, "Expected 100+ politicians!"
    assert "topic" in cols, "saeima_votes missing topic column!"
    print("\n  All assertions PASSED.")


# ---------------------------------------------------------------------------
# migrate_parties — add parties table and seed data
# ---------------------------------------------------------------------------
def migrate_parties(db: sqlite3.Connection) -> None:
    db.execute("""
        CREATE TABLE IF NOT EXISTS parties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            short_name TEXT NOT NULL UNIQUE,
            x_handle TEXT,
            website TEXT,
            ideology TEXT,
            coalition_status TEXT DEFAULT 'opposition',
            color TEXT,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_parties_short ON parties(short_name)"
    )

    seed = [
        ("Jaunā Vienotība", "JV", "JaunaVienotiba", "https://jv.lv", "Liberālkonservatīvisms", "coalition", "#2563eb"),
        ("Progresīvie", "PRO", "Progresivie_LV", "https://progresivie.lv", "Sociāldemokrātija, zaļā politika", "coalition", "#16a34a"),
        ("Zaļo un Zemnieku savienība", "ZZS", "zzs_lv", "https://zzs.lv", "Agrārisms, centrisms", "coalition", "#65a30d"),
        ("Nacionālā apvienība", "NA", "nacionala_apv", "https://nacionalaapvieniba.lv", "Nacionālkonservatīvisms", "coalition", "#dc2626"),
        ("Latvija Pirmajā Vietā", "LPV", "LPV_partija", "https://lpv.lv", "Populisms, centrisms", "opposition", "#eab308"),
        ("Apvienotais saraksts", "AS", "Apvienotais_", "https://apvienotais.lv", "Konservatīvisms", "opposition", "#8b5cf6"),
        ("Stabilitātei!", "MMN", None, None, "Prokrievisks, sociālkonservatīvisms", "opposition", "#64748b"),
    ]

    inserted = 0
    for name, short_name, x_handle, website, ideology, coalition_status, color in seed:
        cur = db.execute(
            """
            INSERT OR IGNORE INTO parties
                (name, short_name, x_handle, website, ideology, coalition_status, color)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (name, short_name, x_handle, website, ideology, coalition_status, color),
        )
        inserted += cur.rowcount

    db.commit()
    count = db.execute("SELECT COUNT(*) FROM parties").fetchone()[0]
    print(f"[parties] Inserted {inserted} new rows. Total rows: {count}")


# ---------------------------------------------------------------------------
# Step 13 — Migrate document_politicians junction table
# ---------------------------------------------------------------------------
def step_migrate_document_politicians(conn: sqlite3.Connection) -> None:
    """Migrate documents.opponent_id and mention_target_id to document_politicians junction table."""
    c = conn.cursor()

    # 1. Create junction table if not exists
    c.execute("""
        CREATE TABLE IF NOT EXISTS document_politicians (
            document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            politician_id INTEGER NOT NULL REFERENCES tracked_politicians(id),
            role TEXT NOT NULL DEFAULT 'subject',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (document_id, politician_id, role)
        )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_dp_politician ON document_politicians(politician_id, role)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_dp_document ON document_politicians(document_id)")

    # 2. Populate from existing opponent_id
    c.execute("""
        INSERT OR IGNORE INTO document_politicians (document_id, politician_id, role, created_at)
        SELECT id, opponent_id, 'subject', COALESCE(scraped_at, CURRENT_TIMESTAMP)
        FROM documents WHERE opponent_id IS NOT NULL
    """)
    migrated_subject = c.rowcount
    print(f"  Migrated {migrated_subject} opponent_id -> document_politicians (subject)")

    # 3. Populate from existing mention_target_id
    c.execute("""
        INSERT OR IGNORE INTO document_politicians (document_id, politician_id, role, created_at)
        SELECT id, mention_target_id, 'mention_target', COALESCE(scraped_at, CURRENT_TIMESTAMP)
        FROM documents WHERE mention_target_id IS NOT NULL
    """)
    migrated_mt = c.rowcount
    print(f"  Migrated {migrated_mt} mention_target_id -> document_politicians (mention_target)")

    # 4. Deduplicate x_mention documents
    dupes = c.execute("""
        SELECT source_url, MIN(id) AS keep_id, GROUP_CONCAT(id) AS all_ids, COUNT(*) AS cnt
        FROM documents
        WHERE platform = 'x_mention' AND source_url IS NOT NULL
        GROUP BY source_url, content
        HAVING COUNT(*) > 1
    """).fetchall()

    total_deleted = 0
    for dupe in dupes:
        keep_id = dupe[1]
        all_ids = [int(x) for x in dupe[2].split(",")]
        delete_ids = [did for did in all_ids if did != keep_id]

        if not delete_ids:
            continue

        for did in delete_ids:
            c.execute("""
                INSERT OR IGNORE INTO document_politicians (document_id, politician_id, role, created_at)
                SELECT ?, politician_id, role, created_at
                FROM document_politicians WHERE document_id = ?
            """, (keep_id, did))

            c.execute("UPDATE OR IGNORE mention_classifications SET document_id = ? WHERE document_id = ?",
                      (keep_id, did))
            c.execute("UPDATE claims SET document_id = ? WHERE document_id = ?", (keep_id, did))

        placeholders = ",".join("?" * len(delete_ids))
        c.execute(f"DELETE FROM document_politicians WHERE document_id IN ({placeholders})", delete_ids)
        c.execute(f"DELETE FROM documents WHERE id IN ({placeholders})", delete_ids)
        total_deleted += len(delete_ids)

    print(f"  Deduplicated x_mentions: removed {total_deleted} duplicate documents")

    # 5. Drop old indexes BEFORE dropping columns (SQLite requires this)
    c.execute("DROP INDEX IF EXISTS idx_documents_opponent")
    c.execute("DROP INDEX IF EXISTS idx_documents_mention_target")

    # 6. Drop old columns
    c.execute("ALTER TABLE documents DROP COLUMN opponent_id")
    c.execute("ALTER TABLE documents DROP COLUMN mention_target_id")
    print("  Dropped opponent_id and mention_target_id columns from documents")

    conn.commit()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    step_copy()

    conn = sqlite3.connect(DST_DB)
    try:
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute("PRAGMA journal_mode = WAL")

        step_purge(conn)
        step_fix_schema(conn)
        step_backfill_topics(conn)
        step_add_deputies(conn)
        step_rematch(conn)
        step_vacuum(conn)
        step_verify(conn)
    finally:
        conn.close()

    print(f"\nMigration complete → {DST_DB}")


def migrate_document_politicians() -> None:
    """Run the document_politicians migration on the live database."""
    db_path = DST_DIR / "atmina.db"
    print(f"[document_politicians] Migrating {db_path}")
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute("PRAGMA journal_mode = WAL")
        step_migrate_document_politicians(conn)
    finally:
        conn.close()
    print("[document_politicians] Migration complete.")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "document_politicians":
        migrate_document_politicians()
    else:
        main()
