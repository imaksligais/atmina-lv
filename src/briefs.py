"""Neutral daily/weekly brief generator for atmina.lv blog."""

import re
from datetime import datetime, timedelta
from pathlib import Path

from src.db import get_db, now_lv_dt

_DB_PATH = Path(__file__).parent.parent / "data" / "atmina.db"


# A claim belongs to a given day's brief if it was stated that day OR extracted
# (created) that day about a statement made within the last 7 days. The
# created_at arm catches the common "politician spoke yesterday, we extracted
# today" case that a pure date(stated_at)=today filter silently dropped (audit
# 2026-06-08, feedback_brief_writer_scoping_gaps). The 7-day floor on stated_at
# keeps bulk historical backfills (stated years ago, created today) out of
# today's brief.
#
# The `already_briefed` guard on the created_at arm (Fix 3, 2026-07-16) closes
# the backfill double-publish hole: a claim stated yesterday and created today
# would surface in TODAY's brief even though YESTERDAY's brief already covered
# that stated-day — the 07-13 and 07-16 incidents. A claim is dropped from the
# created_at arm ONLY when a daily_brief note for its OWN stated-day exists whose
# publish/refresh timestamp is AFTER the claim's created_at — i.e. the claim was
# already in the DB when that day was briefed. This is deliberately narrow:
# claims extracted AFTER their day's brief was published (created_at later than
# the note) are NOT dropped — they legitimately belong in today's brief because
# yesterday's could not have included them. The first disjunct
# (date(stated_at)=day) is untouched, so same-day refresh always re-includes.
#
# NB: context_notes has no updated_at column, so created_at IS the note's
# publish/refresh timestamp (same-day re-runs UPSERT and bump created_at). The
# daily_brief subject-day is encoded in `topic` as 'dienas analīze YYYY-MM-DD'
# (see generate_daily_brief H1 + store path). Both created_at columns are LV
# (now_lv), format 'YYYY-MM-DD HH:MM:SS', so the string comparison is direct.
# Use with the `claims c` alias; bind via _brief_day_params().
#
# Every reader MUST build the topic through DAILY_BRIEF_TOPIC_PREFIX /
# daily_brief_topic(). The literal was previously repeated by hand, and the
# telegram path drifted to 'dienas pārskats {date}' — a form nothing ever
# writes, so its lookup silently matched no row and the summary bullets were
# always empty (BACKLOG 2026-07-16, fixed 2026-07-25). A wrong topic string
# here does not raise; it just returns nothing.
DAILY_BRIEF_TOPIC_PREFIX = "dienas analīze "


def daily_brief_topic(date: str) -> str:
    """Return the `context_notes.topic` value for a given brief day."""
    return f"{DAILY_BRIEF_TOPIC_PREFIX}{date}"


_SUBJECT_DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")


def brief_subject_date(
    topic: str | None,
    content: str | None = None,
    created_at: str | None = None,
) -> str | None:
    """The day a brief is ABOUT — which is not the day it was written.

    A brief's identity is its subject date: the routine day it covers. That is
    NOT ``created_at``. The evening routine routinely stores after midnight, and
    a regenerated brief carries a timestamp from a different day entirely.

    Deriving the subject day from ``created_at`` produced two live defects, in
    opposite directions. False green: on 2026-07-29 both ``_check_daily_brief``
    and ``_check_featured_image`` reported done because the 07-28 brief had been
    stored at 00:04 that morning — and step 8 even named the wrong brief ("brief
    383"). That pair of green ticks was the only thing standing between an
    outage-killed routine and the operator noticing it. False red: whenever
    tonight's brief lands after midnight, the day it covers looks briefless.

    Priority: ``topic`` -> the H1 (first line of content) -> ``created_at``, the
    last only for legacy rows written before the topic convention. Only the
    FIRST line of content is searched — dates occur throughout a brief body,
    while the H1 is its title.

    Returns None when no source yields a date.
    """
    m = _SUBJECT_DATE_RE.search(topic or "")
    if m:
        return m.group(1)
    first_line = (content or "").lstrip().split("\n", 1)[0]
    m = _SUBJECT_DATE_RE.search(first_line)
    if m:
        return m.group(1)
    if created_at:
        return created_at[:10]
    return None


PUBLISH_KEY_RE = re.compile(r"^(?:nedela-)?\d{4}-\d{2}-\d{2}$")


def brief_publish_key(note_type: str | None, subject_date: str) -> str:
    """The identity a publish approval hangs on: the brief's BLOG PAGE slug.

    `src/render/blog.py` slugs a weekly brief as ``nedela-<subject_date>`` and a
    daily one as ``<subject_date>``. Both can carry the SAME subject date (a
    weekly brief's topic names the week's first day), so the date alone is not a
    unique brief identity — a weekly approval would silently cover the daily
    page for the same day. Keying on the slug is also what makes the approval
    survive a brief regeneration: `context_notes.id` changes, the slug does not.
    """
    return f"nedela-{subject_date}" if note_type == "weekly_brief" else subject_date


_BRIEF_DAY_CLAIM_SQL = (
    "(date(c.stated_at) = ? OR "
    "(date(c.created_at) = ? AND date(c.stated_at) >= date(?, '-7 days') "
    "AND NOT EXISTS ("
    "SELECT 1 FROM context_notes _nb "
    "WHERE _nb.note_type = 'daily_brief' "
    f"AND _nb.topic = '{DAILY_BRIEF_TOPIC_PREFIX}' || date(c.stated_at) "
    "AND _nb.created_at > c.created_at)))"
)


def _source_link(url: str | None) -> str:
    """Render a claim's source URL as a `[domain](url)` markdown link, or '—' when
    absent. Domain = host with www. stripped, truncated to 20 chars for display.
    Shared by the per-topic positions table and the Pārējās tēmas table so the
    formatting stays in one place."""
    url = url or ""
    if not url:
        return "—"
    domain = url.split("//")[-1].split("/")[0].replace("www.", "")
    if len(domain) > 20:
        domain = domain[:20]
    return f"[{domain}]({url})"


def _brief_day_params(day: str) -> tuple[str, str, str]:
    """Bind order for _BRIEF_DAY_CLAIM_SQL: (stated==day, created==day, floor).
    The already_briefed NOT EXISTS guard is correlated (c.stated_at/created_at),
    so it adds no bind params."""
    return (day, day, day)


# 2026-06-10 operatora noteikums: dienas pārskata tabulās saturu NEgriež.
# Agrākais _truncate_stance (220 simbolu vārda-robežas elipse) un dažādie
# kailie [:N] slices radīja vidū apgrieztus teikumus publicētajā lapā
# ("…nekavējoties ne"). HTML tabulu šūnas aplaužas pašas — pilns teksts.


