"""Daily routine enforcer for atmina.lv.

Queries DB state to report which steps of the daily routine are complete,
partial, or missing for a given date.
"""

import os
from datetime import datetime

from src.db import get_db, now_lv_dt, today_lv

_WIKI_INDEX_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "wiki", "index.md")
_OUTPUT_INDEX_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output", "atmina", "index.html")

# Steps that operator deliberately defers to afternoon. Before 15:00 LV the
# routine reporter must surface 'waiting' (operator UX) rather than 'missing'
# (false-alarm backlog). See `project_daily_routine_timing` memory for the
# rationale.
_AFTERNOON_ONLY_STEPS = ("analysis", "daily_brief")
_MORNING_WINDOW_HOUR = 15  # local LV hour; before this, deferred steps wait


def check_routine(
    target_date: str,
    db_path: str | None = None,
    now: datetime | None = None,
) -> dict:
    """Check completion status of all daily routine steps for target_date.

    Args:
        target_date: ISO date string (YYYY-MM-DD) to check.
        db_path: Optional DB path override (for testing).
        now: Optional LV-time datetime override. Defaults to ``now_lv_dt()``.
            Used to surface a 'waiting' status on analysis + daily_brief
            steps in the morning, when their absence is expected.

    Returns:
        Dict with 'date', 'all_complete', and 'steps' keys.
        Each step has 'status' ('done', 'partial', 'missing', 'stale',
        'waiting') and 'details'.
    """
    db = get_db(db_path) if db_path else get_db()

    steps = {}
    steps["ingest"] = _check_ingest(db, target_date)
    steps["analysis"] = _check_analysis(db, target_date)
    steps["contradictions"] = _check_contradictions(db, target_date)
    steps["devils_advocate"] = _check_devils_advocate(db, target_date)
    steps["tensions"] = _check_tensions(db, target_date)
    steps["tendences"] = _check_tendences(db, target_date)
    steps["daily_brief"] = _check_daily_brief(db, target_date)
    steps["featured_image"] = _check_featured_image(db, target_date)
    steps["wiki_sync"] = _check_wiki_sync(db, target_date)
    steps["generate"] = _check_generate(db, target_date)

    db.close()

    # Morning-window post-process. Only flip steps that are 'missing' for
    # today's date — never downgrade 'done'/'partial', never alter past-day
    # audits (operator might run check_routine on a backfill date long after).
    current = now if now is not None else now_lv_dt()
    is_today = target_date == current.date().isoformat()
    if is_today and current.hour < _MORNING_WINDOW_HOUR:
        for key in _AFTERNOON_ONLY_STEPS:
            if steps[key]["status"] == "missing":
                steps[key] = {
                    "status": "waiting",
                    "details": f"Gaida pēcpusdienu (≥{_MORNING_WINDOW_HOUR}:00 LV)",
                }

    all_complete = all(s["status"] == "done" for s in steps.values())

    return {
        "date": target_date,
        "all_complete": all_complete,
        "steps": steps,
    }


def _check_wiki_sync(db, target_date: str) -> dict:  # noqa: ARG001 - routine check signature contract; all _check_* functions take (db, target_date)
    """Check if wiki was synced today by reading index.md."""
    if not os.path.exists(_WIKI_INDEX_PATH):
        return {"status": "missing", "details": "wiki/index.md nav atrasts"}
    try:
        with open(_WIKI_INDEX_PATH, "r", encoding="utf-8") as f:
            content = f.read(500)
        import re
        match = re.search(r"Atjaunots: (\d{4}-\d{2}-\d{2})", content)
        if not match:
            return {"status": "missing", "details": "Nav sync datuma wiki/index.md"}
        sync_date = match.group(1)
        if sync_date == target_date:
            return {"status": "done", "details": f"Wiki synced {sync_date}"}
        return {"status": "stale", "details": f"Pēdējais sync: {sync_date}, šodien: {target_date}"}
    except (OSError, UnicodeDecodeError) as e:
        return {"status": "missing", "details": f"Nevar nolasīt wiki/index.md: {e}"}


