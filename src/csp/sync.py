"""Sync pipeline: fetch CSP data and upsert into SQLite."""
import logging
import sqlite3
from datetime import datetime, timezone

from src.csp.client import fetch_table, parse_jsonstat2
from src.csp.tables import TABLES, FREQ_PERIODS_PER_YEAR


def _build_query_with_time(cfg: dict) -> list[dict]:
    """Append a TIME selection based on history_years × periods/year."""
    years = cfg.get("history_years", 5)
    stride = FREQ_PERIODS_PER_YEAR[cfg["freq"]]
    top_n = str(years * stride)
    return list(cfg["query"]) + [
        {"code": "TIME", "selection": {"filter": "top", "values": [top_n]}},
    ]

logger = logging.getLogger(__name__)


def upsert_rows(conn: sqlite3.Connection, table_id: str, freq: str, rows: list[dict]) -> int:
    """Insert or replace parsed rows into csp_data. Returns count."""
    now = datetime.now(timezone.utc).isoformat()
    count = 0
    for row in rows:
        if row["value"] is None:
            continue
        conn.execute(
            """INSERT OR REPLACE INTO csp_data
               (table_id, period, freq, geo, breakdown, value, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (table_id, row["period"], freq, "LV", row["breakdown"], row["value"], now),
        )
        count += 1
    conn.commit()
    return count


def populate_metadata_and_topics(conn: sqlite3.Connection) -> None:
    """Populate csp_metadata and topic_links from TABLES config."""
    for table_id, cfg in TABLES.items():
        conn.execute(
            """INSERT OR REPLACE INTO csp_metadata
               (table_id, label_lv, domain, freq, unit)
               VALUES (?, ?, ?, ?, ?)""",
            (table_id, cfg["label"], cfg["domain"], cfg["freq"], cfg["unit"]),
        )
        for topic in cfg["topics"]:
            conn.execute(
                """INSERT OR REPLACE INTO topic_links
                   (table_id, topic, keywords)
                   VALUES (?, ?, ?)""",
                (table_id, topic, ",".join(cfg["keywords"])),
            )
    conn.commit()


def sync_table(conn: sqlite3.Connection, table_id: str) -> int:
    """Fetch one table from CSP API and upsert. Returns row count."""
    cfg = TABLES[table_id]
    logger.info("Syncing %s (%s)...", table_id, cfg["label"])

    target = cfg["value_indicator"]
    count = 0

    # If table has an archive (CSP restructured some tables in 2024),
    # fetch archive data first so current data overwrites any overlap.
    archive = cfg.get("archive")
    if archive:
        try:
            arch_query = list(archive["query"]) + [
                {"code": "TIME", "selection": {"filter": "all", "values": ["*"]}},
            ]
            arch_data = fetch_table(archive["path"], arch_query)
            arch_rows = parse_jsonstat2(arch_data)
            arch_filtered = [r for r in arch_rows if r["indicator"] == target]
            arch_count = upsert_rows(conn, table_id, cfg["freq"], arch_filtered)
            count += arch_count
            logger.info("  → %d archive rows for %s", arch_count, table_id)
        except Exception as e:
            logger.warning("Archive fetch failed for %s: %s", table_id, e)

    data = fetch_table(cfg["path"], _build_query_with_time(cfg))
    rows = parse_jsonstat2(data)
    filtered = [r for r in rows if r["indicator"] == target]
    count += upsert_rows(conn, table_id, cfg["freq"], filtered)

    # Update metadata sync timestamp
    csp_updated = data.get("updated", "")
    conn.execute(
        "UPDATE csp_metadata SET last_sync=?, csp_updated=? WHERE table_id=?",
        (datetime.now(timezone.utc).isoformat(), csp_updated, table_id),
    )
    conn.commit()

    logger.info("  → %d total rows for %s", count, table_id)
    return count


def sync_all(conn: sqlite3.Connection) -> dict[str, int]:
    """Sync all configured tables. Returns {table_id: row_count}."""
    populate_metadata_and_topics(conn)
    results = {}
    for table_id in TABLES:
        try:
            results[table_id] = sync_table(conn, table_id)
        except Exception as e:
            logger.error("Failed to sync %s: %s", table_id, e)
            results[table_id] = 0
    return results
