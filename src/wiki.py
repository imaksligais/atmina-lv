"""
Wiki sync engine for atmina.
Syncs DB data into an Obsidian-compatible wiki vault.

Key design:
  - YAML frontmatter is auto-synced from DB.
  - Body content below frontmatter is MANUAL and never overwritten.
  - Pages grouped by party, not relationship_type.
"""

import re
import sqlite3
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

import yaml

from src.db import get_db
from src.wiki_lint import lint_wiki_with_db

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = "data/atmina.db"
DEFAULT_WIKI_DIR = "wiki"

# Latvian transliteration map
_LV_TRANS = str.maketrans(
    "āčēģīķļņōŗšūžĀČĒĢĪĶĻŅŌŖŠŪŽ",
    "acegiklnorsuzACEGIKLNORSUZ",
)


def _slugify(name: str) -> str:
    """Transliterate Latvian characters and convert to slug."""
    transliterated = name.translate(_LV_TRANS)
    slug = transliterated.lower()
    slug = slug.replace(" ", "-")
    # Remove any remaining non-alphanumeric chars except hyphens
    slug = "".join(c for c in slug if c.isalnum() or c == "-")
    return slug


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from markdown text.

    Returns (frontmatter_dict, body_string).
    If no frontmatter, returns ({}, text).
    """
    if not text.startswith("---"):
        return {}, text

    # Find the closing ---
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text

    yaml_block = text[3:end].strip()
    body = text[end + 4:].lstrip("\n")

    try:
        fm = yaml.safe_load(yaml_block) or {}
    except yaml.YAMLError:
        fm = {}

    return fm, body


def _render_frontmatter(data: dict) -> str:
    """Render a dict as a YAML frontmatter block."""
    return "---\n" + yaml.dump(
        data,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
    ) + "---\n"


def _update_page(path: Path, new_frontmatter: dict, default_body: str = "") -> None:
    """Create or update a wiki page.

    If the page exists: update frontmatter only, preserve body.
    If new: create stub with frontmatter + default_body.
    """
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        _old_fm, body = _parse_frontmatter(existing)
    else:
        body = default_body

    content = _render_frontmatter(new_frontmatter)
    if body:
        content += "\n" + body

    path.write_text(content, encoding="utf-8")


_SYNC_START = "<!-- SYNC-AUTO -->"
_SYNC_END = "<!-- /SYNC-AUTO -->"

_BILLS_SYNC_START = "<!-- BILLS-SYNC-AUTO -->"
_BILLS_SYNC_END = "<!-- /BILLS-SYNC-AUTO -->"


def _render_law_bills_block(slug: str, db: sqlite3.Connection, md_path: Path) -> bool:
    """Atjauno BILLS-SYNC-AUTO bloku wiki/laws/<slug>.md failā.

    Returns True ja saturs faktiski mainījies (False = idempotents, fails nav skarts).
    """
    rows = db.execute("""
        SELECT document_nr, title, current_stage, current_status, last_updated_at
        FROM saeima_bills
        WHERE base_law_slug = ?
        ORDER BY last_updated_at DESC, id DESC
    """, (slug,)).fetchall()

    if rows:
        lines = [
            _BILLS_SYNC_START,
            "## Aktuālie likumprojekti šajā likumā",
            "",
            "| Bill nr | Nosaukums | Stadija | Datums |",
            "|---|---|---|---|",
        ]
        for r in rows:
            doc_slug = r["document_nr"].lower().replace("/", "-")
            stage_with_status = r["current_stage"] or ""
            if r["current_status"]:
                stage_with_status += f" ({r['current_status']})"
            date = (r["last_updated_at"] or "")[:10]
            lines.append(
                f"| [{r['document_nr']}](/likumprojekti/{doc_slug}.html) | {r['title']} | {stage_with_status} | {date} |"
            )
        lines.append(_BILLS_SYNC_END)
    else:
        lines = [
            _BILLS_SYNC_START,
            "## Aktuālie likumprojekti šajā likumā",
            "",
            "_Šajā likumā šobrīd nav aktīvu likumprojektu Saeimā._",
            _BILLS_SYNC_END,
        ]
    new_block = "\n".join(lines)

    if not md_path.exists():
        return False

    content = md_path.read_text(encoding="utf-8")

    if _BILLS_SYNC_START in content and _BILLS_SYNC_END in content:
        # Replace existing block
        before, _, rest = content.partition(_BILLS_SYNC_START)
        _, _, after = rest.partition(_BILLS_SYNC_END)
        new_content = before + new_block + after
    else:
        # Append at end with newline separation
        new_content = content.rstrip() + "\n\n" + new_block + "\n"

    if new_content == content:
        return False

    md_path.write_text(new_content, encoding="utf-8")
    return True


def _update_page_with_sync_block(
    path: Path,
    new_frontmatter: dict,
    sync_block: str,
) -> None:
    """Create or update a wiki page with a sync-marked auto block.

    Behavior:
      - Frontmatter is always replaced by `new_frontmatter`.
      - Any existing content between SYNC markers is replaced by `sync_block`
        (or removed entirely if `sync_block` is empty).
      - Manual body content outside the markers is preserved verbatim.
      - If page is new and `sync_block` is non-empty: creates frontmatter +
        markers + sync_block. If empty: creates frontmatter only.
      - If page exists without markers and `sync_block` is non-empty: appends
        markers + sync_block to end of body (manual content above).
    """
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        _old_fm, body = _parse_frontmatter(existing)
    else:
        body = ""

    # Strip any existing sync block from the body.
    body = _strip_sync_block(body)

    # Rebuild body: manual content + (optional) new sync block.
    if sync_block.strip():
        block_text = f"{_SYNC_START}\n{sync_block.rstrip()}\n{_SYNC_END}\n"
        if body.strip():
            body = body.rstrip() + "\n\n" + block_text
        else:
            body = block_text

    content = _render_frontmatter(new_frontmatter)
    if body:
        content += "\n" + body

    path.write_text(content, encoding="utf-8")


def _strip_sync_block(body: str) -> str:
    """Remove the SYNC-AUTO markers and their content from `body`.

    If no markers present, returns `body` unchanged. If multiple marker pairs
    exist (should not happen in practice), removes only the first pair and
    leaves subsequent markers intact — a follow-up sync call will re-normalize.
    """
    start_idx = body.find(_SYNC_START)
    if start_idx == -1:
        return body
    end_marker_idx = body.find(_SYNC_END, start_idx)
    if end_marker_idx == -1:
        # Malformed: start without end. Leave body untouched so operator can fix manually.
        return body
    end_idx = end_marker_idx + len(_SYNC_END)
    # Also consume one trailing newline if present.
    if end_idx < len(body) and body[end_idx] == "\n":
        end_idx += 1
    before = body[:start_idx].rstrip()
    after = body[end_idx:].lstrip()
    if before and after:
        return before + "\n\n" + after
    return before or after


def _now_lv() -> str:
    """Current datetime in Latvia time (EEST, UTC+3)."""
    lv_offset = timedelta(hours=3)
    return (datetime.now(timezone.utc) + lv_offset).strftime("%Y-%m-%d %H:%M:%S")


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
    """
    lines: list[str] = []

    # --- 1. Top tēmas ---
    if signal["top_topics"]:
        parts = [f"[[{t['topic']}]] ({t['pct']}%)" for t in signal["top_topics"]]
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
            parts.append(f"[[{t['target_name']}]] ({t['count']} {label})")
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
            last_bit = f"; pēdējā par [[{contra['last_topic']}]], {date_only}"
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