def _check_generate(db, target_date: str) -> dict:
    """Check if static site was generated today (output/atmina/index.html exists and is fresh)."""
    if not os.path.exists(_OUTPUT_INDEX_PATH):
        return {"status": "missing", "details": "output/atmina/index.html nav atrasts"}

    mtime = datetime.fromtimestamp(os.path.getmtime(_OUTPUT_INDEX_PATH))
    mtime_date = mtime.strftime("%Y-%m-%d")

    if mtime_date == target_date:
        return {"status": "done", "details": f"Statiskā vietne ģenerēta {mtime.strftime('%H:%M')}"}

    latest_row = db.execute(
        """SELECT MAX(ts) as latest FROM (
               SELECT MAX(created_at) as ts FROM analyses
               UNION ALL
               SELECT MAX(created_at) as ts FROM context_notes
               UNION ALL
               SELECT MAX(created_at) as ts FROM claims
           )""",
    ).fetchone()

    if not latest_row or not latest_row["latest"]:
        return {"status": "done", "details": "Nav datu, salīdzinājumam"}

    latest_data = datetime.fromisoformat(latest_row["latest"])
    if mtime >= latest_data:
        return {"status": "done", "details": "Statiskā vietne ir aktuāla"}

    diff = latest_data - mtime
    hours = diff.total_seconds() / 3600
    return {
        "status": "stale",
        "details": f"Statiskā vietne novecojusi par {hours:.1f}h",
    }


def print_routine(target_date: str | None = None) -> dict:
    """Print a human-readable routine status report. Returns the check result."""
    # Windows default cp1252 stdout cannot encode the ✓/✗/◐/⚠/⏳ status icons
    # or Latvian diacritics in step labels. Reconfigure stdout to utf-8 for
    # this CLI entry only — module import must not mutate global stream state.
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

    if target_date is None:
        target_date = today_lv().isoformat()

    result = check_routine(target_date)

    status_icons = {
        "done": "\u2713",
        "partial": "\u25d0",
        "missing": "\u2717",
        "stale": "\u25d0",
        "waiting": "\u23f3",
    }
    step_labels = {
        "ingest": "1. Iel\u0101de (ingest)",
        "analysis": "2. Poz\u012bciju anal\u012bze",
        "contradictions": "3. Pretrunu p\u0101rbaude",
        "devils_advocate": "4. Devils-advocate p\u0101rskats",
        "tensions": "5. Spriedžu re\u0123istr\u0113\u0161ana",
        "tendences": "6. Konteksta piezīmes",
        "daily_brief": "7. Dienas p\u0101rskats",
        "featured_image": "8. Featured image \u0123ener\u0113\u0161ana",
        "wiki_sync": "9. Wiki sync",
        "generate": "10. Statisk\u0101s vietnes \u0123ener\u0113\u0161ana",
    }

    if result["all_complete"]:
        print(f"\u2713 RUTĪNA PABEIGTA — {target_date}")
    else:
        missing = [k for k, v in result["steps"].items() if v["status"] != "done"]
        print(f"\u26a0 RUTĪNA NEPILNĪGA \u2014 {len(missing)} soļi nav pabeigti ({target_date}):")

    for key, step in result["steps"].items():
        icon = status_icons.get(step["status"], "?")
        label = step_labels.get(key, key)
        print(f"  {icon} {label} \u2014 {step['details']}")

    from src.confidence_drift import check_confidence_drift
    drift_alerts = check_confidence_drift(days=7)
    if drift_alerts:
        print(f"\n\u26a0 CONFIDENCE DRIFT ({len(drift_alerts)} t\u0113mas):")
        for a in drift_alerts:
            print(f"  {a['topic']}: +{a['drift']:.2f} ({a['first_half_avg']:.2f} \u2192 {a['second_half_avg']:.2f})")

    diacritic_warning = _check_diacritic_health(target_date)
    if diacritic_warning:
        print(f"\n\u26a0 GARUMZĪMJU REGRESIJA ({target_date}): {diacritic_warning}")
        print("  Palaid: python scripts/scan_diacritics.py --list")

    try:
        from src.x_pool import COOKIES_DIR
        # Only numeric-name slot files (1.json, 2.json, ...) \u2014 skip
        # manifest.json and any other helper json placed in the dir.
        cookie_files = sorted(
            p for p in COOKIES_DIR.glob("*.json") if p.stem.isdigit()
        )
        legacy = COOKIES_DIR.parent / "x_cookies.json"
        if not cookie_files and legacy.exists():
            cookie_files = [legacy]
        print(f"\n\U0001f511 X/Twitter pool: {len(cookie_files)} cookie file(s)")
        for f in cookie_files:
            print(f"  \u2022 {f.name}")
    except Exception:
        pass

    # Coverage summary \u2014 informational, NOT a routine step (dark-zone deputies
    # are a standing P4 backlog, never a daily done/missing signal). Wrapped in
    # try/except like the X-pool block so a coverage error never breaks the
    # status print. Uses the same default DB as check_routine.
    try:
        from src.coverage import compute_coverage, format_coverage_summary
        print("\n" + format_coverage_summary(compute_coverage()))
    except Exception:
        pass

    return result


