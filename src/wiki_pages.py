"""
Per-entity wiki page builders — person and topic frontmatter + the person
synthesis block.

Carved out of ``src/wiki.py`` on 2026-09-05 (plāna 5.9) with no behaviour
change. ``src.wiki`` re-exports every name below; flat sibling module, NOT a
package.

The frontmatter KEYS emitted here are what ``src/wiki_lint.py`` checks 3 and 4
read, and ``tests/test_wiki_lint.py::test_lint_reads_keys_wiki_sync_actually_writes``
imports both builders from ``src.wiki`` to pin them — so a rename here breaks
that gate instead of silently switching the checks off.
"""

import sqlite3
from typing import Any

from src.lv_text import slugify as _slugify

def _build_person_frontmatter(
    db: sqlite3.Connection,
    politician: sqlite3.Row,
) -> dict:
    """Build frontmatter dict for a person page.

    `positions` = retoriskās pozīcijas (claim_type='position'). `votes` =
    parlamenta balsojumi (saeima_individual_votes). Iepriekšējais lauks
    `claims` apvienoja abus un radīja parpratumu (sk. wiki/CHANGELOG.md
    2026-04-25 strukturālā sanācija). Top_topics aprēķina TIKAI no position
    claims, lai tēmu saraksts atspoguļotu retorisko fokusu, ne procedurālas
    balss tēmu izlaidi.
    """
    pid = politician["id"]

    positions_count = db.execute(
        "SELECT COUNT(*) FROM claims WHERE opponent_id = ? AND claim_type='position'",
        (pid,),
    ).fetchone()[0]

    contradictions_count = db.execute(
        "SELECT COUNT(*) FROM contradictions WHERE opponent_id = ?", (pid,)
    ).fetchone()[0]

    votes_count = db.execute(
        "SELECT COUNT(*) FROM saeima_individual_votes WHERE politician_id = ?", (pid,)
    ).fetchone()[0]

    mentioned_in = db.execute(
        "SELECT COUNT(DISTINCT document_id) FROM document_politicians WHERE politician_id = ?",
        (pid,),
    ).fetchone()[0]

    # Last active: most recent position claim stated_at (votes notice their own
    # cycle — pārmērīgs balsojumu trends nepastāsta par "kad pēdējoreiz aktīvs").
    last_active_row = db.execute(
        "SELECT MAX(stated_at) FROM claims WHERE opponent_id = ? AND claim_type='position'",
        (pid,),
    ).fetchone()
    last_active = last_active_row[0] if last_active_row and last_active_row[0] else None

    # Top topics: position-claim topics only (rhetorical focus, not vote agenda).
    top_topics_rows = db.execute(
        """
        SELECT topic, COUNT(*) as cnt
        FROM claims
        WHERE opponent_id = ? AND claim_type='position'
        GROUP BY topic
        ORDER BY cnt DESC
        LIMIT 5
        """,
        (pid,),
    ).fetchall()
    top_topics = [r["topic"] for r in top_topics_rows if r["topic"]]

    fm: dict[str, Any] = {
        "name": politician["name"],
        "party": politician["party"] or "",
        "role": politician["role"] or "",
        "positions": positions_count,
        "votes": votes_count,
        "contradictions": contradictions_count,
        "mentioned_in": mentioned_in,
    }
    if last_active:
        fm["last_active"] = last_active
    if top_topics:
        fm["top_topics"] = top_topics

    return fm