def generate_daily_brief(db_path: str = None, date: str = None) -> str:
    """Generate a neutral daily brief in markdown. No campaign framing."""
    db_path = db_path or str(_DB_PATH)
    date = date or now_lv_dt().strftime("%Y-%m-%d")
    db = get_db(db_path)

    # Per-platform, never by subtraction: `doc_count - web_count` dumped every
    # non-web platform into the Twitter/X bucket — the 08-03 brief reported
    # "561 Twitter/X" where 24 were vestnesis (BACKLOG 2026-08-04). Unknown
    # platforms surface as `citi` instead of inflating a named bucket.
    platform_counts = dict(
        db.execute(
            "SELECT platform, COUNT(*) FROM documents"
            " WHERE date(scraped_at) = ? GROUP BY platform",
            (date,),
        ).fetchall()
    )
    doc_count = sum(platform_counts.values())
    web_count = platform_counts.pop("web", 0)
    x_count = platform_counts.pop("twitter", 0) + platform_counts.pop("x_mention", 0)
    vestnesis_count = platform_counts.pop("vestnesis", 0)
    other_count = sum(platform_counts.values())

    # Audience / context accounts (journalists, influencers, neutral analysts,
    # organizations) ARE emitted in the topic tables since 2026-08-03 (operator
    # decision). They used to be filtered out of every section, which silently
    # dropped 11 of 50 positions on 2026-07-31 — all four Valsts kontrole audit
    # findings among them — and brief-writer re-added the rows by hand each day.
    # That was the T7 mechanism (loss by construction) on the relationship_type
    # axis, and it contradicted seeding.md's Institucionālā balss convention:
    # an audit finding is exactly the content the entity was seeded to capture.
    #
    # `inactive` stays excluded EVERYWHERE — it hides sentinel entries and
    # retired deputies and is not an audience type.
    #
    # Still audience-filtered on purpose, because they are not topic tables:
    # the Aktīvākie leaderboard (a ranking OF politicians), the cross-party
    # narrative hint (party-based; audience accounts carry no party), and the
    # Koalīcija vs Opozīcija bloc split (which handles them explicitly in its
    # own disjoint Neitrāli row).

    # DIENAS STATS pozīciju skaits — TIEŠI tas pats dienas-loga predikāts
    # (_BRIEF_DAY_CLAIM_SQL, Fix 3-korekcija ieskaitot) + claim_type='position'
    # kā ###-emisijas vaicājumi, lai STATS skaitlis sakristu ar publicētajām
    # pozīcijām (Fix 2, 2026-07-16).
    #
    # position_count tagad skaita VISU, ko tabulas emitē (viss ne-inaktīvais).
    # Iepriekš tas izslēdza audience un org, kamēr pats STATS teksts org tomēr
    # pieskaitīja kopsummai — tāpēc pārskats paziņoja vairāk pozīciju, nekā
    # uzskaitīja (40 pret 47/48, 2026-07-31), un žurnālistu rindas neparādījās
    # ne vienā, ne otrā skaitā. Sadalījums paliek informatīvs, bet abas puses
    # tagad summējas uz emitēto.
    position_count = db.execute(
        f"""SELECT COUNT(*) FROM claims c
           JOIN tracked_politicians p ON c.opponent_id = p.id
           WHERE {_BRIEF_DAY_CLAIM_SQL} AND c.claim_type = 'position'
             AND p.relationship_type != 'inactive'""",
        _brief_day_params(date),
    ).fetchone()[0]
    audience_count = db.execute(
        f"""SELECT COUNT(*) FROM claims c
           JOIN tracked_politicians p ON c.opponent_id = p.id
           WHERE {_BRIEF_DAY_CLAIM_SQL} AND c.claim_type = 'position'
             AND p.relationship_type IN ('journalist','influencer','neutral','organization')""",
        _brief_day_params(date),
    ).fetchone()[0]
    politician_count = position_count - audience_count
    contradiction_count = db.execute(
        "SELECT COUNT(*) FROM contradictions WHERE date(detected_at) = ? "
        "AND COALESCE(confirmed, 1) = 1",
        (date,),
    ).fetchone()[0]

    # Active politicians: position-only so the leaderboard reflects who
    # actually spoke rather than who happened to be present for a bulk
    # vote import.
    #
    # The `p.name` tie-break is load-bearing, not cosmetic. On a normal day most
    # politicians sit at cnt=1 (2026-08-07: 14 of 15 tied), so `cnt DESC` alone
    # left the cut to SQLite's `GROUP BY p.id` order — i.e. seeding recency.
    # That is not neutral: recently seeded cohorts cluster at high ids, and on
    # 2026-08-07 one party took 3 of the 7 rows on 4 of 18 positions while the
    # coalition took 2 rows on 8 of 18. Alphabetical is still an arbitrary cut
    # among ties, but it is stable across runs and uncorrelated with party.
    active = db.execute(f"""
        SELECT p.name, p.party, COUNT(*) as cnt,
            GROUP_CONCAT(DISTINCT c.topic) as topics
        FROM claims c
        JOIN tracked_politicians p ON c.opponent_id = p.id
        WHERE {_BRIEF_DAY_CLAIM_SQL}
          AND c.claim_type = 'position'
          AND p.relationship_type NOT IN ('journalist','influencer','neutral','inactive','organization')
        GROUP BY p.id ORDER BY cnt DESC, p.name ASC LIMIT 7
    """, _brief_day_params(date)).fetchall()

    # Coalition map needed both for per-topic synthesis hints and for the
    # Koalīcija vs Opozīcija section further down.
    from src.coalition import get_coalition_map
    coalition_map = get_coalition_map(db)

    # Rank topics by "interestingness": position count + bonus for tensions
    # and contradictions — a topic with 3 positions and 2 tensions is more
    # newsworthy than one with 6 positions and 0 tensions.
    # T7 fix (2026-07-24): no LIMIT here — full ### sections are top-5 by
    # interest_score PLUS every topic with cnt>=3 (split in Python below); the
    # remainder is collapsed into one `### Pārējās tēmas` table. max_salience
    # orders the Pārējās rows. Previously `LIMIT 5` silently dropped ~5
    # important topics/day, incl. a 5-position topic on 2026-07-23.
    by_topic = db.execute(f"""
        SELECT c.topic, COUNT(*) as cnt,
            COALESCE(tens.t_cnt, 0) as tension_cnt,
            COALESCE(cont.c_cnt, 0) as contradiction_cnt,
            COUNT(*) + COALESCE(tens.t_cnt, 0) * 3 + COALESCE(cont.c_cnt, 0) * 2 as interest_score,
            MAX(c.salience) as max_salience
        FROM claims c
        JOIN tracked_politicians p ON c.opponent_id = p.id
        LEFT JOIN (
            -- 'localtime': political_tensions.created_at is UTC (schema.sql).
            SELECT topic, COUNT(*) as t_cnt FROM political_tensions
            WHERE date(created_at, 'localtime') = ? GROUP BY topic
        ) tens ON tens.topic = c.topic
        LEFT JOIN (
            SELECT c2.topic, COUNT(*) as c_cnt FROM contradictions con
            JOIN claims c2 ON con.claim_old_id = c2.id OR con.claim_new_id = c2.id
            WHERE date(con.detected_at) = ?
              AND COALESCE(con.confirmed, 1) = 1
            GROUP BY c2.topic
        ) cont ON cont.topic = c.topic
        WHERE {_BRIEF_DAY_CLAIM_SQL} AND c.claim_type = 'position'
          AND p.relationship_type != 'inactive'
        GROUP BY c.topic ORDER BY interest_score DESC
    """, (date, date, *_brief_day_params(date))).fetchall()

    # Split the ranked topics: a topic gets a full ### section when it is in the
    # top 5 by interest_score OR carries cnt>=3 (regardless of rank). The order
    # stays interest_score DESC — the cnt>=3 topics simply aren't cut. Everything
    # else flows to the Pārējās tēmas table.
    full_topics = [r for i, r in enumerate(by_topic) if i < 5 or r["cnt"] >= 3]
    rest_topics = [r for i, r in enumerate(by_topic) if not (i < 5 or r["cnt"] >= 3)]

    # Narrative hints for @brief-writer: which topics have cross-party
    # conflict, who clashed with whom, what tensions dominate the day.
    # Party suffix only when a party exists — bezpartejiskie (party NULL/'')
    # must render as bare name, never 'Vārds ()'. The CASE emits ' (JV)' or ''.
    top_tension_topics = db.execute("""
        SELECT t.topic, COUNT(*) as cnt,
            GROUP_CONCAT(DISTINCT sp.name
                || CASE WHEN COALESCE(sp.party,'') <> '' THEN ' (' || sp.party || ')' ELSE '' END
                || ' → ' || tp.name
                || CASE WHEN COALESCE(tp.party,'') <> '' THEN ' (' || tp.party || ')' ELSE '' END
            ) as pairs
        FROM political_tensions t
        JOIN tracked_politicians sp ON t.source_pid = sp.id
        JOIN tracked_politicians tp ON t.target_pid = tp.id
        -- 'localtime': political_tensions.created_at is UTC (schema.sql).
        WHERE date(t.created_at, 'localtime') = ?
        GROUP BY t.topic ORDER BY cnt DESC LIMIT 3
    """, (date,)).fetchall()

    cross_party_clashes = db.execute(f"""
        SELECT c.topic, COUNT(DISTINCT p.party) as party_cnt,
            GROUP_CONCAT(DISTINCT p.party) as parties
        FROM claims c
        JOIN tracked_politicians p ON c.opponent_id = p.id
        WHERE {_BRIEF_DAY_CLAIM_SQL} AND c.claim_type = 'position'
          AND p.relationship_type NOT IN ('journalist','influencer','neutral','inactive','organization')
        GROUP BY c.topic HAVING party_cnt >= 3
        ORDER BY party_cnt DESC LIMIT 3
    """, _brief_day_params(date)).fetchall()

    lines = [f"# Dienas analīze — {date}\n"]
    lines.append("## Galvenais\n")
    # Iekšējs aģenta orientācijas signāls — HTML komentārs paliek DOM-ā, bet
    # browseris to nerāda. Publiskais skaitļu footer tiek renderēts template-
    # līmenī no src/render/blog.py:_fetch_blog_posts() (F3f.4).
    plural_pos = "pozīcija" if position_count == 1 else "pozīcijas"
    plural_pret = "pretruna" if contradiction_count == 1 else "pretrunas"
    # Pozīciju skaits = dienas-loga politiķu pozīcijas (=emitētās ###-tabulas).
    # Ja dienā ir arī organizāciju pozīcijas, uzrādām sadalījumu skaidri
    # ('N pozīcijas (M politiķu + K org)'), lai nav klusa neatbilstība starp
    # STATS skaitli un emitētajām politiķu tabulām (Fix 2). doc_count mēra
    # date(scraped_at)=diena visiem dokumentiem; web/X sadalījums pēc platform.
    pos_stat = f"{position_count} {plural_pos}"
    if audience_count:
        pos_stat = (
            f"{position_count} pozīcijas "
            f"({politician_count} politiķu + {audience_count} auditorijas)"
        )
    doc_stat = (
        f"{doc_count} dokumenti ({web_count} web + {x_count} Twitter/X"
        f" + {vestnesis_count} vestnesis"
    )
    if other_count:
        doc_stat += f" + {other_count} citi"
    doc_stat += ")"
    lines.append(
        f"<!-- DIENAS STATS (iekšēja piezīme aģentam; nav renderēta publikai): "
        f"{doc_stat} · "
        f"{pos_stat} · "
        f"{contradiction_count} {plural_pret} -->"
    )

    # Narrative hints — @brief-writer uses these to write the Galvenais paragraph
    if top_tension_topics or cross_party_clashes:
        lines.append("\n<!-- NARATĪVA MATERIĀLS (izmanto Galvenais paragrāfam, pēc tam izdzēs šo bloku):")
        if top_tension_topics:
            lines.append("Spriedžu tēmas:")
            for t in top_tension_topics:
                lines.append(f"  - {t['topic']} ({t['cnt']} spriedzes): {t['pairs']}")
        if cross_party_clashes:
            lines.append("Starppartiju tēmas (3+ partijas iesaistītas):")
            for c in cross_party_clashes:
                lines.append(f"  - {c['topic']}: {c['parties']}")
        lines.append("-->")

    if active:
        lines.append("\n## Aktīvākie politiķi\n")
        lines.append("| Politiķis | Partija | Pozīcijas | Galvenās tēmas |")
        lines.append("|-----------|---------|-----------|----------------|")
        for a in active:
            topics = (a["topics"] or "").replace(",", ", ")
            lines.append(f"| {a['name']} | {a['party'] or ''} | {a['cnt']} | {topics} |")

    # Fetch context notes for the date
    context_notes = db.execute("""
        SELECT topic, content FROM context_notes
        WHERE note_type = 'context' AND date(created_at) = ?
        ORDER BY created_at DESC
    """, (date,)).fetchall()

    # Skip raw JSON marker rows (e.g. synthesis_featured_image hints stored as
    # {"kind": "...", ...}) — they are scaffolding for a synthesis-card render
    # pipeline that doesn't yet exist, so dumping the JSON into a context-box
    # leaks structured data into the public HTML.
    context_notes = [
        cn for cn in context_notes
        if not (cn["content"] or "").lstrip().startswith("{")
    ]

    if by_topic:
        lines.append("\n## Galvenās tēmas\n")
        for t in full_topics:
            pos_word = "pozīcija" if t["cnt"] == 1 else "pozīcijas"
            lines.append(f"### {t['topic']} ({t['cnt']} {pos_word})\n")

            # Embed matching context note if available
            for cn in context_notes:
                if cn["topic"] and cn["topic"].lower() in t["topic"].lower() or \
                   t["topic"].lower() in (cn["topic"] or "").lower():
                    lines.append('<div class="context-box" markdown="1">')
                    lines.append('<div class="context-label">Konteksts</div>\n')
                    lines.append(f'{cn["content"]}')
                    lines.append('</div>\n')
                    break

            # Claims with source URLs — positions only, excluding
            # audience accounts. Vote rows carry procedural stances
            # that make no sense in a rhetorical brief.
            samples = db.execute(f"""
                SELECT p.name, p.party, c.stance, c.source_url FROM claims c
                JOIN tracked_politicians p ON c.opponent_id = p.id
                WHERE {_BRIEF_DAY_CLAIM_SQL} AND c.topic = ?
                  AND c.claim_type = 'position'
                  AND p.relationship_type != 'inactive'
                ORDER BY c.id
            """, (*_brief_day_params(date), t["topic"])).fetchall()

            if samples:
                lines.append("| Politiķis | Partija | Pozīcija | Avots |")
                lines.append("|-----------|---------|----------|-------|")
                for s in samples:
                    link = _source_link(s["source_url"])
                    stance_full = (s["stance"] or "").strip()
                    lines.append(f"| {s['name']} | {s['party'] or ''} | {stance_full} | {link} |")
                lines.append("")

                # Per-topic synthesis hint: group stances by coalition side
                # so @brief-writer can write "JV un ZZS saskata problēmu,
                # bet piedāvā atšķirīgus risinājumus" style sentences.
                koa_stances = [s for s in samples if coalition_map.get(s["party"]) == "coalition"]
                opo_stances = [s for s in samples if coalition_map.get(s["party"]) == "opposition"]
                if koa_stances or opo_stances:
                    hint_parts = []
                    if koa_stances:
                        names = ", ".join(sorted({f"{s['name']} ({s['party']})" for s in koa_stances}))
                        hint_parts.append(f"Koalīcija: {names}")
                    if opo_stances:
                        names = ", ".join(sorted({f"{s['name']} ({s['party']})" for s in opo_stances}))
                        hint_parts.append(f"Opozīcija: {names}")
                    lines.append(f"<!-- SINTĒZE: {' | '.join(hint_parts)} -->")

        # Pārējās tēmas — one compact table for every topic that did not earn a
        # full ### section (T7 fix). Rows use the SAME filters as the per-topic
        # samples query (positions only, audience excluded, _BRIEF_DAY_CLAIM_SQL),
        # ordered by each topic's max_salience DESC, then topic name, then c.id.
        if rest_topics:
            rest_names = [t["topic"] for t in rest_topics]
            placeholders = ",".join("?" for _ in rest_names)
            # Preserve the interest-ranked, max_salience-tie order from Python by
            # sorting in SQL on the same keys the fetched rest_topics carry.
            rest_rows = db.execute(f"""
                SELECT p.name, p.party, c.topic, c.stance, c.source_url
                FROM claims c
                JOIN tracked_politicians p ON c.opponent_id = p.id
                WHERE {_BRIEF_DAY_CLAIM_SQL} AND c.claim_type = 'position'
                  AND p.relationship_type != 'inactive'
                  AND c.topic IN ({placeholders})
                ORDER BY c.topic, c.id
            """, (*_brief_day_params(date), *rest_names)).fetchall()

            # Order topics by max_salience DESC then topic name (mirrors
            # rest_topics); rows within a topic stay in c.id order. Python's sort
            # is stable, so sorting the already (topic, c.id)-ordered rows by the
            # per-topic rank key alone preserves the c.id order inside each topic.
            topic_rank = {
                t["topic"]: (-(t["max_salience"] or 0), t["topic"])
                for t in rest_topics
            }
            rest_rows = sorted(rest_rows, key=lambda r: topic_rank[r["topic"]])

            n_rows = len(rest_rows)
            m_topics = len({r["topic"] for r in rest_rows})
            pos_word = "pozīcija" if n_rows == 1 else "pozīcijas"
            tema_word = "tēmā" if m_topics == 1 else "tēmās"
            lines.append(
                f"\n### Pārējās tēmas ({n_rows} {pos_word} {m_topics} {tema_word})\n"
            )
            lines.append("| Politiķis | Partija | Tēma | Pozīcija | Avots |")
            lines.append("|-----------|---------|------|----------|-------|")
            for r in rest_rows:
                link = _source_link(r["source_url"])
                stance_full = (r["stance"] or "").strip()
                lines.append(
                    f"| {r['name']} | {r['party'] or ''} | {r['topic']} | "
                    f"{stance_full} | {link} |"
                )
            lines.append("")

    # Add remaining context notes that didn't match any topic. matched_topics =
    # topics with a FULL ### section only (T7): a Pārējās-table topic's context
    # note flows through this unmatched path unchanged.
    matched_topics = {t["topic"] for t in full_topics} if by_topic else set()
    unmatched_context = [cn for cn in context_notes
                         if not any(cn["topic"] and (cn["topic"].lower() in mt.lower() or mt.lower() in cn["topic"].lower())
                                    for mt in matched_topics)]
    if unmatched_context:
        lines.append("\n## Papildu konteksts\n")
        for cn in unmatched_context:
            lines.append('<div class="context-box" markdown="1">')
            lines.append(f'<div class="context-label">{cn["topic"] or "Konteksts"}</div>\n')
            lines.append(f'{cn["content"]}')
            lines.append('</div>\n')

    # Coalition vs opposition split — renderē kā kompaktu tabulu.
    # Pārveidots 2026-04-19 no 3 paragrāfiem uz 5-kolonnu tabulu, lai padarītu
    # skenējamu. Aģents ZEM tabulas pievieno 1-2 teikumu sintēzi.
    all_day_rows = db.execute(f"""
        SELECT p.name, p.party, c.topic, c.stance, p.relationship_type
        FROM claims c
        JOIN tracked_politicians p ON c.opponent_id = p.id
        WHERE {_BRIEF_DAY_CLAIM_SQL}
          AND c.claim_type = 'position'
        ORDER BY c.id
    """, _brief_day_params(date)).fetchall()
    _AUDIENCE_TYPES = ("journalist", "influencer", "neutral", "inactive", "organization")

    def _is_political(row):
        """Bloc classification applies only to elected/tracked politicians —
        not to audience accounts (journalists, influencers, neutral analysts,
        inactive sentinels). Excluding them keeps the coalition/opposition
        counts honest and makes the Neitrāli row disjoint from the others."""
        return row["relationship_type"] not in _AUDIENCE_TYPES

    koa_rows = [r for r in all_day_rows if _is_political(r)
                and coalition_map.get(r["party"]) == "coalition"]
    opo_rows = [r for r in all_day_rows if _is_political(r)
                and coalition_map.get(r["party"]) == "opposition"]
    out_rows = [r for r in all_day_rows if _is_political(r)
                and coalition_map.get(r["party"]) == "not_in_saeima"]
    # Bezpartejiskie: politiskie (tracked, ne audience) politiķi, kuru partija
    # neatbilst nevienam Saeimas blokam — party IS NULL (coalition_map.get(None)
    # → None) vai coalition_status='other'. Bez šī bloka tādi politiķi (piem.
    # Valsts prezidents) izkrīt cauri visiem blokiem UN Neitrāli rindai, un
    # "Pozīcijas" kopskaits klusi nesakrīt.
    bezp_rows = [r for r in all_day_rows if _is_political(r)
                 and coalition_map.get(r["party"]) not in ("coalition", "opposition", "not_in_saeima")]
    neutral_rows = [r for r in all_day_rows
                    if r["relationship_type"] in ("journalist", "influencer", "neutral", "organization")]

    if koa_rows or opo_rows or out_rows or bezp_rows or neutral_rows:

        lines.append("\n## Koalīcija vs Opozīcija\n")
        lines.append("| Bloks | Pozīcijas | Partijas | Galvenie runātāji | Dominējošās tēmas |")
        lines.append("|-------|-----------|----------|-------------------|-------------------|")
        for label, rows in [
            ("Koalīcija", koa_rows),
            ("Opozīcija", opo_rows),
            # "Bez Saeimas frakcijas" (līdz 2026-07-22 "Ārpus Saeimas"): bloks
            # grupē pēc PARTIJAS statusa (not_in_saeima), tāpēc te nonāk arī
            # deputāti, kuru partijai nav frakcijas (piem. Burovs/GKR ievēlēts,
            # bet GKR frakcijas Saeimā nav) — vecais nosaukums lasītājam meloja.
            ("Bez Saeimas frakcijas", out_rows),
            ("Bezpartejiskie", bezp_rows),
            ("Neitrāli", neutral_rows),
        ]:
            summary = _bloc_summary(rows, show_parties=(label != "Neitrāli"))
            if summary is None:
                continue
            cnt, parties, people, topics = summary
            lines.append(f"| {label} | {cnt} | {parties} | {people} | {topics} |")
        lines.append("")

    # Tensions (spriedzes) — same-day cross-party attacks/support
    tension_rows = db.execute("""
        SELECT t.tension_type, t.topic, t.description, t.source_url,
               sp.name as s_name, sp.party as s_party,
               tp.name as t_name, tp.party as t_party
        FROM political_tensions t
        JOIN tracked_politicians sp ON t.source_pid = sp.id
        JOIN tracked_politicians tp ON t.target_pid = tp.id
        -- 'localtime': political_tensions.created_at is UTC (schema.sql).
        WHERE date(t.created_at, 'localtime') = ?
        ORDER BY t.id
    """, (date,)).fetchall()
    if tension_rows:
        lines.append("\n## Spriedzes\n")
        lines.append("| Tips | Avots | Mērķis | Tēma | Apraksts | Saite |")
        lines.append("|------|-------|--------|------|----------|-------|")
        for t in tension_rows:
            url = t["source_url"] or ""
            if url:
                domain = url.split("//")[-1].split("/")[0].replace("www.", "")[:20]
                link = f"[{domain}]({url})"
            else:
                link = "—"
            desc = (t["description"] or "").strip()
            # Party suffix only when a party exists — bezpartejiskie render as
            # bare name, never 'Vārds ()' (Fix 1, 2026-07-16).
            src = _name_party(t["s_name"], t["s_party"])
            tgt = _name_party(t["t_name"], t["t_party"])
            lines.append(f"| {t['tension_type']} | {src} | {tgt} | {t['topic']} | {desc} | {link} |")
        lines.append("")

    # Pretrunas — tīrs formāts bez raw DB ID un severity enum noplūdes.
    # Aģentam AIZLIEGTS ievelk šīs rindas Spriedžu tabulā vai rakstīt
    # "Pretruna #NN" redzamā tekstā (skat .claude/agents/brief-writer.md).
    contra_rows = db.execute("""
        SELECT c.id, c.topic, c.severity, c.summary,
               c.claim_old_id, c.claim_new_id,
               p.name, p.party,
               c_old.source_url AS old_url, c_old.stated_at AS old_date,
               c_new.source_url AS new_url, c_new.stated_at AS new_date
        FROM contradictions c
        JOIN tracked_politicians p ON c.opponent_id = p.id
        LEFT JOIN claims c_old ON c.claim_old_id = c_old.id
        LEFT JOIN claims c_new ON c.claim_new_id = c_new.id
        WHERE date(c.detected_at) = ?
          AND COALESCE(c.confirmed, 1) = 1
        ORDER BY c.id
    """, (date,)).fetchall()

    if contra_rows:
        lines.append("\n## Pretrunas\n")
        lines.append("| Politiķis | Partija | Tēma | Veids | Apraksts | Avoti |")
        lines.append("|-----------|---------|------|-------|----------|-------|")
        for r in contra_rows:
            severity_lv = _SEVERITY_LV.get(r["severity"] or "", "pretruna")
            # Apraksts — pirmais paragrāfs pilnā garumā (paragrāfa izvēle ir
            # atlase, ne griešana; simbolu limita nav — sk. no-truncation
            # noteikumu faila sākumā).
            summary = (r["summary"] or "").split("\n\n", 1)[0].strip()

            old_label = _date_label(r["old_date"])
            new_label = _date_label(r["new_date"])
            old_link = f"[{old_label}]({r['old_url']})" if r["old_url"] and old_label else ""
            new_link = f"[{new_label}]({r['new_url']})" if r["new_url"] and new_label else ""
            if old_link and new_link:
                sources = f"{old_link} / {new_link}"
            elif old_link:
                sources = old_link
            elif new_link:
                sources = new_link
            else:
                sources = "—"
            lines.append(f"| {r['name']} | {r['party'] or ''} | {r['topic']} | "
                         f"{severity_lv} | {summary} | {sources} |")
        lines.append("")

    db.close()
    return "\n".join(lines)