# ---------------------------------------------------------------------------
# Sub-index builders (auto-generated, fully overwritten each sync)
# ---------------------------------------------------------------------------

def _build_persons_index(db: sqlite3.Connection) -> str:
    """Build persons/personas.md — politicians grouped by party in tables.

    "Pozīcijas" kolonna skaita TIKAI claim_type='position'. "Balsojumi" ir
    raw saeima_individual_votes count. Iepriekšējais total-claims rādītājs
    "Pozīcijas" ailē ietvēra arī saeima_vote claims un radīja ~10× pārliecīgu
    skaitli (sk. wiki/CHANGELOG.md 2026-04-25 strukturālā sanācija).
    """
    now = _now_lv()

    # Each table is pre-aggregated by politician id in its own subquery, then
    # joined 1:1 onto tracked_politicians. The earlier single-statement form
    # LEFT JOINed claims + contradictions + saeima_individual_votes together
    # before counting, which multiplied each politician's claims × votes rows
    # (a cartesian blow-up) and made the query effectively never finish at
    # ~511k claims / ~506k votes. Counting per table independently keeps the
    # exact same numbers (COUNT(DISTINCT id) over a single table == COUNT(*)
    # of its grouped rows) without the explosion.
    rows = db.execute("""
        SELECT tp.id, tp.name, tp.party,
               COALESCE(cl.positions, 0) AS positions,
               COALESCE(ct.contradictions, 0) AS contradictions,
               COALESCE(v.votes, 0) AS votes,
               cl.last_active AS last_active
        FROM tracked_politicians tp
        LEFT JOIN (
            SELECT opponent_id,
                   COUNT(CASE WHEN claim_type='position' THEN 1 END) AS positions,
                   MAX(CASE WHEN claim_type='position' THEN stated_at END) AS last_active
            FROM claims GROUP BY opponent_id
        ) cl ON cl.opponent_id = tp.id
        LEFT JOIN (
            SELECT opponent_id, COUNT(*) AS contradictions
            FROM contradictions GROUP BY opponent_id
        ) ct ON ct.opponent_id = tp.id
        LEFT JOIN (
            SELECT politician_id, COUNT(*) AS votes
            FROM saeima_individual_votes GROUP BY politician_id
        ) v ON v.politician_id = tp.id
        WHERE tp.relationship_type != 'inactive'
        ORDER BY positions DESC
    """).fetchall()

    total = len(rows)
    total_positions = sum(r["positions"] for r in rows)

    # Group by party
    parties: dict[str, list] = {}
    party_positions: dict[str, int] = {}
    for r in rows:
        p = r["party"] or "Nezināms"
        parties.setdefault(p, []).append(r)
        party_positions[p] = party_positions.get(p, 0) + r["positions"]

    # Sort parties by total positions desc
    sorted_parties = sorted(parties.keys(), key=lambda p: party_positions[p], reverse=True)

    lines = [
        "# Politiķi — Indekss",
        "",
        f"_Atjaunots: {now}_",
        "",
        f"**{total}** politiķi, **{total_positions}** pozīcijas",
        "",
    ]

    for party in sorted_parties:
        members = parties[party]
        lines.append(f"## {party} ({len(members)})")
        lines.append("")
        lines.append("| Politiķis | Pozīcijas | Pretrunas | Balsojumi | Pēdējā aktivitāte |")
        lines.append("|---|---|---|---|---|")
        for r in members:
            slug = _slugify(r["name"])
            last = (r["last_active"] or "")[:10]
            lines.append(
                f"| [[persons/{slug}\\|{r['name']}]] | {r['positions']} | {r['contradictions']} | {r['votes']} | {last} |"
            )
        lines.append("")

    return "\n".join(lines) + "\n"