def _gather_person_signal(db: sqlite3.Connection, pid: int) -> dict:
    """Collect four signal categories for the auto synthesis block.

    Returns a dict with keys:
      - top_topics: list[dict(topic, count, pct)] — empty if <3 topics with ≥2 claims
      - activity_30d: dict(count, ratio) or None — None if 0 claims in 30d
      - tensions: list[dict(target_pid, target_name, count, tension_type)] — top 3
      - contradictions: dict(total, rhetoric_action, position_shift, last_topic, last_date) or None

    Each field follows the "null when insufficient signal" convention so the
    render function can skip bullets cleanly without threshold logic.
    """
    # --- 1. Top topics: need ≥3 topics with ≥2 position claims each ---
    topic_rows = db.execute(
        """
        SELECT topic, COUNT(*) AS cnt
        FROM claims
        WHERE opponent_id = ? AND claim_type = 'position' AND topic IS NOT NULL
        GROUP BY topic
        HAVING cnt >= 2
        ORDER BY cnt DESC
        """,
        (pid,),
    ).fetchall()

    top_topics: list[dict] = []
    if len(topic_rows) >= 3:
        total_position_claims = db.execute(
            "SELECT COUNT(*) FROM claims WHERE opponent_id = ? AND claim_type = 'position'",
            (pid,),
        ).fetchone()[0]
        for row in topic_rows[:3]:
            pct = round(row["cnt"] * 100 / total_position_claims) if total_position_claims else 0
            top_topics.append({"topic": row["topic"], "count": row["cnt"], "pct": pct})

    # --- 2. Activity 30d + 90d baseline ratio ---
    count_30d = db.execute(
        """
        SELECT COUNT(*) FROM claims
        WHERE opponent_id = ? AND claim_type = 'position'
          AND stated_at >= date('now', '-30 days')
        """,
        (pid,),
    ).fetchone()[0]

    activity_30d: dict | None = None
    if count_30d >= 1:
        count_90d = db.execute(
            """
            SELECT COUNT(*) FROM claims
            WHERE opponent_id = ? AND claim_type = 'position'
              AND stated_at >= date('now', '-90 days')
            """,
            (pid,),
        ).fetchone()[0]
        # Baseline = claims in the 30–90d historical window (60-day span).
        # We require ≥6 historical claims (≈3/month) for the ratio to be
        # statistically meaningful; otherwise leave ratio=None so the render
        # function only reports raw count.
        historical_60d = count_90d - count_30d
        ratio: float | None = None
        if historical_60d >= 6:
            baseline_30 = historical_60d / 2.0
            ratio = round(count_30d / baseline_30, 1) if baseline_30 else None
        activity_30d = {"count": count_30d, "ratio": ratio}

    # --- 3. Tensions: top 3 targets by count ---
    tension_rows = db.execute(
        """
        SELECT pt.target_pid, tp.name AS target_name, pt.tension_type,
               COUNT(*) AS cnt
        FROM political_tensions pt
        JOIN tracked_politicians tp ON tp.id = pt.target_pid
        WHERE pt.source_pid = ? AND pt.target_pid IS NOT NULL
        GROUP BY pt.target_pid
        ORDER BY cnt DESC, pt.target_pid ASC
        LIMIT 3
        """,
        (pid,),
    ).fetchall()
    tensions = [
        {
            "target_pid": r["target_pid"],
            "target_name": r["target_name"],
            "count": r["cnt"],
            "tension_type": r["tension_type"],
        }
        for r in tension_rows
    ]

    # --- 4. Contradictions: confirmed only, split by rhetoric_action vs position_shift ---
    contra_total = db.execute(
        "SELECT COUNT(*) FROM contradictions WHERE opponent_id = ? AND confirmed = 1",
        (pid,),
    ).fetchone()[0]

    contradictions: dict | None = None
    if contra_total >= 1:
        rhetoric_action = db.execute(
            """
            SELECT COUNT(*)
            FROM contradictions c
            JOIN claims old_c ON old_c.id = c.claim_old_id
            JOIN claims new_c ON new_c.id = c.claim_new_id
            WHERE c.opponent_id = ? AND c.confirmed = 1
              AND old_c.claim_type != new_c.claim_type
            """,
            (pid,),
        ).fetchone()[0]

        position_shift = contra_total - rhetoric_action

        last_row = db.execute(
            """
            SELECT topic, detected_at
            FROM contradictions
            WHERE opponent_id = ? AND confirmed = 1
            ORDER BY detected_at DESC, id DESC
            LIMIT 1
            """,
            (pid,),
        ).fetchone()

        contradictions = {
            "total": contra_total,
            "rhetoric_action": rhetoric_action,
            "position_shift": position_shift,
            "last_topic": last_row["topic"] if last_row else None,
            "last_date": last_row["detected_at"] if last_row else None,
        }

    return {
        "top_topics": top_topics,
        "activity_30d": activity_30d,
        "tensions": tensions,
        "contradictions": contradictions,
    }


_SYNTHESIS_MAX_CHARS = 1500


class WikiSynthesisOverflow(Exception):
    """Raised when rendered synthesis block exceeds _SYNTHESIS_MAX_CHARS.

    Fail-loud design: silent truncation would hide a regression where a new
    bullet or an uncapped data source lets the block grow unboundedly. The
    operator must see and diagnose the overflow.
    """


