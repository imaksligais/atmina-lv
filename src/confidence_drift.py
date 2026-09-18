"""Detect confidence inflation — familiarity confused with understanding."""

from datetime import timedelta
from pathlib import Path

from src.db import get_db, now_lv_dt

_DB_PATH = Path(__file__).parent.parent / "data" / "atmina.db"

# Minimums claims skaitam vienā pusē. Zem tā divu vidējo starpība nav mērījums,
# bet troksnis: 2026-08-24 Ārpolitikas brīdinājums salīdzināja divus n<=3
# paraugus, un 07-10 skaitlis nekad netika pārmērīts. Operatora verdikts
# 2026-09-07 (rinda 26): detektors rāda n abās pusēs un klusē, kad kāda puse
# ir zem šī sliekšņa. Brīdinājums bez saucēja ir vārti, kas nevar nokrist.
_MIN_HALF_CLAIMS = 5


def check_confidence_drift(
    db_path: str = None,
    days: int = 7,
    threshold: float = 0.15,
    min_half_claims: int = _MIN_HALF_CLAIMS,
) -> list[dict]:
    """
    Check if average confidence on any topic has risen >threshold over the past N days
    without new source diversity. Returns list of drifting topics.

    Filters to ``claim_type='position'`` only — Saeima voting records have
    hard-coded confidence=1.0 (votes are factual, not interpreted) and would
    otherwise swamp the drift signal with procedural noise. Confidence
    inflation is a rhetorical-coverage pathology, not a legislative one.

    A topic is skipped unless BOTH halves hold at least ``min_half_claims``
    rows (default ``_MIN_HALF_CLAIMS``); every returned alert carries both
    denominators (``first_half_claims`` / ``second_half_claims``), and
    ``format_drift_line()`` prints them.
    """
    db_path = db_path or str(_DB_PATH)
    db = get_db(db_path)

    cutoff = (now_lv_dt() - timedelta(days=days)).strftime("%Y-%m-%d")
    half = (now_lv_dt() - timedelta(days=days // 2)).strftime("%Y-%m-%d")

    topics = db.execute(
        "SELECT DISTINCT topic FROM claims WHERE stated_at >= ? AND claim_type = 'position'",
        (cutoff,),
    ).fetchall()

    alerts = []
    for row in topics:
        topic = row["topic"]

        first_half = db.execute("""
            SELECT AVG(confidence) as avg_conf, COUNT(*) as cnt,
                   COUNT(DISTINCT source_url) as sources
            FROM claims WHERE topic = ? AND stated_at >= ? AND stated_at < ?
              AND claim_type = 'position'
        """, (topic, cutoff, half)).fetchone()

        second_half = db.execute("""
            SELECT AVG(confidence) as avg_conf, COUNT(*) as cnt,
                   COUNT(DISTINCT source_url) as sources
            FROM claims WHERE topic = ? AND stated_at >= ?
              AND claim_type = 'position'
        """, (topic, half)).fetchone()

        if not first_half["avg_conf"] or not second_half["avg_conf"]:
            continue
        if first_half["cnt"] < min_half_claims or second_half["cnt"] < min_half_claims:
            continue

        drift = second_half["avg_conf"] - first_half["avg_conf"]
        source_growth = second_half["sources"] - first_half["sources"]

        if drift > threshold and source_growth <= 1:
            alerts.append({
                "topic": topic,
                "drift": round(drift, 3),
                "first_half_avg": round(first_half["avg_conf"], 3),
                "second_half_avg": round(second_half["avg_conf"], 3),
                "first_half_claims": first_half["cnt"],
                "second_half_claims": second_half["cnt"],
                "source_growth": source_growth,
            })

    db.close()
    alerts.sort(key=lambda x: x["drift"], reverse=True)
    return alerts


def format_drift_line(alert: dict) -> str:
    """Viena brīdinājuma rinda ar SAUCĒJU abās pusēs.

    Kopīga atskaitei un rutīnas statusam, lai n nevar pazust vienā no tiem.
    """
    return (
        f"{alert['topic']}: +{alert['drift']:.2f} "
        f"({alert['first_half_avg']:.2f} → {alert['second_half_avg']:.2f}), "
        f"n {alert['first_half_claims']} → {alert['second_half_claims']}, "
        f"jauni avoti: {alert['source_growth']}"
    )


def print_drift_report(alerts: list[dict]) -> None:
    if not alerts:
        print("Nav konstatēta confidence inflācija.")
        return
    print(f"⚠ {len(alerts)} tēmas ar confidence drift:\n")
    for a in alerts:
        print(f"  {format_drift_line(a)}")


if __name__ == "__main__":
    alerts = check_confidence_drift()
    print_drift_report(alerts)
