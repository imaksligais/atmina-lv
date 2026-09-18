"""KNAB lasīšanas puses vaicājumi (kopsavilkumi, ziedotāji, brīdinājumi).

Tikai SELECT — nekas šeit neraksta datubāzē.  Ielādi sk. ``src/knab/ingest.py``.
"""

from src.db import get_db

def get_party_summary(party: str | None = None, db_path: str | None = None) -> list[dict]:
    """Query donation summary per party.

    If *party* is given, filter to that party only.
    Returns list of dicts with: party, donation_count, total_eur,
    unique_donors, first_donation, last_donation, avg_donation.
    Ordered by total_eur DESC.
    """
    db = get_db(db_path)
    sql = """
        SELECT
            party,
            COUNT(*)          AS donation_count,
            SUM(amount_eur)   AS total_eur,
            COUNT(DISTINCT donor_name) AS unique_donors,
            MIN(date)         AS first_donation,
            MAX(date)         AS last_donation,
            ROUND(AVG(amount_eur), 2) AS avg_donation
        FROM knab_donations
    """
    params: list = []
    if party:
        sql += " WHERE party = ? "
        params.append(party)
    sql += " GROUP BY party ORDER BY total_eur DESC"

    rows = db.execute(sql, params).fetchall()
    db.close()
    return [dict(r) for r in rows]


def get_top_donors(
    limit: int = 20,
    party: str | None = None,
    db_path: str | None = None,
) -> list[dict]:
    """Top donors by total amount, optionally filtered by party (LIKE %party%).

    Returns list of dicts with: donor_name, donor_pid_masked, total_eur,
    donation_count, parties (GROUP_CONCAT DISTINCT).
    """
    db = get_db(db_path)
    sql = """
        SELECT
            donor_name,
            donor_pid_masked,
            SUM(amount_eur)   AS total_eur,
            COUNT(*)          AS donation_count,
            GROUP_CONCAT(DISTINCT party) AS parties
        FROM knab_donations
    """
    params: list = []
    if party:
        sql += " WHERE party LIKE ? "
        params.append(f"%{party}%")
    sql += " GROUP BY donor_name, donor_pid_masked ORDER BY total_eur DESC LIMIT ?"
    params.append(limit)

    rows = db.execute(sql, params).fetchall()
    db.close()
    return [dict(r) for r in rows]


def get_alerts(
    alert_type: str | None = None,
    severity: str | None = None,
    db_path: str | None = None,
) -> list[dict]:
    """Query knab_alerts with optional filters.

    Returns list of dicts ordered by created_at DESC.
    """
    db = get_db(db_path)
    clauses: list[str] = []
    params: list = []
    if alert_type:
        clauses.append("alert_type = ?")
        params.append(alert_type)
    if severity:
        clauses.append("severity = ?")
        params.append(severity)

    sql = "SELECT * FROM knab_alerts"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY created_at DESC"

    rows = db.execute(sql, params).fetchall()
    db.close()
    return [dict(r) for r in rows]