def _render_person_synthesis(signal: dict) -> str:
    """Render the auto synthesis block from a signal dict.

    Returns either a bullet-list string (no leading/trailing newlines, no
    section headers) or an empty string when no bullet's threshold is met.

    Raises WikiSynthesisOverflow if the rendered block exceeds
    _SYNTHESIS_MAX_CHARS. This should never happen under normal data —
    if it does, diagnose before relaxing the limit.

    Wikilinks MUST carry the subdir + slug with the display name as alias
    (`[[topics/valsts-parvalde|Valsts pārvalde]]`), exactly like the index
    tables below. A bare `[[Valsts pārvalde]]` resolves to no file: pages
    live at topics/<slug>.md / persons/<slug>.md, and _slugify strips
    diacritics and spaces. Until 2026-08-02 all three bullets emitted the
    bare form, so wiki_sync itself wrote 338 broken links across 82 person
    pages — while wiki_lint reported "0 broken links", because its link
    check only walks the four index files (wiki_lint.py:100-122).
    """
    lines: list[str] = []

    # --- 1. Top tēmas ---
    if signal["top_topics"]:
        parts = [
            f"[[topics/{_slugify(t['topic'])}|{t['topic']}]] ({t['pct']}%)"
            for t in signal["top_topics"]
        ]
        lines.append(f"- **Top tēmas:** {', '.join(parts)}")

    # --- 2. 30d activity ---
    act = signal["activity_30d"]
    if act is not None:
        if act["ratio"] is not None:
            lines.append(f"- **30d:** {act['count']} claims, {act['ratio']}× bāzes līnija")
        else:
            lines.append(f"- **30d:** {act['count']} claims")

    # --- 3. Tensions ---
    if signal["tensions"]:
        parts = []
        for t in signal["tensions"]:
            label = _pluralize_lv(t["tension_type"], t["count"])
            parts.append(
                f"[[persons/{_slugify(t['target_name'])}|{t['target_name']}]] "
                f"({t['count']} {label})"
            )
        lines.append(f"- **Spriedzes:** {', '.join(parts)}")

    # --- 4. Contradictions ---
    contra = signal["contradictions"]
    if contra is not None:
        total = contra["total"]
        count_label = "apstiprinātas" if total != 1 else "apstiprināta"
        breakdown = ""
        if contra["rhetoric_action"] > 0 and contra["position_shift"] > 0:
            breakdown = (
                f" ({contra['rhetoric_action']} retorika↔balsojums, "
                f"{contra['position_shift']} pozīciju maiņa)"
            )
        last_bit = ""
        if contra["last_topic"] and contra["last_date"]:
            date_only = contra["last_date"][:10]
            last_bit = (
                f"; pēdējā par "
                f"[[topics/{_slugify(contra['last_topic'])}|{contra['last_topic']}]], "
                f"{date_only}"
            )
        lines.append(f"- **Pretrunas:** {total} {count_label}{breakdown}{last_bit}")

    if not lines:
        return ""

    block = "\n".join(lines) + "\n"

    if len(block) > _SYNTHESIS_MAX_CHARS:
        raise WikiSynthesisOverflow(
            f"Synthesis block {len(block)} chars exceeds max {_SYNTHESIS_MAX_CHARS}"
        )

    return block


def _pluralize_lv(tension_type: str, count: int) -> str:
    """Return the Latvian plural form for tension_type label.

    Tension types used by the codebase: 'uzbrukums', 'spriedze', 'atbalsts'.
    Singular keeps the base word; plural follows normal LV rules.
    """
    if count == 1:
        return tension_type
    plurals = {
        "uzbrukums": "uzbrukumi",
        "spriedze": "spriedzes",
        "atbalsts": "atbalsti",
    }
    return plurals.get(tension_type, tension_type)


def _build_topic_frontmatter(
    db: sqlite3.Connection,
    topic: str,
) -> dict:
    """Build frontmatter dict for a topic page.

    `positions` = retoriskās pozīcijas šajā tēmā (claim_type='position').
    `votes` = Saeimas balsojumi šajā tēmā (claim_type='saeima_vote').
    `politicians` un `top_politicians` skaita TIKAI position aktivitāti, lai
    tēmas leaderboard atspoguļo, kuri politiķi par tēmu RUNĀ, ne kuri tikai
    procedūriski par to balsojuši.
    """
    positions_count = db.execute(
        "SELECT COUNT(*) FROM claims WHERE topic = ? AND claim_type='position'",
        (topic,),
    ).fetchone()[0]

    votes_count = db.execute(
        "SELECT COUNT(*) FROM claims WHERE topic = ? AND claim_type='saeima_vote'",
        (topic,),
    ).fetchone()[0]

    politicians_count = db.execute(
        "SELECT COUNT(DISTINCT opponent_id) FROM claims WHERE topic = ? AND claim_type='position'",
        (topic,),
    ).fetchone()[0]

    contradictions_count = db.execute(
        "SELECT COUNT(*) FROM contradictions WHERE topic = ?", (topic,)
    ).fetchone()[0]

    last_activity_row = db.execute(
        "SELECT MAX(stated_at) FROM claims WHERE topic = ? AND claim_type='position'",
        (topic,),
    ).fetchone()
    last_activity = last_activity_row[0] if last_activity_row and last_activity_row[0] else None

    # Top politicians by POSITION claim count for this topic.
    top_politicians_rows = db.execute(
        """
        SELECT tp.name, COUNT(*) as cnt
        FROM claims c
        JOIN tracked_politicians tp ON c.opponent_id = tp.id
        WHERE c.topic = ? AND c.claim_type = 'position'
        GROUP BY c.opponent_id
        ORDER BY cnt DESC
        LIMIT 5
        """,
        (topic,),
    ).fetchall()
    top_politicians = [r["name"] for r in top_politicians_rows]

    fm: dict[str, Any] = {
        "topic": topic,
        "positions": positions_count,
        "votes": votes_count,
        "politicians": politicians_count,
        "contradictions": contradictions_count,
    }
    if last_activity:
        fm["last_activity"] = last_activity
    if top_politicians:
        fm["top_politicians"] = top_politicians

    return fm
