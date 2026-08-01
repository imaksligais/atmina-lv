"""KNAB cross-referencing and anomaly detection.

Matches KNAB donors to tracked politicians, detects multi-party donors,
family donation clusters, annual limit violations, and donation/declaration
mismatches.
"""

import json
from collections import defaultdict

from src.db import get_db, now_lv

# ---------------------------------------------------------------------------
# Name normalisation
# ---------------------------------------------------------------------------

_LV_TRANS = str.maketrans(
    "āčēģīķļņōŗšūžĀČĒĢĪĶĻŅŌŖŠŪŽ",
    "acegiklnorsuzACEGIKLNORSUZ",
)


def _normalize_name(name: str) -> str:
    """Normalize a Latvian name for fuzzy matching.

    Lowercase, transliterate diacritics, collapse whitespace.
    """
    return " ".join(name.translate(_LV_TRANS).lower().split())


# ---------------------------------------------------------------------------
# 1. Link donors to politicians
# ---------------------------------------------------------------------------


def link_donors_to_politicians(db_path: str | None = None) -> int:
    """Match knab_donors to tracked_politicians by name/name_forms.

    Builds a lookup dict from politician names + name_forms JSON array,
    then updates knab_donors.politician_id where a normalised match is found.
    Returns count of newly linked donors.
    """
    db = get_db(db_path)

    # Build lookup: normalised name -> politician id
    lookup: dict[str, int] = {}
    politicians = db.execute("SELECT id, name, name_forms FROM tracked_politicians").fetchall()
    for row in politicians:
        pid = row["id"]
        lookup[_normalize_name(row["name"])] = pid
        forms_raw = row["name_forms"] or "[]"
        try:
            forms = json.loads(forms_raw)
        except (json.JSONDecodeError, TypeError):
            forms = []
        for form in forms:
            if isinstance(form, str) and form.strip():
                lookup[_normalize_name(form)] = pid

    # Match donors
    donors = db.execute(
        "SELECT id, name FROM knab_donors WHERE politician_id IS NULL"
    ).fetchall()

    linked = 0
    for donor in donors:
        norm = _normalize_name(donor["name"])
        if norm in lookup:
            db.execute(
                "UPDATE knab_donors SET politician_id = ? WHERE id = ?",
                (lookup[norm], donor["id"]),
            )
            linked += 1

    db.commit()
    db.close()
    print(f"[KNAB] Linked {linked} donors to politicians")
    return linked


# ---------------------------------------------------------------------------
# 2. Multi-party donors
# ---------------------------------------------------------------------------


