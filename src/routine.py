"""Daily routine enforcer for atmina.lv.

Queries DB state to report which steps of the daily routine are complete,
partial, or missing for a given date.
"""

import json
import os
from datetime import datetime

from src.db import get_db, now_lv_dt, today_lv
from src.scope import queue_politician_sql

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
        Each step has 'status' ('done', 'n/a', 'partial', 'missing', 'stale',
        'waiting') and 'details'. 'n/a' means the step had nothing to do —
        complete, but deliberately not the same claim as 'done'.
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

    # `n/a` = "there was nothing for this step to do". It counts as complete —
    # a day with no new contradictions is not an unfinished day — but it must
    # NOT render as ✓, because the two are different facts and the difference
    # is exactly what hides a bad day. When ingest fails, steps 2-5 each find
    # nothing and each used to report ✓, so a dead day produced a wall of green
    # and "10/10" (cf. 2026-07-29 outage, and 08-02 where the morning chain
    # never ran). See CLAUDE.md § "A gate that cannot fail is not evidence".
    all_complete = all(s["status"] in ("done", "n/a") for s in steps.values())

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
        return {"status": "n/a", "details": "Nav datu, salīdzinājumam"}

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
        "n/a": "\u25cb",
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

    # Count 'n/a' separately in the header. "10/10 zaļi" has been reported
    # on days where several of those steps simply had nothing to do, which
    # reads as a fuller day than it was — and on a day the ingest silently
    # fails, EVERY downstream step has nothing to do.
    na = [k for k, v in result["steps"].items() if v["status"] == "n/a"]
    na_tail = f", {len(na)} soļiem nebija ko darīt" if na else ""
    if result["all_complete"]:
        print(f"✓ RUTĪNA PABEIGTA — {target_date}{na_tail}")
    else:
        missing = [
            k for k, v in result["steps"].items() if v["status"] not in ("done", "n/a")
        ]
        print(
            f"⚠ RUTĪNA NEPILNĪGA — {len(missing)} soļi nav pabeigti "
            f"({target_date}{na_tail}):"
        )

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
        # (Here stood "Palaid: python scripts/scan_diacritics.py --list". That
        # script was deleted 2026-04-19 (94552450), and the line also handed out
        # bare `python`, which CLAUDE.md forbids — it resolves to a foreign venv
        # and the failure mode is a PARTIAL WRITE. It printed at exactly the T4
        # STOP moment, i.e. the worst time to be given a dead command.)

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


# The morning steps that write a log action of their own, in run order.
# Vestnesis and the junction backstop write none, so they are observable only
# through the `morning_ingest` summary row.
_INGEST_LOG_ACTIONS = {
    "ingest": "RSS",
    "social_fetch_all": "X profili",
    "mentions_fetch": "X pieminējumi",
}


def _check_ingest(db, target_date: str) -> dict:
    """Vai ielāde ŠODIEN NOTIKA — nevis vai šodien kaut kas ir ierakstīts.

    Sākotnējā pārbaude skaitīja `documents` rindas ar šodienas `scraped_at`, un
    tas ir cits jautājums. 2026-08-02 viens ad-hoc `ingest_url.py` dokuments
    padarīja šo soli zaļu, kamēr rīta ķēde nebija palaista vispār: parasta diena
    dod 600–900 dokumentu, tā diena bija devusi 10. Tā pati forma slēpa 07-29
    outage. Autoritāte tagad ir žurnāls; dokumentu skaits ir tikai dekorācija
    virsū, jo tas neatbild uz uzdoto jautājumu.

    `logs.timestamp` raksta `now_lv()`, tātad tā ir LV laika kolonna un datuma
    filtrs šeit iet BEZ laikjoslas modifikatora — sk. CLAUDE.md § Timestamp
    columns un `tests/test_timestamp_timezone_gate.py`.
    """
    row = db.execute(
        "SELECT COUNT(*) as cnt FROM documents WHERE DATE(scraped_at) = ?",
        (target_date,),
    ).fetchone()
    count = row["cnt"] if row else 0
    docs = f"{count} jauni dokumenti"

    summary = db.execute(
        "SELECT status, details FROM logs "
        "WHERE action = 'morning_ingest' AND DATE(timestamp) = ? "
        "ORDER BY id DESC LIMIT 1",
        (target_date,),
    ).fetchone()
    if summary is not None:
        if summary["status"] == "success":
            return {"status": "done", "details": f"rīta ķēde 5/5, {docs}"}
        detail = ""
        try:
            failed = (json.loads(summary["details"] or "{}") or {}).get("failed") or []
            if failed:
                detail = " — krita: " + ", ".join(failed)
        except (ValueError, TypeError):
            pass
        return {
            "status": "partial",
            "details": f"rīta ķēde NEPILNĪGA{detail}; {docs}",
        }

    ran = {
        r["action"]
        for r in db.execute(
            "SELECT DISTINCT action FROM logs WHERE DATE(timestamp) = ? "
            f"AND action IN ({','.join('?' * len(_INGEST_LOG_ACTIONS))})",
            (target_date, *_INGEST_LOG_ACTIONS),
        )
    }
    if not ran:
        return {
            "status": "missing",
            "details": f"ielāde šodien nav palaista ({docs})",
        }
    missing = [lbl for act, lbl in _INGEST_LOG_ACTIONS.items() if act not in ran]
    if missing:
        # The traceless case: stopping partway through the three manual calls
        # leaves no failure row anywhere, so the day looked like "no mentions
        # today" rather than "step 3 never ran" (2026-07-22, 07-28, 07-31).
        return {
            "status": "partial",
            "details": f"nav palaists: {', '.join(missing)}; {docs}",
        }
    return {"status": "done", "details": f"{docs} (manuālais ceļš, bez kopsavilkuma)"}