def _build_topics_index(db: sqlite3.Connection) -> str:
    """Build topics/temas.md — all topics in a single table.

    Pozīcijas un Balsojumi ir DIVAS atsevišķas kolonnas, lai nesajauktu
    retorisko aktivitāti ar parlamenta balss procedūru. Politiķu un
    aktivitātes laukus aprēķina no position claims (kuri par tēmu runā,
    ne kuri par to procedūriski balsoja).
    """
    now = _now_lv()

    rows = db.execute("""
        SELECT c.topic,
               SUM(CASE WHEN c.claim_type='position' THEN 1 ELSE 0 END) AS positions,
               SUM(CASE WHEN c.claim_type='saeima_vote' THEN 1 ELSE 0 END) AS votes,
               COUNT(DISTINCT CASE WHEN c.claim_type='position' THEN c.opponent_id END) AS politicians,
               COUNT(DISTINCT ct.id) AS contradictions,
               MAX(CASE WHEN c.claim_type='position' THEN c.stated_at END) AS last_activity
        FROM claims c
        LEFT JOIN contradictions ct ON ct.topic = c.topic
        WHERE c.topic IS NOT NULL
        GROUP BY c.topic
        ORDER BY positions DESC, votes DESC
    """).fetchall()

    lines = [
        "# Tēmas — Indekss",
        "",
        f"_Atjaunots: {now}_",
        "",
        f"**{len(rows)}** tēmas",
        "",
        "| Tēma | Pozīcijas | Balsojumi | Politiķi | Pretrunas | Pēdējā poz. aktivitāte |",
        "|---|---|---|---|---|---|",
    ]
    for r in rows:
        slug = _slugify(r["topic"])
        last = (r["last_activity"] or "")[:10] or "—"
        lines.append(
            f"| [[topics/{slug}\\|{r['topic']}]] | {r['positions']} | {r['votes']} | {r['politicians']} | {r['contradictions']} | {last} |"
        )
    lines.append("")
    return "\n".join(lines) + "\n"