def _check_diacritic_health(target_date: str) -> str | None:
    """Return a one-line warning if today's writes show diacritic stripping.

    Informational only — not a routine step. The validator at write time
    already prevents NEW corruption, so this just surfaces lingering
    pre-guardrail records or any that slipped through validation.
    """
    from src.quality import validate_lv_diacritics
    db = get_db()
    try:
        rows = db.execute(
            """SELECT stance, quote FROM claims
               WHERE DATE(created_at) = ? AND claim_type != 'saeima_vote'""",
            (target_date,),
        ).fetchall()
    finally:
        db.close()
    if not rows:
        return None
    bad = sum(
        1 for r in rows
        if not validate_lv_diacritics(r["stance"])[0]
        or not validate_lv_diacritics(r["quote"])[0]
    )
    if not bad:
        return None
    return f"{bad}/{len(rows)} šodienas pozīcijām nav garumzīmju"


def _check_ingest(db, target_date: str) -> dict:
    row = db.execute(
        "SELECT COUNT(*) as cnt FROM documents WHERE DATE(scraped_at) = ?",
        (target_date,),
    ).fetchone()
    count = row["cnt"] if row else 0
    if count > 0:
        return {"status": "done", "details": f"{count} jauni dokumenti"}
    return {"status": "missing", "details": "Nav ielādētu dokumentu šodien"}