def detect_multi_party_donors(db_path: str | None = None) -> list[dict]:
    """Find donors who gave to 2+ different parties.

    Groups by donor_name + donor_pid_masked. Stores alerts in knab_alerts.
    Returns list sorted by total_eur DESC.
    """
    db = get_db(db_path)

    # Clear previous alerts of this type
    db.execute("DELETE FROM knab_alerts WHERE alert_type = 'multi_party_donor'")

    rows = db.execute("""
        SELECT donor_name, donor_pid_masked,
               COUNT(DISTINCT party) AS party_count,
               GROUP_CONCAT(DISTINCT party) AS parties,
               SUM(amount_eur) AS total_eur
        FROM knab_donations
        GROUP BY donor_name, donor_pid_masked
        HAVING COUNT(DISTINCT party) >= 2
        ORDER BY total_eur DESC
    """).fetchall()

    results = []
    for r in rows:
        data = {
            "donor_name": r["donor_name"],
            "donor_pid_masked": r["donor_pid_masked"],
            "party_count": r["party_count"],
            "parties": r["parties"],
            "total_eur": r["total_eur"],
        }
        severity = "warning" if r["party_count"] >= 3 else "info"
        db.execute(
            """INSERT INTO knab_alerts
               (alert_type, severity, title, description, data, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                "multi_party_donor",
                severity,
                f"{r['donor_name']} ziedojis {r['party_count']} partijām",
                f"Kopā: EUR {r['total_eur']:.2f}. Partijas: {r['parties']}",
                json.dumps(data, ensure_ascii=False),
                now_lv(),
            ),
        )
        results.append(data)

    db.commit()
    db.close()
    print(f"[KNAB] Found {len(results)} multi-party donors")
    return results


# ---------------------------------------------------------------------------
# 3. Family clusters
# ---------------------------------------------------------------------------


def detect_family_clusters(db_path: str | None = None) -> list[dict]:
    """Find same-surname donation clusters within the same party.

    Surname = last word of the name. Groups by normalised surname + party.
    Only flags clusters with 2+ members AND total >= EUR 1000.
    Stores alerts in knab_alerts. Returns sorted by total_eur DESC.
    """
    db = get_db(db_path)

    # Clear previous alerts of this type
    db.execute("DELETE FROM knab_alerts WHERE alert_type = 'family_cluster'")

    rows = db.execute("""
        SELECT donor_name, donor_pid_masked, party, SUM(amount_eur) AS donor_total
        FROM knab_donations
        GROUP BY donor_name, donor_pid_masked, party
    """).fetchall()

    # Group by (normalised surname, party)
    clusters: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in rows:
        name = r["donor_name"]
        parts = _normalize_name(name).split()
        if not parts:
            continue
        surname = parts[-1]
        key = (surname, r["party"])
        clusters[key].append({
            "donor_name": r["donor_name"],
            "donor_pid_masked": r["donor_pid_masked"],
            "donor_total": r["donor_total"],
        })

    results = []
    for (surname, party), members in clusters.items():
        if len(members) < 2:
            continue
        total_eur = sum(m["donor_total"] for m in members)
        if total_eur < 1000:
            continue
        data = {
            "surname": surname,
            "party": party,
            "member_count": len(members),
            "total_eur": total_eur,
            "members": [m["donor_name"] for m in members],
        }
        db.execute(
            """INSERT INTO knab_alerts
               (alert_type, severity, party, title, description, data, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                "family_cluster",
                "warning",
                party,
                f"Ģimenes klasteris: {surname} ({len(members)} personas)",
                f"Kopā: EUR {total_eur:.2f} partijai {party}",
                json.dumps(data, ensure_ascii=False),
                now_lv(),
            ),
        )
        results.append(data)

    results.sort(key=lambda x: x["total_eur"], reverse=True)
    db.commit()
    db.close()
    print(f"[KNAB] Found {len(results)} family clusters")
    return results


# ---------------------------------------------------------------------------
# 4. Limit violations
# ---------------------------------------------------------------------------