def _check_analysis(db, target_date: str) -> dict:
    # Denominator: politicians who had an *analyzable* subject document today.
    # platform='vestnesis' is excluded to mirror get_pending_politicians /
    # get_politician_documents — Saeimas stenogrammas list dozens of MPs as
    # 'subject' and signed legal acts list signatories, none of which carry a
    # first-party position to extract. Without this filter they perpetually
    # flagged politicians as "unanalyzed" every session day (2026-06-05 incident:
    # Briškens/Kalējs phantom-flagged off vestnesis subject docs).
    # The politician-side scope is `src/scope.py`, NOT a local literal. This
    # denominator and `get_pending_politicians()` must answer the same question
    # — on 2026-08-02 they did not: the relay exclusion landed in the queue and
    # not here, and since a relay entity has a subject document on 26 of any 30
    # days, step 2 could essentially never report green again. A status that
    # can never be green is as useless as a gate that can never fail.
    politicians_with_docs = db.execute(
        f"""SELECT DISTINCT dp.politician_id AS opponent_id, tp.name
           FROM documents d
           JOIN document_politicians dp ON dp.document_id = d.id AND dp.role = 'subject'
           JOIN tracked_politicians tp ON tp.id = dp.politician_id
           WHERE DATE(d.scraped_at) = ?
             AND d.platform != 'vestnesis'
             AND {queue_politician_sql()}""",
        (target_date,),
    ).fetchall()

    if not politicians_with_docs:
        return {"status": "n/a", "details": "Nav politiķu ar jauniem dokumentiem"}

    # A politician counts as analyzed if EITHER signal is present:
    #   (a) a today-dated analyses row that COVERS every unreviewed analyzable
    #       subject doc — i.e. no such doc was scraped AFTER the politician's
    #       latest today-dated analyses row, OR
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
    #
    # (a) is NOT absolute (2026-07-16 fix): an analyses row only vouches for docs
    # the extraction session actually saw — those scraped BEFORE it. A morning
    # backfill writes today-dated analyses rows; docs that arrive LATER the same
    # day are not covered and must reopen the politician as pending. Otherwise a
    # 12-pending status masked 20 real (Kulbergs/Rinkēvičs/Rajevskis unreviewed
    # docs hidden behind their morning rows). "Later" = documents.scraped_at
    # after MAX(analyses.created_at); below-cap residuals stay done because their
    # docs predate the row.
    pending_names = []
    analyzed_count = 0
    for p in politicians_with_docs:
        pid = p["opponent_id"]
        # analyses.created_at is UTC (DEFAULT CURRENT_TIMESTAMP), so 'localtime'
        # is CORRECT here — unlike documents.scraped_at / claims.created_at /
        # context_notes.created_at, which are LV (now_lv()) and must NOT carry it.
        analysis_row = db.execute(
            "SELECT MAX(created_at) AS max_ca FROM analyses "
            "WHERE opponent_id = ? AND DATE(created_at, 'localtime') = ?",
            (pid, target_date),
        ).fetchone()
        max_ca = analysis_row["max_ca"] if analysis_row else None
        if max_ca:
            # Mixed-tz compare (this repo's trap family): documents.scraped_at is
            # LV (now_lv()), analyses.created_at is UTC. Shift the analyses bound
            # +3h (fixed UTC+3) into LV before comparing; without it the compare
            # lies in the 00:00–03:00 LV window when overnight/morning backfills
            # run. A doc scraped after the shifted bound arrived AFTER the
            # analysis and reopens the politician.
            has_late_doc = db.execute(
                """SELECT 1 FROM documents d
                   JOIN document_politicians dp ON dp.document_id = d.id AND dp.role = 'subject'
                   WHERE dp.politician_id = ?
                     AND DATE(d.scraped_at) = ?
                     AND d.platform != 'vestnesis'
                     AND d.reviewed_at IS NULL
                     AND d.scraped_at > datetime(?, '+3 hours')
                   LIMIT 1""",
                (pid, target_date, max_ca),
            ).fetchone()
            if has_late_doc:
                pending_names.append(p["name"])
            else:
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
    # claim_type='position': solis prasa pretrunu pārbaudi par jaunām POZĪCIJĀM,
    # un tā arī saka lietotājam. Bez filtra Saeimas ielādes diena to iesloga —
    # 2026-07-23 šis skaitīja 5361 claim, kur pozīcijas bija 72 (07-25: 1664/33).
    claims_row = db.execute(
        "SELECT COUNT(*) as cnt FROM claims "
        "WHERE DATE(created_at) = ? AND claim_type = 'position'",
        (target_date,),
    ).fetchone()
    claims_today = claims_row["cnt"] if claims_row else 0

    if claims_today == 0:
        return {"status": "n/a", "details": "Nav jaunu pozīciju pārbaudei"}

    contra_row = db.execute(
        "SELECT COUNT(*) as cnt FROM contradictions WHERE DATE(detected_at) = ?",
        (target_date,),
    ).fetchone()
    contra_today = contra_row["cnt"] if contra_row else 0

    # Medību izpildes pēda: `store_contradiction()` raksta tikai ATRADUMUS, tāpēc
    # 0 rindas nav atšķiramas no „medības netika palaistas" (2026-08-19 audits,
    # kandidāts #4). Trase ir `logs` rinda ar action='contradiction_hunt', ko
    # raksta rutīnas 3. solis pēc medību pabeigšanas — arī pie 0 atradumiem
    # (godīgā nulle ir iznākums, ne klusēšana; sk. dienas-rutina Step 3).
    if contra_today > 0:
        return {
            "status": "done",
            "details": f"{claims_today} pozīcijas pārbaudītas, {contra_today} pretrunas atrastas",
        }
    hunt_row = db.execute(
        "SELECT COUNT(*) as cnt FROM logs "
        "WHERE action = 'contradiction_hunt' AND DATE(timestamp) = ?",
        (target_date,),
    ).fetchone()
    if hunt_row and hunt_row["cnt"]:
        return {
            "status": "done",
            "details": (
                f"{claims_today} pozīcijas pārbaudītas, 0 pretrunas atrastas "
                "(medību izpilde pierādīta ar logs ierakstu)"
            ),
        }
    return {
        "status": "missing",
        "details": (
            f"{claims_today} pozīcijas šodien, bet pretrunu medību izpilde nav "
            "pierādāma — nav ne pretrunu ierakstu, ne logs rindas 'contradiction_hunt'"
        ),
    }