def _check_analysis(db, target_date: str) -> dict:
    # Denominator: politicians who had an *analyzable* subject document today.
    # platform='vestnesis' is excluded to mirror get_pending_politicians /
    # get_politician_documents — Saeimas stenogrammas list dozens of MPs as
    # 'subject' and signed legal acts list signatories, none of which carry a
    # first-party position to extract. Without this filter they perpetually
    # flagged politicians as "unanalyzed" every session day (2026-06-05 incident:
    # Briškens/Kalējs phantom-flagged off vestnesis subject docs).
    politicians_with_docs = db.execute(
        """SELECT DISTINCT dp.politician_id AS opponent_id, tp.name
           FROM documents d
           JOIN document_politicians dp ON dp.document_id = d.id AND dp.role = 'subject'
           JOIN tracked_politicians tp ON tp.id = dp.politician_id
           WHERE DATE(d.scraped_at) = ?
             AND d.platform != 'vestnesis'
             AND tp.relationship_type != 'inactive'""",
        (target_date,),
    ).fetchall()

    if not politicians_with_docs:
        return {"status": "done", "details": "Nav politiķu ar jauniem dokumentiem"}

    # A politician counts as analyzed if EITHER signal is present:
    #   (a) an analyses row dated today, OR
    #   (b) no remaining unreviewed analyzable subject doc (reviewed_at IS NULL).
    # Both are computed against the passed `db` — never get_pending_politicians,
    # which opens the default DB and would ignore the db_path the routine was
    # invoked with (test isolation / non-default-DB runs).
    #
    # The pre-2026-06-05 check used (a) alone, which produced phantom "trūkst"
    # flags: a doc reviewed via empty_doc_ids during a DB-lock retry whose
    # analyses row rolled back left the politician with reviewed docs but no
    # analyses row (Rajevskis). Signal (b) clears those. Combined with the
    # vestnesis exclusion in the denominator (Saeimas stenogrammas list dozens
    # of MPs as 'subject'), this keeps the status in step with the actual
    # claim-extractor backlog without going noisy on below-cap residuals
    # (e.g. bare-RT leftovers from the 12-doc cap stay "done" via signal (a)).
    pending_names = []
    analyzed_count = 0
    for p in politicians_with_docs:
        pid = p["opponent_id"]
        # analyses.created_at is UTC (DEFAULT CURRENT_TIMESTAMP), so 'localtime'
        # is CORRECT here — unlike documents.scraped_at / claims.created_at /
        # context_notes.created_at, which are LV (now_lv()) and must NOT carry it.
        has_analysis = db.execute(
            "SELECT 1 FROM analyses WHERE opponent_id = ? AND DATE(created_at, 'localtime') = ? LIMIT 1",
            (pid, target_date),
        ).fetchone()
        if has_analysis:
            analyzed_count += 1
            continue
        has_unreviewed = db.execute(
            """SELECT 1 FROM documents d
               JOIN document_politicians dp ON dp.document_id = d.id AND dp.role = 'subject'
               WHERE dp.politician_id = ?
                 AND DATE(d.scraped_at) = ?
                 AND d.platform != 'vestnesis'
                 AND d.reviewed_at IS NULL
               LIMIT 1""",
            (pid, target_date),
        ).fetchone()
        if has_unreviewed:
            pending_names.append(p["name"])
        else:
            analyzed_count += 1

    total = len(politicians_with_docs)

    if not pending_names:
        return {"status": "done", "details": f"{total}/{total} politiķi analizēti"}
    if analyzed_count == 0:
        return {"status": "missing", "details": f"0/{total} analizēti, trūkst: {', '.join(pending_names)}"}
    return {"status": "partial", "details": f"{analyzed_count}/{total} analizēti, trūkst: {', '.join(pending_names)}"}


def _check_contradictions(db, target_date: str) -> dict:
    claims_row = db.execute(
        "SELECT COUNT(*) as cnt FROM claims WHERE DATE(created_at) = ?",
        (target_date,),
    ).fetchone()
    claims_today = claims_row["cnt"] if claims_row else 0

    if claims_today == 0:
        return {"status": "done", "details": "Nav jaunu pozīciju pārbaudei"}

    contra_row = db.execute(
        "SELECT COUNT(*) as cnt FROM contradictions WHERE DATE(detected_at) = ?",
        (target_date,),
    ).fetchone()
    contra_today = contra_row["cnt"] if contra_row else 0

    return {
        "status": "done",
        "details": f"{claims_today} pozīcijas pārbaudītas, {contra_today} pretrunas atrastas",
    }


def _check_devils_advocate(db, target_date: str) -> dict:
    """Check that all new contradictions today have been reviewed by @devils-advocate."""
    contra_row = db.execute(
        "SELECT COUNT(*) as cnt FROM contradictions WHERE DATE(detected_at) = ?",
        (target_date,),
    ).fetchone()
    total_today = contra_row["cnt"] if contra_row else 0

    if total_today == 0:
        return {"status": "done", "details": "Nav jaunu pretrunu pārskatīšanai"}

    unreviewed_row = db.execute(
        "SELECT COUNT(*) as cnt FROM contradictions WHERE DATE(detected_at) = ? AND reviewed = 0",
        (target_date,),
    ).fetchone()
    unreviewed = unreviewed_row["cnt"] if unreviewed_row else 0

    if unreviewed == 0:
        reviewed = total_today
        return {"status": "done", "details": f"{reviewed}/{total_today} pretrunas pārskatītas"}

    reviewed = total_today - unreviewed
    if reviewed == 0:
        return {
            "status": "missing",
            "details": f"0/{total_today} pretrunas pārskatītas — palaid @devils-advocate",
        }
    return {
        "status": "partial",
        "details": f"{reviewed}/{total_today} pārskatītas, {unreviewed} vēl gaida @devils-advocate",
    }