def detect_limit_violations(db_path: str | None = None, limit_eur: float = 35000) -> list[dict]:
    """Find donors exceeding annual per-party donation limits.

    Groups by donor + party + year, flags where total > limit_eur.
    Stores alerts with severity 'critical'. Returns list of violations.
    """
    db = get_db(db_path)

    # Clear previous alerts of this type
    db.execute("DELETE FROM knab_alerts WHERE alert_type = 'limit_violation'")

    rows = db.execute("""
        SELECT donor_name, donor_pid_masked, party,
               SUBSTR(date, 1, 4) AS year,
               SUM(amount_eur) AS total_eur,
               COUNT(*) AS donation_count
        FROM knab_donations
        GROUP BY donor_name, donor_pid_masked, party, SUBSTR(date, 1, 4)
        HAVING SUM(amount_eur) > ?
        ORDER BY total_eur DESC
    """, (limit_eur,)).fetchall()

    results = []
    for r in rows:
        data = {
            "donor_name": r["donor_name"],
            "donor_pid_masked": r["donor_pid_masked"],
            "party": r["party"],
            "year": r["year"],
            "total_eur": r["total_eur"],
            "donation_count": r["donation_count"],
            "limit_eur": limit_eur,
            "excess_eur": r["total_eur"] - limit_eur,
        }
        db.execute(
            """INSERT INTO knab_alerts
               (alert_type, severity, party, title, description, data, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                "limit_violation",
                "critical",
                r["party"],
                f"{r['donor_name']} pārsniedz limitu {r['year']}",
                f"Kopā: EUR {r['total_eur']:.2f} (limits: EUR {limit_eur:.2f}, pārsniegums: EUR {data['excess_eur']:.2f})",
                json.dumps(data, ensure_ascii=False),
                now_lv(),
            ),
        )
        results.append(data)

    db.commit()
    db.close()
    print(f"[KNAB] Found {len(results)} limit violations")
    return results


# ---------------------------------------------------------------------------
# 5. Donation vs declaration mismatch
# ---------------------------------------------------------------------------


def detect_donation_declaration_mismatch(db_path: str | None = None) -> list[dict]:
    """Compare sum of KNAB ziedojumi (Nauda + Manta vai pakalpojums) per party/year
    vs declared income_donations.

    Biedru nauda is excluded because KNAB does not publish all membership fees.
    Only flags discrepancies > 10%. Stores alerts. Returns list of mismatches.
    Note: will often return empty until declaration detail pages are scraped.
    """
    db = get_db(db_path)

    # Clear previous alerts of this type
    db.execute("DELETE FROM knab_alerts WHERE alert_type = 'donation_declaration_mismatch'")

    # Sum only ziedojumi (Nauda + Manta vai pakalpojums) per party/year.
    # Biedru nauda is excluded because KNAB does not publish all membership fees.
    donation_sums = db.execute("""
        SELECT party, SUBSTR(date, 1, 4) AS year, SUM(amount_eur) AS donation_total
        FROM knab_donations
        WHERE donation_type IN ('Nauda', 'Manta vai pakalpojums')
        GROUP BY party, SUBSTR(date, 1, 4)
    """).fetchall()

    results = []
    for ds in donation_sums:
        party = ds["party"]
        year = ds["year"]
        donation_total = ds["donation_total"]

        # Find matching declaration
        decl = db.execute("""
            SELECT income_donations FROM knab_declarations
            WHERE party = ? AND year = ? AND income_donations IS NOT NULL
            LIMIT 1
        """, (party, int(year))).fetchone()

        if not decl or decl["income_donations"] is None:
            continue

        declared = decl["income_donations"]
        if declared == 0 and donation_total == 0:
            continue

        # Calculate discrepancy relative to the larger value
        reference = max(abs(declared), abs(donation_total))
        if reference == 0:
            continue
        discrepancy_pct = abs(donation_total - declared) / reference * 100

        if discrepancy_pct <= 10:
            continue

        data = {
            "party": party,
            "year": year,
            "donation_total": donation_total,
            "declared_donations": declared,
            "discrepancy_pct": round(discrepancy_pct, 1),
        }
        severity = "critical" if discrepancy_pct > 50 else "warning"
        db.execute(
            """INSERT INTO knab_alerts
               (alert_type, severity, party, title, description, data, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                "donation_declaration_mismatch",
                severity,
                party,
                f"Ziedojumu/deklarācijas neatbilstība: {party} ({year})",
                f"Ziedojumi (bez biedru naudas): EUR {donation_total:.2f}, deklarēts: EUR {declared:.2f} ({discrepancy_pct:.1f}% starpība)",
                json.dumps(data, ensure_ascii=False),
                now_lv(),
            ),
        )
        results.append(data)

    db.commit()
    db.close()
    print(f"[KNAB] Found {len(results)} donation/declaration mismatches")
    return results


# ---------------------------------------------------------------------------
# 6. Run all checks
# ---------------------------------------------------------------------------


def run_all_checks(db_path: str | None = None) -> dict:
    """Run all KNAB cross-referencing and anomaly detection checks.

    Prints summary. Returns dict with counts for each check.
    """
    print("[KNAB] Running cross-reference checks...")

    linked = link_donors_to_politicians(db_path)
    multi = detect_multi_party_donors(db_path)
    families = detect_family_clusters(db_path)
    violations = detect_limit_violations(db_path)
    mismatches = detect_donation_declaration_mismatch(db_path)

    summary = {
        "linked_donors": linked,
        "multi_party_donors": len(multi),
        "family_clusters": len(families),
        "limit_violations": len(violations),
        "declaration_mismatches": len(mismatches),
    }

    print(f"[KNAB] Summary: {json.dumps(summary, ensure_ascii=False)}")
    return summary