def _check_devils_advocate(db, target_date: str) -> dict:
    """Check that all new contradictions today have been reviewed by @devils-advocate."""
    contra_row = db.execute(
        "SELECT COUNT(*) as cnt FROM contradictions WHERE DATE(detected_at) = ?",
        (target_date,),
    ).fetchone()
    total_today = contra_row["cnt"] if contra_row else 0

    if total_today == 0:
        return {"status": "n/a", "details": "Nav jaunu pretrunu pārskatīšanai"}

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

    # claim_type='position' — sk. _check_contradictions. Ziņojums saka „politiķiem
    # ir jaunas pozīcijas", tāpēc balsojumu claims te nedrīkst skaitīt: 2026-07-23
    # bez filtra sanāca 115 politiķi, ar filtru 39 (07-25: 121 pret 23).
    claims_by_pol = db.execute(
        """SELECT COUNT(DISTINCT opponent_id) as pols FROM claims
           WHERE DATE(created_at) = ? AND claim_type = 'position'""",
        (target_date,),
    ).fetchone()
    pol_count = claims_by_pol["pols"] if claims_by_pol else 0

    if pol_count < 2:
        return {"status": "n/a", "details": "Mazāk par 2 politiķiem ar jaunām pozīcijām"}
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


def _daily_briefs_for(db, target_date: str) -> list:
    """``daily_brief`` rows whose SUBJECT day is *target_date*.

    Not "rows created on that date" — see ``src.briefs.brief_subject_date`` for
    why that distinction is load-bearing. The WHERE clause only narrows the
    candidate set (exact topic, same-day creation, or the date appearing
    anywhere in the text); ``brief_subject_date`` makes the actual decision, so
    a row whose topic names a different day can never count for this one.
    """
    from src.briefs import brief_subject_date, daily_brief_topic

    rows = db.execute(
        """SELECT id, topic, content, created_at, visual_brief_json
           FROM context_notes
           WHERE note_type = 'daily_brief'
             AND (topic = ? OR DATE(created_at) = ? OR content LIKE ?)
           ORDER BY id""",
        (daily_brief_topic(target_date), target_date, f"%{target_date}%"),
    ).fetchall()
    return [
        r for r in rows
        if brief_subject_date(r["topic"], r["content"], r["created_at"]) == target_date
    ]


def _check_daily_brief(db, target_date: str) -> dict:
    if _daily_briefs_for(db, target_date):
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
    briefs = _daily_briefs_for(db, target_date)
    if not briefs:
        return {"status": "n/a", "details": "Nav dienas pārskata pārbaudei"}
    # Newest row for THIS subject day. Selecting by created_at instead used to
    # pick a neighbouring day's brief and check its image — on 2026-07-29 this
    # step reported "apstiprināts (brief 383)" while 383 covers 07-28.
    brief = briefs[-1]

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