def _check_tensions(db, target_date: str) -> dict:
    """Check if political tensions were recorded today."""
    # political_tensions.created_at is UTC (DEFAULT CURRENT_TIMESTAMP) — keep
    # 'localtime'. The claims count below uses now_lv() (LV) — no 'localtime'.
    row = db.execute(
        "SELECT COUNT(*) as cnt FROM political_tensions WHERE DATE(created_at, 'localtime') = ?",
        (target_date,),
    ).fetchone()
    count = row["cnt"] if row else 0

    claims_by_pol = db.execute(
        """SELECT COUNT(DISTINCT opponent_id) as pols FROM claims
           WHERE DATE(created_at) = ?""",
        (target_date,),
    ).fetchone()
    pol_count = claims_by_pol["pols"] if claims_by_pol else 0

    if pol_count < 2:
        return {"status": "done", "details": "Mazāk par 2 politiķiem ar jaunām pozīcijām"}
    if count > 0:
        return {"status": "done", "details": f"{count} spriedzes reģistrētas"}
    return {"status": "missing", "details": f"Nav spriedžu, bet {pol_count} politiķiem ir jaunas pozīcijas"}


def _check_tendences(db, target_date: str) -> dict:
    row = db.execute(
        "SELECT COUNT(*) as cnt FROM context_notes WHERE note_type = 'context' AND DATE(created_at) = ?",
        (target_date,),
    ).fetchone()
    count = row["cnt"] if row else 0
    if count > 0:
        return {"status": "done", "details": f"{count} konteksta piezīmes pievienotas"}
    return {"status": "missing", "details": "Nav konteksta piezīmju šodien"}


def _check_daily_brief(db, target_date: str) -> dict:
    row = db.execute(
        "SELECT COUNT(*) as cnt FROM context_notes WHERE note_type = 'daily_brief' AND DATE(created_at) = ?",
        (target_date,),
    ).fetchone()
    count = row["cnt"] if row else 0
    if count > 0:
        return {"status": "done", "details": "Dienas pārskats sarakstīts"}
    return {"status": "missing", "details": f"Nav dienas pārskata par {target_date}"}


def _check_featured_image(db, target_date: str) -> dict:
    """Check whether today's daily_brief has an approved featured image.

    Decouples from _check_daily_brief: if no brief exists we return 'done'
    (not this step's concern — step 7 flags it). If the brief lacks a
    visual_brief_json block we surface that as 'partial' so brief-writer
    can be retried. If the block exists but no approved=1 image row is
    present, the step is 'missing' and @graphics-designer must run.
    """
    brief = db.execute(
        """SELECT id, visual_brief_json FROM context_notes
           WHERE note_type = 'daily_brief' AND DATE(created_at) = ?
           ORDER BY id DESC LIMIT 1""",
        (target_date,),
    ).fetchone()
    if brief is None:
        return {"status": "done", "details": "Nav dienas pārskata pārbaudei"}

    brief_id = brief["id"]
    if not brief["visual_brief_json"]:
        return {
            "status": "partial",
            "details": f"Brief {brief_id} bez vizuālā brief bloka (brief-writer izlaidis)",
        }

    approved = db.execute(
        "SELECT id FROM brief_images WHERE note_id = ? AND approved = 1 LIMIT 1",
        (brief_id,),
    ).fetchone()
    if approved is not None:
        return {"status": "done", "details": f"Featured image apstiprināts (brief {brief_id})"}

    return {
        "status": "missing",
        "details": f"Brief {brief_id} gaida featured image — izsauc @graphics-designer",
    }