def generate_weekly_brief(db_path: str = None, week_start: str = None,
                          chart_dir: str = "output/images/briefs") -> str:
    """Generate a neutral weekly brief in markdown covering 7 days from week_start.

    Writes the deterministic movers chart SVG into `chart_dir` and references it
    from the markdown. The chart is data (never enters brief_images)."""
    db_path = db_path or str(_DB_PATH)
    if week_start is None:
        today = now_lv_dt()
        week_start = (today - timedelta(days=today.weekday())).strftime("%Y-%m-%d")
    week_end_dt = datetime.strptime(week_start, "%Y-%m-%d") + timedelta(days=6)
    week_end = week_end_dt.strftime("%Y-%m-%d")

    db = get_db(db_path)

    position_count = db.execute(
        "SELECT COUNT(*) FROM claims WHERE date(stated_at) BETWEEN ? AND ? "
        "AND claim_type = 'position'",
        (week_start, week_end),
    ).fetchone()[0]
    # Count DISTINCT Saeima vote events that occurred this week (saeima_votes by
    # vote_date) — NOT per-deputy saeima_vote claims. The latter has ~one row per
    # deputy per vote (~100×), so a normal 70-vote week reported "votes=5692",
    # an absurd figure that also happened to sit near the all-time vote total.
    # saeima_votes is created by init_saeima_tables (not init_db), so guard for
    # DBs that lack it (brief unit-test fixtures) → 0.
    if db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='saeima_votes'"
    ).fetchone():
        vote_count = db.execute(
            "SELECT COUNT(*) FROM saeima_votes WHERE date(vote_date) BETWEEN ? AND ?",
            (week_start, week_end),
        ).fetchone()[0]
    else:
        vote_count = 0
    contradiction_count = db.execute(
        "SELECT COUNT(*) FROM contradictions WHERE date(detected_at) BETWEEN ? AND ? "
        "AND COALESCE(confirmed, 1) = 1",
        (week_start, week_end),
    ).fetchone()[0]

    by_topic = db.execute("""
        SELECT topic, COUNT(*) as cnt FROM claims
        WHERE date(stated_at) BETWEEN ? AND ?
          AND claim_type = 'position'
        GROUP BY topic ORDER BY cnt DESC LIMIT 7
    """, (week_start, week_end)).fetchall()

    top_topic = by_topic[0]["topic"] if by_topic else "—"
    top_party_row = db.execute("""
        SELECT p.party, COUNT(*) AS cnt FROM claims c
        JOIN tracked_politicians p ON c.opponent_id = p.id
        WHERE date(c.stated_at) BETWEEN ? AND ? AND c.claim_type='position'
          AND p.relationship_type != 'inactive' AND p.party IS NOT NULL
        GROUP BY p.party ORDER BY cnt DESC LIMIT 1
    """, (week_start, week_end)).fetchone()
    top_party = top_party_row["party"] if top_party_row else "—"

    lines = [f"# Nedēļas analīze — {week_start} līdz {week_end}\n"]

    # Prose section — agent fills. Placeholder keeps validation + structure stable.
    lines.append("## Nedēļas stāsts\n")
    lines.append("<!-- AGENT: 2-3 īsas prozas rindkopas par nedēļas arku. "
                 "Aizvāc šo komentāru. -->\n")

    # Deterministic stat strip (render-time parsed into cards).
    lines.append("## Nedēļa skaitļos\n")
    lines.append(
        f"<!-- WEEKLY_STATS: positions={position_count} votes={vote_count} "
        f"contradictions={contradiction_count} top_topic={top_topic} "
        f"top_party={top_party} -->\n"
    )

    # Movers leaderboard + deterministic SVG chart (data, not brief_images).
    lines.append("## Kas kustējās\n")
    movers = _weekly_movers(db_path, week_start, week_end)
    from src.coalition import get_coalition_map
    cmap = get_coalition_map(db)
    # Coalition vs opposition strip — computed over ALL position claims in the
    # week, not just the top-6 movers. The movers leaderboard is a raw-count
    # top-6 and is structurally coalition-heavy (the governing side speaks
    # most), so summing the bloc bar from it left the opposition segment empty
    # even in weeks where the opposition was active. Mirror the daily bloc
    # logic: full-week counts grouped by party, audience/org excluded.
    coalition = {"coalition": 0, "opposition": 0}
    bloc_rows = db.execute(
        """SELECT p.party, COUNT(*) AS cnt
           FROM claims c JOIN tracked_politicians p ON c.opponent_id = p.id
           WHERE date(c.stated_at) BETWEEN ? AND ? AND c.claim_type = 'position'
             AND p.relationship_type NOT IN
                 ('journalist','influencer','neutral','inactive','organization')
           GROUP BY p.party""",
        (week_start, week_end),
    ).fetchall()
    for r in bloc_rows:
        status = cmap.get(r["party"], "other")
        if status in coalition:
            coalition[status] += r["cnt"]
    from src.graphics.weekly_chart import make_movers_svg
    svg = make_movers_svg(movers, coalition)
    out_dir = Path(chart_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    fname = f"{week_start}-nedelas-movers.svg"
    (out_dir / fname).write_bytes(svg)
    # Path is relative to the rendered post at /blog/<slug>.html (mirrors the
    # hero template's ../images/briefs/ prefix).
    lines.append(f"![Kas kustējās](../images/briefs/{fname})\n")
    # Reader-facing legend for the count + delta (the chart/list show raw
    # numbers; without this the "+6 / -3 / jauns" annotations are unexplained).
    lines.append(
        "*Skaitlis = pozīciju skaits nedēļā · +/− = izmaiņa pret iepriekšējo "
        "nedēļu · «jauns» = iepriekšējā nedēļā nebija.*\n"
    )
    for m in movers:
        d = m["delta"]
        arrow = "jauns" if d == "jauns" else (f"↑{d}" if isinstance(d, int) and d > 0
                 else (f"↓{abs(d)}" if isinstance(d, int) and d < 0 else "—"))
        lines.append(f"- **{m['name']}** ({m['party'] or '—'}) — {m['count']} ({arrow})")

    # Theme scaffold — top topics with source-linked candidate positions.
    if by_topic:
        lines.append("\n## Nedēļas galvenās tēmas\n")
        for t in by_topic[:4]:
            lines.append(f"### {t['topic']} — {t['cnt']} pozīcijas\n")
            cands = db.execute("""
                SELECT p.name, p.party, c.stance, c.source_url
                FROM claims c JOIN tracked_politicians p ON c.opponent_id = p.id
                WHERE date(c.stated_at) BETWEEN ? AND ? AND c.claim_type='position'
                  AND c.topic = ? AND p.relationship_type != 'inactive'
                ORDER BY c.salience DESC LIMIT 3
            """, (week_start, week_end, t["topic"])).fetchall()
            for c in cands:
                url = c["source_url"] or ""
                lines.append(f"- {c['name']} ({c['party'] or '—'}): {c['stance']} {url}")
            lines.append("")

    # Koalīcija vs Opozīcija — same 5-bloc table the daily emits, computed over
    # the full week. Added 2026-06-22: the weekly previously had no bloc section
    # at all, so the opposition was invisible in the weekly synthesis even when
    # active. Audience accounts (journalists/influencers/neutral/org) are
    # excluded from the political blocs and counted under Neitrāli, mirroring
    # generate_daily_brief. The agent adds a 1–2 sentence synthesis below.
    week_bloc_rows = db.execute(
        """SELECT p.name, p.party, c.topic, p.relationship_type
           FROM claims c JOIN tracked_politicians p ON c.opponent_id = p.id
           WHERE date(c.stated_at) BETWEEN ? AND ? AND c.claim_type = 'position'
           ORDER BY c.id""",
        (week_start, week_end),
    ).fetchall()
    _AUDIENCE_TYPES = ("journalist", "influencer", "neutral", "inactive", "organization")

    def _is_political(row):
        return row["relationship_type"] not in _AUDIENCE_TYPES

    koa_rows = [r for r in week_bloc_rows if _is_political(r) and cmap.get(r["party"]) == "coalition"]
    opo_rows = [r for r in week_bloc_rows if _is_political(r) and cmap.get(r["party"]) == "opposition"]
    out_rows = [r for r in week_bloc_rows if _is_political(r) and cmap.get(r["party"]) == "not_in_saeima"]
    bezp_rows = [r for r in week_bloc_rows if _is_political(r)
                 and cmap.get(r["party"]) not in ("coalition", "opposition", "not_in_saeima")]
    neutral_rows = [r for r in week_bloc_rows
                    if r["relationship_type"] in ("journalist", "influencer", "neutral", "organization")]

    if koa_rows or opo_rows or out_rows or bezp_rows or neutral_rows:
        lines.append("\n## Koalīcija vs Opozīcija\n")
        lines.append("| Bloks | Pozīcijas | Partijas | Galvenie runātāji | Dominējošās tēmas |")
        lines.append("|-------|-----------|----------|-------------------|-------------------|")
        for label, rows in [
            ("Koalīcija", koa_rows),
            ("Opozīcija", opo_rows),
            # Sk. dienas ģeneratora piezīmi: bloks grupē pēc partijas statusa,
            # ne pēc deputāta mandāta — nosaukums saskaņots 2026-07-22.
            ("Bez Saeimas frakcijas", out_rows),
            ("Bezpartejiskie", bezp_rows),
            ("Neitrāli", neutral_rows),
        ]:
            summary = _bloc_summary(rows, show_parties=(label != "Neitrāli"))
            if summary is None:
                continue
            cnt, parties, people, topics = summary
            lines.append(f"| {label} | {cnt} | {parties} | {people} | {topics} |")
        lines.append("")

    db.close()
    return "\n".join(lines)


def _weekly_movers(db_path: str, week_start: str, week_end: str, limit: int = 6) -> list[dict]:
    """Top `limit` politicians by position-claims this week, with delta vs the
    prior 7-day window. delta is an int, or the string "jauns" when the prior
    window has zero baseline. Absolute counts only — never percentages."""
    db = get_db(db_path)
    prev_start = (datetime.strptime(week_start, "%Y-%m-%d") - timedelta(days=7)).strftime("%Y-%m-%d")
    prev_end = (datetime.strptime(week_start, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")

    def counts(start, end):
        rows = db.execute("""
            SELECT p.id, p.name, p.party, COUNT(*) AS cnt
            FROM claims c JOIN tracked_politicians p ON c.opponent_id = p.id
            WHERE date(c.stated_at) BETWEEN ? AND ? AND c.claim_type = 'position'
              AND p.relationship_type != 'inactive'
            GROUP BY p.id
        """, (start, end)).fetchall()
        return {r["id"]: r for r in rows}

    cur = counts(week_start, week_end)
    prev = counts(prev_start, prev_end)
    movers = []
    for pid, r in cur.items():
        base = prev.get(pid)
        delta = (r["cnt"] - base["cnt"]) if base else "jauns"
        movers.append({"id": pid, "name": r["name"], "party": r["party"],
                       "count": r["cnt"], "delta": delta})
    movers.sort(key=lambda m: m["count"], reverse=True)
    db.close()
    return movers[:limit]


_PARTY_SHORT = {
    "Jaunā Vienotība": "JV",
    "Nacionālā apvienība": "NA",
    "Progresīvie": "PRO",
    "Apvienotais saraksts": "AS",
    "Zaļo un Zemnieku savienība": "ZZS",
    "MMN": "MMN",
    "Latvija Pirmajā Vietā": "LPV",
    "Stabilitātei!": "S!",
    "Latvijas Krievu savienība": "LKS",
    "Saskaņa": "SAS",
}

_SEVERITY_LV = {
    "minor_shift": "neliela novirze",
    "direct_contradiction": "tieša pretruna",
    "reversal": "reversija",
}


def _date_label(date_str: str | None) -> str:
    """Format ISO date/timestamp string to DD.MM for display in tables.
    Accepts 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS' (slices first 10 chars).
    Returns empty string if input is falsy or not recognizable."""
    if not date_str:
        return ""
    try:
        parts = date_str[:10].split("-")
        return f"{parts[2]}.{parts[1]}"
    except (IndexError, ValueError):
        return ""


def _short_party(party: str | None) -> str:
    if not party:
        return ""
    return _PARTY_SHORT.get(party, party)


def _name_party(name: str, party: str | None) -> str:
    """'Vārds (Partija)' when a party exists, else bare 'Vārds'. Never emits
    empty parens '()' for bezpartejiskie (party NULL/'') — Fix 1, 2026-07-16."""
    return f"{name} ({party})" if (party or "").strip() else f"{name}"


def _bloc_summary(rows, show_parties: bool = True):
    """Atgriež (cnt, partijas_str, runātāji_str, tēmas_str) vienam blokam
    Koalīcija vs Opozīcija tabulai. Atgriež None, ja rindu nav.

    show_parties=False (Neitrāli/audience rindai): Partijas aile vienmēr "—".
    Audience bloku definē relationship_type, ne partija, tāpēc residuāla
    partija nedrīkst noplūst Partijas ailē un maldināt — piem. Kārlis Seržants
    ir relationship_type='journalist' (matcher-guard, uzvārds=sugasvārds), bet
    party='Apvienotais saraksts', un viņa "AS" tags agrāk parādījās Neitrāli
    rindā, kuras top runātāji ir bezpartijas. Sk. project_serzants_journalist_guard."""
    if not rows:
        return None
    by_person: dict[tuple[str, str], int] = {}
    by_party: dict[str, int] = {}
    by_topic: dict[str, int] = {}
    org_names: set[str] = set()
    for r in rows:
        key = (r["name"], r["party"] or "")
        by_person[key] = by_person.get(key, 0) + 1
        if "relationship_type" in r.keys() and r["relationship_type"] == "organization":
            org_names.add(r["name"])
        if r["party"]:
            by_party[r["party"]] = by_party.get(r["party"], 0) + 1
        if r["topic"]:
            by_topic[r["topic"]] = by_topic.get(r["topic"], 0) + 1

    top_people = sorted(by_person.items(), key=lambda x: (-x[1], x[0][0]))[:3]
    # Personām rāda uzvārdu; institūcijai pēdējais vārds ir sugasvārds
    # ("Valsts kontrole" → "kontrole"), tāpēc organizācijām paliek pilnais
    # nosaukums.
    #
    # Uzvārds ir identifikators tikai tad, ja tas blokā ir unikāls. 2026-08-07
    # dienas pārskatā "Bez Saeimas frakcijas" rindā stāvēja "Hermanis (1),
    # Hermanis (1)" — divi DAŽĀDI MMN cilvēki (Alvis id=29, Jānis id=13), un
    # arī partijas tags tos nešķīra. Kolīzijas gadījumā abiem rāda pilno vārdu.
    colliding = set()
    seen_surnames: dict[str, str] = {}
    for name, _party in by_person:
        if name in org_names:
            continue
        surname = name.split()[-1]
        other = seen_surnames.setdefault(surname, name)
        if other != name:
            colliding.add(surname)
    people_str = ", ".join(
        f"{name if (name in org_names or name.split()[-1] in colliding) else name.split()[-1]} ({cnt})"
        for (name, _), cnt in top_people
    ) or "—"

    parties_sorted = sorted(by_party.items(), key=lambda x: -x[1])
    parties_str = (", ".join(_short_party(p) for p, _ in parties_sorted) or "—") if show_parties else "—"

    topics_sorted = sorted(by_topic.items(), key=lambda x: -x[1])[:3]
    topics_str = ", ".join(t for t, _ in topics_sorted) or "—"

    return (len(rows), parties_str, people_str, topics_str)


_VB_BLOCK_RE = re.compile(
    r"##\s*Viz[uū]ālais\s+brief\s*\n+(.*?)(?=\n##\s|\Z)",
    flags=re.IGNORECASE | re.DOTALL,
)
_VB_FIELD_RE = re.compile(r"^\s*-\s*\*\*([^*]+):\*\*\s*(.*?)\s*$")


_HTML_COMMENT_RE = re.compile(r"<!--.*?-->\n?", flags=re.DOTALL)


def strip_visual_brief_block(content: str) -> str:
    """Remove internal scaffolding from a brief's markdown before public render.

    Two things go: the `## Vizuālais brief` block (consumed by
    parse_visual_brief() at store time and by @graphics-designer) and HTML
    comments (e.g. the `<!-- DIENAS STATS -->` line — invisible in the
    browser but readable in the published page source, 2026-08-12 decision).
    Returns the content with both removed (and surrounding blank lines
    collapsed).
    """
    cleaned = _VB_BLOCK_RE.sub("", content)
    cleaned = _HTML_COMMENT_RE.sub("", cleaned)
    return re.sub(r"\n{3,}", "\n\n", cleaned).rstrip() + "\n"


def parse_visual_brief(content: str) -> dict | None:
    """Extract the `## Vizuālais brief` block from a brief's markdown content.

    Returns a dict with keys {topic, headline, stat, metaphor_hint} or None if
    the block is missing or malformed. The `stat` field is set to None when
    its value does not appear as a substring of the brief body — this prevents
    hallucinated figures from reaching the image prompt.

    If multiple `## Vizuālais brief` blocks exist (e.g. template examples inside
    code fences), iteration happens in reverse and the first block parsing to a
    valid, non-placeholder result wins. Blocks with `<topic>`-style placeholders
    or missing required fields are skipped.
    """
    matches = list(_VB_BLOCK_RE.finditer(content))
    if not matches:
        return None

    # Iterate in reverse: prefer later (real) blocks over earlier (example)
    # ones, but skip placeholder stubs like "<topic>" and empty-field blocks.
    for m in reversed(matches):
        block = m.group(1)
        fields: dict[str, str] = {}
        for line in block.splitlines():
            fm = _VB_FIELD_RE.match(line)
            if fm:
                fields[fm.group(1).strip()] = fm.group(2).strip()

        topic = fields.get("Tēma", "").strip()
        headline = fields.get("Galvenā tēze", "").strip()
        stat_raw = fields.get("Skaitlis", "").strip()
        metaphor_hint = fields.get("Metaforas hint", "").strip()

        if not topic or not headline:
            continue  # stub / malformed — try earlier block
        if topic.startswith("<") or headline.startswith("<"):
            continue  # placeholder template like "<topic>" — not a real block

        if stat_raw in ("", "-", "–", "—", "nav"):
            stat: str | None = None
        else:
            body = content[: m.start()] + content[m.end():]
            stat = stat_raw if stat_raw in body else None

        return {
            "topic": topic,
            "headline": headline,
            "stat": stat,
            "metaphor_hint": metaphor_hint,
        }

    return None