def _build_parties_index(db: sqlite3.Connection) -> str:
    """Build parties/partijas.md — all parties in a single table.

    "Pozīcijas" kolonna skaita TIKAI claim_type='position' (retorika), nevis
    visi claims (kas iekļautu arī saeima_vote claims un dubultoti ar Par/Pret/
    Atturas balsojumu kolonnām blakus). Saeima vote totals ir Par+Pret+Atturas.
    """
    now = _now_lv()

    rows = db.execute("""
        SELECT tp.party,
               COUNT(DISTINCT tp.id) AS members,
               COUNT(DISTINCT CASE WHEN c.claim_type='position' THEN c.id END) AS positions,
               COUNT(DISTINCT ct.id) AS contradictions
        FROM tracked_politicians tp
        LEFT JOIN claims c ON c.opponent_id = tp.id
        LEFT JOIN contradictions ct ON ct.opponent_id = tp.id
        WHERE tp.relationship_type != 'inactive' AND tp.party IS NOT NULL
        GROUP BY tp.party
        ORDER BY positions DESC
    """).fetchall()

    # Vote stats per party
    vote_stats = {}
    for pr in rows:
        vs = db.execute("""
            SELECT SUM(CASE WHEN siv.vote='Par' THEN 1 ELSE 0 END) AS par,
                   SUM(CASE WHEN siv.vote='Pret' THEN 1 ELSE 0 END) AS pret,
                   SUM(CASE WHEN siv.vote='Atturas' THEN 1 ELSE 0 END) AS atturas
            FROM saeima_individual_votes siv
            JOIN tracked_politicians p ON siv.politician_id = p.id
            WHERE p.party = ?
        """, (pr["party"],)).fetchone()
        vote_stats[pr["party"]] = vs

    lines = [
        "# Partijas — Indekss",
        "",
        f"_Atjaunots: {now}_",
        "",
        f"**{len(rows)}** partijas",
        "",
        "| Partija | Biedri | Pozīcijas | Pretrunas | Par | Pret | Atturas |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        slug = _slugify(r["party"])
        vs = vote_stats.get(r["party"])
        par = (vs["par"] or 0) if vs else 0
        pret = (vs["pret"] or 0) if vs else 0
        atturas = (vs["atturas"] or 0) if vs else 0
        lines.append(
            f"| [[parties/{slug}\\|{r['party']}]] | {r['members']} | {r['positions']} | {r['contradictions']} | {par} | {pret} | {atturas} |"
        )
    lines.append("")
    return "\n".join(lines) + "\n"


def _build_laws_index(wiki_dir: Path) -> str:
    """Build laws/likumi.md — parsed from existing law files."""
    now = _now_lv()
    laws_dir = wiki_dir / "laws"
    if not laws_dir.exists():
        return "# Likumi — Indekss\n\nNav likumu.\n"

    entries = []
    for p in sorted(laws_dir.glob("*.md")):
        # Skip the index file itself (current canonical name and any legacy)
        if p.stem in ("likumi", "index"):
            continue
        text = p.read_text(encoding="utf-8")
        # Parse title from first # heading
        title_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else p.stem
        # Parse vote count
        votes_match = re.search(r"\*\*Saistītie balsojumi:\*\*\s*(\d+)", text)
        votes = int(votes_match.group(1)) if votes_match else 0
        entries.append({"slug": p.stem, "title": title, "votes": votes})

    entries.sort(key=lambda e: e["votes"], reverse=True)

    lines = [
        "# Likumi — Indekss",
        "",
        f"_Atjaunots: {now}_",
        "",
        f"**{len(entries)}** likumi",
        "",
        "| Likums | Saistītie balsojumi |",
        "|---|---|",
    ]
    for e in entries:
        lines.append(f"| [[laws/{e['slug']}\\|{e['title']}]] | {e['votes']} |")
    lines.append("")
    return "\n".join(lines) + "\n"


def _build_mediji_page() -> str:
    """wiki/mediji.md — konfigurācijas spogulis no sources.yaml outlets:.
    Tikai config (load_outlets), BEZ DB joiniem — skaitļi dzīvo publiskajā
    lapā mediji.html; šī ir operatora reģistrs (spec 2026-06-10)."""
    from src.outlets import load_outlets
    outlets = load_outlets()
    lines = [
        "# Mediji",
        "",
        f"_Konfigurācijas spogulis no `sources.yaml` (`outlets:`); atjaunots: {_now_lv()}_",
        "",
        "Caurskatāmības fakti un pārklājums dzīvo publiskajā vietnē "
        "(`mediji.html`, `mediji/<slug>.html`); šī lapa ir operatora reģistrs.",
        "",
        "| Medijs | Tips | Hosti | X feedi |",
        "|---|---|---|---|",
    ]
    for o in outlets:
        feeds = ", ".join(f"@{h}" for h in o.get("x_feeds") or []) or "—"
        lines.append(f"| {o['name']} | {o['type'] or '—'} | "
                     f"{', '.join(o['hosts'])} | {feeds} |")
    return "\n".join(lines) + "\n"


def _build_index(
    db: sqlite3.Connection,
    wiki_dir: Path,
    db_path: str = DEFAULT_DB_PATH,
) -> str:
    """Build index.md as a concise table of contents with status overview."""
    now = _now_lv()

    # --- Status overview ---
    total_politicians = db.execute(
        "SELECT COUNT(*) FROM tracked_politicians WHERE relationship_type != 'inactive'"
    ).fetchone()[0]
    # Saeima vs media split — the raw total_claims hides the fact that ~88%
    # of rows are legislative votes (one claim per MP per bill), not first-
    # person policy positions. Reporting both lets readers see the real
    # rhetorical-coverage denominator. Post Phase A of the claim_type split
    # migration, the split uses the authoritative claim_type column rather
    # than the fragile source_url LIKE heuristic.
    saeima_claims = db.execute(
        "SELECT COUNT(*) FROM claims WHERE claim_type = 'saeima_vote'"
    ).fetchone()[0]
    media_claims = db.execute(
        "SELECT COUNT(*) FROM claims WHERE claim_type = 'position'"
    ).fetchone()[0]

    # Phase C's dual-read guard (comparing claim_type counts against the
    # documents.platform join) was removed here in Phase D2 — it ran for
    # one phase without firing, confirming the invariant holds.

    total_contradictions = db.execute("SELECT COUNT(*) FROM contradictions").fetchone()[0]
    total_docs = db.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    total_topics = db.execute(
        "SELECT COUNT(DISTINCT topic) FROM claims WHERE topic IS NOT NULL"
    ).fetchone()[0]

    # Backlog accounting — the previous metric counted any subject-linked web
    # doc without a claim row, which conflated two very different states:
    #   (a) never reviewed by an extractor (real backlog)
    #   (b) reviewed and judged empty (ceremonial, duplicate, off-topic)
    # Reporting them separately prevents false urgency (the 2026-04-10 audit
    # found the old metric showed 209 "unprocessed" when the real unreviewed
    # count was 0). Filters use documents.platform (authoritative) rather
    # than the legacy source_url LIKE heuristic.
    true_backlog = db.execute("""
        SELECT COUNT(DISTINCT d.id)
        FROM documents d
        JOIN document_politicians dp ON dp.document_id = d.id
        WHERE d.reviewed_at IS NULL
          AND d.platform = 'web'
          AND dp.role = 'subject'
    """).fetchone()[0]
    reviewed_empty = db.execute("""
        SELECT COUNT(DISTINCT d.id)
        FROM documents d
        JOIN document_politicians dp ON dp.document_id = d.id
        LEFT JOIN claims c ON c.document_id = d.id
        WHERE d.reviewed_at IS NOT NULL
          AND c.id IS NULL
          AND d.platform = 'web'
          AND dp.role = 'subject'
    """).fetchone()[0]

    # Media coverage health — the headline metric for the rhetorical side of
    # the project. Median position claims per active politician is a better
    # health signal than raw totals because legislative votes dominate the
    # totals. `zero_media_count` surfaces politicians with no first-person
    # extracted statements at all. Uses claim_type='position' as the
    # authoritative filter post Phase A.
    media_per_politician = [
        row[0] for row in db.execute("""
            SELECT COUNT(CASE WHEN c.claim_type = 'position' THEN 1 END)
            FROM tracked_politicians tp
            LEFT JOIN claims c ON c.opponent_id = tp.id
            WHERE tp.relationship_type != 'inactive'
            GROUP BY tp.id
        """).fetchall()
    ]
    if media_per_politician:
        sorted_media = sorted(media_per_politician)
        n = len(sorted_media)
        if n % 2 == 1:
            media_median = sorted_media[n // 2]
        else:
            media_median = (sorted_media[n // 2 - 1] + sorted_media[n // 2]) / 2
        zero_media_count = sum(1 for v in sorted_media if v == 0)
    else:
        media_median = 0
        zero_media_count = 0

    # Last ingest
    last_ingest = db.execute(
        "SELECT MAX(scraped_at) FROM documents"
    ).fetchone()[0] or "nav"

    # Lint stats — pass db_path through so hermetic tests (and any non-default
    # DB) lint against the same DB wiki_sync was given, not the live default.
    from src.wiki_lint import lint_wiki_with_db
    lint = lint_wiki_with_db(str(wiki_dir), db_path)
    lint_s = lint["stats"]

    # Recent claims (last 7 days) — filtered to positions only so the
    # leaderboard reflects who actually spoke publicly rather than who
    # happened to be present for a bulk Saeima vote import. Post Phase A
    # of the claim_type split, uses the authoritative claim_type column.
    recent_claims = db.execute("""
        SELECT p.name, COUNT(c.id) as cnt
        FROM claims c JOIN tracked_politicians p ON c.opponent_id = p.id
        WHERE c.created_at >= datetime('now', '-7 days')
          AND c.claim_type = 'position'
        GROUP BY p.id ORDER BY cnt DESC LIMIT 5
    """).fetchall()

    # Distinct non-NULL parties among active politicians — only the row COUNT
    # feeds the "X partijas" Struktūra line. `party IS NOT NULL` mirrors
    # _build_parties_index: active tracked entities without a party
    # (journalists, news outlets, orgs) must not form a phantom party bucket
    # that inflates the count vs the partijas.md headline this links to
    # (the 16-vs-15 bug). This query previously also computed members/claims
    # via a LEFT JOIN on the ~511k-row claims table — both columns were unused
    # and the join was pure waste; dropped.
    party_rows = db.execute("""
        SELECT DISTINCT party
        FROM tracked_politicians
        WHERE relationship_type != 'inactive' AND party IS NOT NULL
    """).fetchall()

    # Synthesis pages
    synthesis_dir = wiki_dir / "synthesis"
    synthesis_files = sorted(synthesis_dir.glob("*.md")) if synthesis_dir.exists() else []

    # Laws
    laws_dir = wiki_dir / "laws"
    laws_count = len([p for p in laws_dir.glob("*.md") if p.stem not in ("likumi", "index")]) if laws_dir.exists() else 0

    # Format median nicely (1.5 → "1.5", 2.0 → "2")
    if isinstance(media_median, float) and media_median.is_integer():
        media_median_str = str(int(media_median))
    else:
        media_median_str = str(media_median)

    # --- Build content ---
    lines = [
        "# atmina — Indekss",
        "",
        f"_Atjaunots: {now}_",
        "",
        "> **Kas mainījās 2026-04-11:** Pozīcijas un Saeimas balsojumi tagad "
        "tiek skaitīti atsevišķi. Agrāk \"pozīciju\" skaits apvienoja abus "
        "un izskatījās 8× lielāks par faktisko retorisko aktivitāti. "
        "Skaitļi nav mazāki — tie ir pārklasificēti.",
        "",
        "## Stāvoklis",
        "",
        f"- **{total_politicians}** politiķi, **{media_claims}** pozīcijas + **{saeima_claims}** Saeimas balsojumi, **{total_contradictions}** pretrunas, **{total_docs}** dokumenti",
        f"- **{total_topics}** tēmas, **{laws_count}** likumi",
        f"- Pēdējais ingest: {last_ingest[:16] if last_ingest != 'nav' else 'nav'}",
        f"- Media pārklājums: mediāns {media_median_str} claims/politiķi, {zero_media_count}/{total_politicians} bez neviena media claim",
    ]

    if true_backlog > 0:
        lines.append(f"- Nepārskatīts backlog: {true_backlog} ziņu raksti")
    if reviewed_empty > 0:
        lines.append(
            f"- Pārskatīti bez claims: {reviewed_empty} (ceremoniāli/dublikāti — "
            f"re-extraction var atgūt daļu)"
        )

    if lint_s["total_issues"] > 0:
        lines.append(f"- Lint: {lint_s['orphans']} orphans, {lint_s['broken_links']} broken links")

    if recent_claims:
        names = ", ".join(f"{r['name']} ({r['cnt']})" for r in recent_claims[:5])
        lines.append(f"- Pēdējo 7 dienu media claims: {names}")

    # Mirror the personas.md headline count: position-only, filtered to active
    # politicians. The previous sum included saeima_vote + commentary across
    # active politicians (~19 k) and labelled it "pozīcijas", which collided
    # with the 2026-04-11 Saeima vote split semantics. Two numbers should
    # match: this link's count and persons/personas.md's headline.
    active_positions = db.execute(
        """SELECT COUNT(c.id)
           FROM claims c
           JOIN tracked_politicians tp ON tp.id = c.opponent_id
           WHERE c.claim_type = 'position'
             AND tp.relationship_type != 'inactive'"""
    ).fetchone()[0]

    lines += [
        "",
        "## Struktūra",
        "",
        f"- [[persons/personas|Politiķi]] — {total_politicians} profili, {active_positions} pozīcijas",
        f"- [[parties/partijas|Partijas]] — {len(party_rows)} partijas",
        f"- [[topics/temas|Tēmas]] — {total_topics} tēmas",
    ]
    # Mediji — config-driven (sources.yaml outlets:); wiki/mediji.md ir
    # wiki_sync ģenerēts konfigurācijas spogulis (sk. _build_mediji_page).
    from src.outlets import load_outlets
    n_outlets = len(load_outlets())
    if n_outlets:
        lines.append(
            f"- [[mediji|Mediji]] — {n_outlets} mediju caurskatāmības profili "
            "(publiskā vietne `mediji.html`)"
        )
    if laws_count:
        lines.append(f"- [[laws/likumi|Likumi]] — {laws_count} likumi")
    if synthesis_files:
        lines.append(f"- `synthesis/` — {len(synthesis_files)} starppartiju analīzes")
    lines.append("- [[operations/operacijas|Operācijas]] — rutīnas, rokasgrāmatas, aģentu apraksti")
    lines.append("- [[operations/atmina-ops|atmina ops]] — lokāls operatora dashboard (`python serve.py`)")
    lines.append("- [[log-ingest|Ielādes žurnāls]] — dokumentu ielādes vēsture")
    lines.append("")

    # Bases panels — static .base files in wiki/ root (not regenerated by this
    # sync; they query live frontmatter). Require Obsidian 1.9+. Embedding the
    # compact "ar pretrunām" view here surfaces the operator's review list at
    # the vault entry point; the full tables stay one click away.
    lines += [
        "## Paneļi (Bases)",
        "",
        "- [[politiki.base|Politiķu dzīvais panelis]] — filtrē/kārto pēc partijas, pozīcijām, pretrunām",
        "- [[pretrunas.base|Pretrunu fokuss]] — politiķi un partijas ar pretrunām",
        "",
        "![[pretrunas.base#Politiķi ar pretrunām]]",
        "",
    ]

    return "\n".join(lines)


def _append_log(wiki_dir: Path, message: str) -> None:
    """Append a log entry to wiki/log.md."""
    log_path = wiki_dir / "log.md"
    timestamp = _now_lv()
    entry = f"- {timestamp}: {message}\n"
    with log_path.open("a", encoding="utf-8") as f:
        f.write(entry)


def wiki_sync(
    db_path: str = DEFAULT_DB_PATH,
    wiki_dir: str = DEFAULT_WIKI_DIR,
) -> dict:
    """Sync DB data into the wiki vault.

    Returns a summary dict: {persons, topics, updated_at}.

    What this touches (patch the template here instead of hand-editing):
      - FULLY overwritten each run — hand-edits are silently lost:
        wiki/index.md, wiki/mediji.md, and the four sub-indexes personas.md /
        temas.md / partijas.md / likumi.md.
      - PARTIALLY regenerated — frontmatter + the SYNC-AUTO / BILLS-SYNC-AUTO
        blocks are rewritten, the rest of the body is preserved (_update_page):
        wiki/persons/*.md, wiki/topics/*.md, wiki/parties/*.md, wiki/laws/*.md.
      - NOT touched — safe to hand-edit: wiki/operations/*.md, wiki/CHANGELOG.md,
        wiki/dailies/*.md, wiki/synthesis/*.md, wiki/log-ingest/*.md.
    (2026-05-17: a hand-added link in the fully-overwritten index.md was dropped
    by the next sync; that class of regression is why this list exists.)
    """
    wiki = Path(wiki_dir)
    persons_dir = wiki / "persons"
    topics_dir = wiki / "topics"

    parties_dir = wiki / "parties"

    laws_dir = wiki / "laws"

    # Ensure directories exist
    for d in [wiki, persons_dir, topics_dir, parties_dir, laws_dir, wiki / "synthesis", wiki / "dailies"]:
        d.mkdir(parents=True, exist_ok=True)

    db = get_db(db_path)

    # Sync person pages — only active politicians get wiki pages.
    # Inactive entries (sentinels like 'Nepareizais', 'Kas Notiek Latvijā',
    # retired deputies) are excluded by design: _build_persons_index also
    # excludes them, so generating their pages would create permanent
    # orphans flagged by wiki_lint on every run.
    politicians = db.execute(
        "SELECT * FROM tracked_politicians "
        "WHERE relationship_type != 'inactive' "
        "ORDER BY name"
    ).fetchall()

    persons_synced = 0
    for politician in politicians:
        slug = _slugify(politician["name"])
        page_path = persons_dir / f"{slug}.md"
        fm = _build_person_frontmatter(db, politician)
        signal = _gather_person_signal(db, politician["id"])
        sync_block = _render_person_synthesis(signal)
        _update_page_with_sync_block(page_path, fm, sync_block)
        persons_synced += 1

    # Sync topic pages
    topic_rows = db.execute(
        "SELECT DISTINCT topic FROM claims WHERE topic IS NOT NULL ORDER BY topic"
    ).fetchall()

    topics_synced = 0
    for row in topic_rows:
        topic = row["topic"]
        slug = _slugify(topic)
        page_path = topics_dir / f"{slug}.md"
        fm = _build_topic_frontmatter(db, topic)
        _update_page(page_path, fm)
        topics_synced += 1

    # Sync party pages
    party_rows = db.execute("""
        SELECT party, COUNT(DISTINCT id) AS members,
               (SELECT COUNT(*) FROM claims c WHERE c.opponent_id IN
                (SELECT id FROM tracked_politicians WHERE party = tp.party)) AS claims,
               (SELECT COUNT(*) FROM contradictions ct WHERE ct.opponent_id IN
                (SELECT id FROM tracked_politicians WHERE party = tp.party)) AS contradictions
        FROM tracked_politicians tp
        WHERE party IS NOT NULL AND relationship_type != 'inactive'
        GROUP BY party ORDER BY claims DESC
    """).fetchall()

    parties_synced = 0
    for pr in party_rows:
        party = pr["party"]
        slug = _slugify(party)
        page_path = parties_dir / f"{slug}.md"

        top_pols = db.execute("""
            SELECT p.name, COUNT(c.id) AS cnt
            FROM claims c JOIN tracked_politicians p ON c.opponent_id = p.id
            WHERE p.party = ? GROUP BY p.id ORDER BY cnt DESC LIMIT 5
        """, (party,)).fetchall()

        top_topics = db.execute("""
            SELECT c.topic, COUNT(*) AS cnt
            FROM claims c JOIN tracked_politicians p ON c.opponent_id = p.id
            WHERE p.party = ? AND c.topic IS NOT NULL
            GROUP BY c.topic ORDER BY cnt DESC LIMIT 5
        """, (party,)).fetchall()

        vote_stats = db.execute("""
            SELECT SUM(CASE WHEN siv.vote='Par' THEN 1 ELSE 0 END) AS par,
                   SUM(CASE WHEN siv.vote='Pret' THEN 1 ELSE 0 END) AS pret,
                   SUM(CASE WHEN siv.vote='Atturas' THEN 1 ELSE 0 END) AS atturas
            FROM saeima_individual_votes siv
            JOIN tracked_politicians p ON siv.politician_id = p.id
            WHERE p.party = ?
        """, (party,)).fetchone()

        members = db.execute("""
            SELECT name FROM tracked_politicians
            WHERE party = ? AND relationship_type != 'inactive' ORDER BY name
        """, (party,)).fetchall()

        fm = {
            "party": party,
            "members": pr["members"],
            "claims": pr["claims"],
            "contradictions": pr["contradictions"],
            "votes_par": vote_stats["par"] or 0,
            "votes_pret": vote_stats["pret"] or 0,
            "votes_atturas": vote_stats["atturas"] or 0,
            "top_politicians": [t["name"] for t in top_pols],
            "top_topics": [t["topic"] for t in top_topics],
        }

        body = "\n## Biedri\n\n"
        for m in members:
            mslug = _slugify(m["name"])
            body += f"- [[persons/{mslug}|{m['name']}]]\n"

        _update_page(page_path, fm, body)
        parties_synced += 1

    # Phase 1B-ii — render BILLS-SYNC-AUTO blocks in wiki/laws/<slug>.md
    if laws_dir.exists():
        bills_changed = 0
        for md_file in laws_dir.glob("*.md"):
            if md_file.name == "likumi.md":
                continue
            slug = md_file.stem
            if _render_law_bills_block(slug, db, md_file):
                bills_changed += 1
        if bills_changed:
            logger.info("wiki_sync: BILLS-SYNC-AUTO updated in %d wiki/laws files", bills_changed)

    # Write sub-indexes (fully overwritten each sync). File names are the
    # Latvian semantic equivalents of the folder names (personas.md instead
    # of index.md, etc.) so that Obsidian's graph view shows meaningful
    # node labels rather than five identical "index" nodes. Mapping must
    # stay in sync with src/wiki_lint.py::_SUBDIR_INDEX.
    (persons_dir / "personas.md").write_text(_build_persons_index(db), encoding="utf-8")
    (topics_dir / "temas.md").write_text(_build_topics_index(db), encoding="utf-8")
    (parties_dir / "partijas.md").write_text(_build_parties_index(db), encoding="utf-8")
    (laws_dir / "likumi.md").write_text(_build_laws_index(wiki), encoding="utf-8")

    # Write main index. The wiki root stays index.md (not a Latvian name like
    # the sub-indexes above): Obsidian recognises index.md as the vault home note.
    index_content = _build_index(db, wiki, db_path)
    (wiki / "index.md").write_text(index_content, encoding="utf-8")
    (wiki / "mediji.md").write_text(_build_mediji_page(), encoding="utf-8")

    db.close()

    result = {
        "persons": persons_synced,
        "topics": topics_synced,
        "parties": parties_synced,
        "updated_at": _now_lv(),
    }

    logger.info("wiki_sync complete: %s", result)

    # Run wiki lint check (also used by _build_index for status)
    lint_result = lint_wiki_with_db(wiki_dir, db_path)

    result["lint"] = lint_result["stats"]

    return result
