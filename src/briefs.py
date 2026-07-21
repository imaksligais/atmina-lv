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
_BRIEF_DAY_CLAIM_SQL = (
    "(date(c.stated_at) = ? OR "
    "(date(c.created_at) = ? AND date(c.stated_at) >= date(?, '-7 days') "
    "AND NOT EXISTS ("
    "SELECT 1 FROM context_notes _nb "
    "WHERE _nb.note_type = 'daily_brief' "
    "AND _nb.topic = 'dienas analīze ' || date(c.stated_at) "
    "AND _nb.created_at > c.created_at)))"
)


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

    doc_count = db.execute(
        "SELECT COUNT(*) FROM documents WHERE date(scraped_at) = ?", (date,)
    ).fetchone()[0]
    web_count = db.execute(
        "SELECT COUNT(*) FROM documents WHERE date(scraped_at) = ? AND platform = 'web'", (date,)
    ).fetchone()[0]
    x_count = doc_count - web_count

    # Audience / context accounts (journalists, influencers, neutral
    # analysts, inactive sentinels) are excluded from all daily brief
    # sections — their commentary may be political, but the brief's
    # subject is elected/tracked politicians. Audience commentary
    # belongs in context_notes, not in the position leaderboard.

    # DIENAS STATS pozīciju skaits — TIEŠI tas pats dienas-loga predikāts
    # (_BRIEF_DAY_CLAIM_SQL, Fix 3-korekcija ieskaitot) + claim_type='position'
    # kā ###-emisijas vaicājumi, lai STATS skaitlis sakristu ar publicētajām
    # pozīcijām (Fix 2, 2026-07-16). politician_count izslēdz audience UN org —
    # tas ir tieši tas, ko emitē Aktīvākie/Galvenās tēmas/blocs. org_count ir
    # organizāciju pozīcijas (LDDK u.c.), kuras skeleta ###-tabulas NEemitē
    # (org ir audience-filtrā), tāpēc tās uzrādām atsevišķi ar marķējumu, nevis
    # klusi izslēdzam vai klusi ieskaitām — citādi STATS skaitlis nesakrīt.
    politician_count = db.execute(
        f"""SELECT COUNT(*) FROM claims c
           JOIN tracked_politicians p ON c.opponent_id = p.id
           WHERE {_BRIEF_DAY_CLAIM_SQL} AND c.claim_type = 'position'
             AND p.relationship_type NOT IN ('journalist','influencer','neutral','inactive','organization')""",
        _brief_day_params(date),
    ).fetchone()[0]
    org_count = db.execute(
        f"""SELECT COUNT(*) FROM claims c
           JOIN tracked_politicians p ON c.opponent_id = p.id
           WHERE {_BRIEF_DAY_CLAIM_SQL} AND c.claim_type = 'position'
             AND p.relationship_type = 'organization'""",
        _brief_day_params(date),
    ).fetchone()[0]
    position_count = politician_count
    contradiction_count = db.execute(
        "SELECT COUNT(*) FROM contradictions WHERE date(detected_at) = ? "
        "AND COALESCE(confirmed, 1) = 1",
        (date,),
    ).fetchone()[0]

    # Active politicians: position-only so the leaderboard reflects who
    # actually spoke rather than who happened to be present for a bulk
    # vote import.
    active = db.execute(f"""
        SELECT p.name, p.party, COUNT(*) as cnt,
            GROUP_CONCAT(DISTINCT c.topic) as topics
        FROM claims c
        JOIN tracked_politicians p ON c.opponent_id = p.id
        WHERE {_BRIEF_DAY_CLAIM_SQL}
          AND c.claim_type = 'position'
          AND p.relationship_type NOT IN ('journalist','influencer','neutral','inactive','organization')
        GROUP BY p.id ORDER BY cnt DESC LIMIT 7
    """, _brief_day_params(date)).fetchall()

    # Coalition map needed both for per-topic synthesis hints and for the
    # Koalīcija vs Opozīcija section further down.
    from src.coalition import get_coalition_map
    coalition_map = get_coalition_map(db)

    # Rank topics by "interestingness": position count + bonus for tensions
    # and contradictions — a topic with 3 positions and 2 tensions is more
    # newsworthy than one with 6 positions and 0 tensions.
    by_topic = db.execute(f"""
        SELECT c.topic, COUNT(*) as cnt,
            COALESCE(tens.t_cnt, 0) as tension_cnt,
            COALESCE(cont.c_cnt, 0) as contradiction_cnt,
            COUNT(*) + COALESCE(tens.t_cnt, 0) * 3 + COALESCE(cont.c_cnt, 0) * 2 as interest_score
        FROM claims c
        JOIN tracked_politicians p ON c.opponent_id = p.id
        LEFT JOIN (
            SELECT topic, COUNT(*) as t_cnt FROM political_tensions
            WHERE date(created_at) = ? GROUP BY topic
        ) tens ON tens.topic = c.topic
        LEFT JOIN (
            SELECT c2.topic, COUNT(*) as c_cnt FROM contradictions con
            JOIN claims c2 ON con.claim_old_id = c2.id OR con.claim_new_id = c2.id
            WHERE date(con.detected_at) = ?
              AND COALESCE(con.confirmed, 1) = 1
            GROUP BY c2.topic
        ) cont ON cont.topic = c.topic
        WHERE {_BRIEF_DAY_CLAIM_SQL} AND c.claim_type = 'position'
          AND p.relationship_type NOT IN ('journalist','influencer','neutral','inactive','organization')
        GROUP BY c.topic ORDER BY interest_score DESC LIMIT 5
    """, (date, date, *_brief_day_params(date))).fetchall()

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
        WHERE date(t.created_at) = ?
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
    if org_count:
        pos_stat = (
            f"{position_count + org_count} pozīcijas "
            f"({position_count} politiķu + {org_count} org)"
        )
    lines.append(
        f"<!-- DIENAS STATS (iekšēja piezīme aģentam; nav renderēta publikai): "
        f"{doc_count} dokumenti ({web_count} web + {x_count} Twitter/X) · "
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
        for t in by_topic:
            pos_word = "pozīcija" if t["cnt"] == 1 else "pozīcijas"
            lines.append(f"### {t['topic']} ({t['cnt']} {pos_word})\n")

            # Embed matching context note if available
            for cn in context_notes:
                if cn["topic"] and cn["topic"].lower() in t["topic"].lower() or \
                   t["topic"].lower() in (cn["topic"] or "").lower():
                    lines.append('<div class="context-box">')
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
                  AND p.relationship_type NOT IN ('journalist','influencer','neutral','inactive','organization')
                ORDER BY c.id
            """, (*_brief_day_params(date), t["topic"])).fetchall()

            if samples:
                lines.append("| Politiķis | Partija | Pozīcija | Avots |")
                lines.append("|-----------|---------|----------|-------|")
                for s in samples:
                    url = s["source_url"] or ""
                    domain = ""
                    if url:
                        # Extract domain for display
                        domain = url.split("//")[-1].split("/")[0].replace("www.", "")
                        if len(domain) > 20:
                            domain = domain[:20]
                        link = f"[{domain}]({url})"
                    else:
                        link = "—"
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

    # Add remaining context notes that didn't match any topic
    matched_topics = {t["topic"] for t in by_topic} if by_topic else set()
    unmatched_context = [cn for cn in context_notes
                         if not any(cn["topic"] and (cn["topic"].lower() in mt.lower() or mt.lower() in cn["topic"].lower())
                                    for mt in matched_topics)]
    if unmatched_context:
        lines.append("\n## Papildu konteksts\n")
        for cn in unmatched_context:
            lines.append('<div class="context-box">')
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
        WHERE date(t.created_at) = ?
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
    lines.append("## Nedēļā skaitļos\n")
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
    for r in rows:
        key = (r["name"], r["party"] or "")
        by_person[key] = by_person.get(key, 0) + 1
        if r["party"]:
            by_party[r["party"]] = by_party.get(r["party"], 0) + 1
        if r["topic"]:
            by_topic[r["topic"]] = by_topic.get(r["topic"], 0) + 1

    top_people = sorted(by_person.items(), key=lambda x: (-x[1], x[0][0]))[:3]
    people_str = ", ".join(
        f"{name.split()[-1]} ({cnt})" for (name, _), cnt in top_people
    ) or "—"

    parties_sorted = sorted(by_party.items(), key=lambda x: -x[1])
    parties_str = (", ".join(_short_party(p) for p, _ in parties_sorted) or "—") if show_parties else "—"

    topics_sorted = sorted(by_topic.items(), key=lambda x: -x[1])[:3]
    topics_str = ", ".join(t for t, _ in topics_sorted) or "—"

    return (len(rows), parties_str, people_str, topics_str)


def _domain_label(url: str) -> str:
    """Strip https:// + www. + path, return host only (e.g. 'x.com', 'lsm.lv')."""
    if not url:
        return "avots"
    host = re.sub(r"^https?://", "", url)
    host = host.split("/", 1)[0]
    if host.startswith("www."):
        host = host[4:]
    return host or "avots"


_MD2_ESCAPE_RE = re.compile(r"([_*\[\]()~`>#+\-=|{}.!\\])")


def _md2(text: str) -> str:
    """Escape literal text for Telegram MarkdownV2."""
    return _MD2_ESCAPE_RE.sub(r"\\\1", text)


def _md2_url(url: str) -> str:
    """Escape characters that need escaping inside MarkdownV2 link URL."""
    return url.replace("\\", "\\\\").replace(")", "\\)")


def generate_telegram_brief(
    db_path: str = None,
    date: str = None,
    public_url_base: str = "https://atmina.lv",
    max_politicians: int = 5,
    fmt: str = "html",
) -> str:
    """Generate a condensed Telegram-formatted daily brief.

    Designed for Telegram channel posting (under 4096 chars). Includes top N most
    active politicians with their headline position + source link, plus
    contradictions detected today, plus a link to the full brief.

    Args:
        fmt: 'html' (default — bot API parse_mode='HTML') or 'markdownv2'
            (parse_mode='MarkdownV2'; required for the telegram MCP reply tool's
            `format='markdownv2'` argument).
    """
    if fmt not in ("html", "markdownv2"):
        raise ValueError(f"fmt must be 'html' or 'markdownv2', got {fmt!r}")
    db_path = db_path or str(_DB_PATH)
    date = date or now_lv_dt().strftime("%Y-%m-%d")
    db = get_db(db_path)

    doc_count = db.execute(
        "SELECT COUNT(*) FROM documents WHERE date(scraped_at) = ?", (date,)
    ).fetchone()[0]
    position_count = db.execute(
        """SELECT COUNT(*) FROM claims c
           JOIN tracked_politicians p ON c.opponent_id = p.id
           WHERE date(c.stated_at) = ? AND c.claim_type = 'position'
             AND p.relationship_type NOT IN ('journalist','influencer','neutral','inactive','organization')""",
        (date,),
    ).fetchone()[0]
    contradiction_count = db.execute(
        "SELECT COUNT(*) FROM contradictions WHERE date(detected_at) = ? "
        "AND COALESCE(confirmed, 1) = 1",
        (date,),
    ).fetchone()[0]

    # Pull narrative summary from today's full daily brief (if @brief-writer
    # already wrote one) and split it into sentence-level bullets. Strips
    # markdown bold (**) and the leading stats bullet so we only keep the prose.
    summary_bullets: list[str] = []
    db_brief = db.execute(
        """SELECT content FROM context_notes
           WHERE note_type='daily_brief' AND topic = ?
           ORDER BY created_at DESC LIMIT 1""",
        (f"dienas pārskats {date}",),
    ).fetchone()
    if db_brief and db_brief["content"]:
        m = re.search(r"##\s*Galvenais\s*\n(.*?)(?=\n##\s)", db_brief["content"], re.DOTALL)
        if m:
            block = m.group(1).strip()
            # Drop HTML comments (DIENAS STATS etc.) — they're agent-only metadata
            block = re.sub(r"<!--.*?-->", "", block, flags=re.DOTALL).strip()
            paragraphs = [p.strip() for p in block.split("\n\n") if p.strip()]
            prose = [p for p in paragraphs if not p.startswith("-")]
            bullet_blocks = [p for p in paragraphs if p.startswith("-")]
            if prose:
                paragraph = re.sub(r"\*\*([^*]+)\*\*", r"\1", prose[0])
                sentences = re.split(r"(?<=[.!?])\s+(?=[A-ZĀČĒĢĪĶĻŅŠŪŽ])", paragraph)
                summary_bullets = [s.strip() for s in sentences if s.strip()]
            elif bullet_blocks:
                raw = bullet_blocks[0].splitlines()
                for line in raw:
                    s = line.lstrip("- ").strip()
                    s = re.sub(r"\*\*([^*]+)\*\*", r"\1", s)
                    if s:
                        summary_bullets.append(s)

    active = db.execute(
        """SELECT p.id, p.name, p.party, COUNT(*) AS cnt
           FROM claims c
           JOIN tracked_politicians p ON c.opponent_id = p.id
           WHERE date(c.stated_at) = ? AND c.claim_type = 'position'
             AND p.relationship_type NOT IN ('journalist','influencer','neutral','inactive','organization')
           GROUP BY p.id ORDER BY cnt DESC, p.name LIMIT ?""",
        (date, max_politicians),
    ).fetchall()

    if fmt == "html":
        def b(s: str) -> str: return f"<b>{s}</b>"
        def i(s: str) -> str: return f"<i>{s}</i>"
        def link(text: str, url: str) -> str: return f'<a href="{url}">{text}</a>'
        def t(s: str) -> str: return s
    else:  # markdownv2
        def b(s: str) -> str: return f"*{_md2(s)}*"
        def i(s: str) -> str: return f"_{_md2(s)}_"
        def link(text: str, url: str) -> str: return f"[{_md2(text)}]({_md2_url(url)})"
        def t(s: str) -> str: return _md2(s)

    lv_date = datetime.strptime(date, "%Y-%m-%d").strftime("%d.%m.%Y")
    full_url = f"{public_url_base}/blog/{date}.html"
    full_label = f"atmina.lv/blog/{date}"
    lines: list[str] = []
    lines.append(f"📰 {b(f'Atmina dienas pārskats — {lv_date}')}")
    lines.append(link(full_label, full_url))
    lines.append("")
    pretruna_word = "pretruna" if contradiction_count == 1 else "pretrunas"
    lines.append(t(
        f"{doc_count} dokumenti · {position_count} jaunas pozīcijas · "
        f"{contradiction_count} {pretruna_word}"
    ))

    if summary_bullets:
        lines.append("")
        lines.append(b("Kopsavilkums:"))
        for s in summary_bullets:
            lines.append(f"{t('•')} {t(s)}")

    if active:
        lines.append("")
        lines.append(b("Aktīvākie politiķi:"))
        for idx, p in enumerate(active, 1):
            top = db.execute(
                """SELECT topic, stance, source_url FROM claims
                   WHERE opponent_id = ? AND date(stated_at) = ? AND claim_type='position'
                   ORDER BY salience DESC, confidence DESC LIMIT 1""",
                (p["id"], date),
            ).fetchone()
            party_short = _short_party(p["party"])
            party_tag = f" {i(f'({party_short})')}" if party_short else ""
            cnt_label = "pozīcija" if p["cnt"] == 1 else "pozīcijas"
            lines.append("")
            cnt = p["cnt"]
            header_tail = f"— {cnt} {cnt_label}"
            lines.append(f"{t(f'{idx}.')} {b(p['name'])}{party_tag} {t(header_tail)}")
            if top and top["stance"]:
                stance = top["stance"].strip()
                if len(stance) > 280:
                    stance = stance[:277].rstrip() + "…"
                src = top["source_url"]
                topic_text = top["topic"] or ""
                bullet = f"• {topic_text}: {stance}"
                if src:
                    lines.append(f"   {t(bullet)} {t('·')} {link(_domain_label(src), src)}")
                else:
                    lines.append(f"   {t(bullet)}")

    # Šodien izsludināts — promulgated legal acts from vestnesis.lv with at
    # least one tracked-politician junction (drops municipal/technical noise).
    vestnesis_docs = db.execute(
        """SELECT d.id, d.title, d.source_url
           FROM documents d
           JOIN sources s ON d.source_id = s.id
           WHERE s.name = 'Latvijas Vēstnesis JL'
             AND date(COALESCE(d.published_at, d.scraped_at)) = ?
             AND EXISTS (
               SELECT 1 FROM document_politicians dp
               JOIN tracked_politicians p ON dp.politician_id = p.id
               WHERE dp.document_id = d.id
                 AND p.relationship_type NOT IN
                   ('journalist','influencer','neutral','inactive','organization')
             )
           ORDER BY d.published_at DESC, d.id DESC LIMIT 6""",
        (date,),
    ).fetchall()
    if vestnesis_docs:
        lines.append("")
        lines.append(b("Šodien izsludināts:"))
        for d in vestnesis_docs:
            signers_rows = db.execute(
                """SELECT p.name, p.party FROM document_politicians dp
                   JOIN tracked_politicians p ON dp.politician_id = p.id
                   WHERE dp.document_id = ?
                     AND p.relationship_type NOT IN
                       ('journalist','influencer','neutral','inactive','organization')
                   ORDER BY dp.politician_id LIMIT 3""",
                (d["id"],),
            ).fetchall()
            title = d["title"] or "(bez nosaukuma)"
            if len(title) > 110:
                title = title[:107] + "…"
            if signers_rows:
                parts = []
                for s in signers_rows:
                    short = _short_party(s["party"])
                    parts.append(f"{s['name']}{f' ({short})' if short else ''}")
                signer_str = ", ".join(parts)
            else:
                signer_str = "—"
            url = d["source_url"]
            if url:
                lines.append(
                    f"{t('•')} {link(title, url)} {t('—')} {t(signer_str)}"
                )
            else:
                lines.append(f"{t('•')} {t(title)} {t('—')} {t(signer_str)}")

    contras = db.execute(
        """SELECT c.topic, c.summary, c.severity, p.name AS pname, p.party
           FROM contradictions c
           JOIN tracked_politicians p ON c.opponent_id = p.id
           WHERE date(c.detected_at) = ?
             AND COALESCE(c.confirmed, 1) = 1
           ORDER BY c.salience DESC LIMIT 3""",
        (date,),
    ).fetchall()
    if contras:
        lines.append("")
        lines.append(b("Pretrunas:"))
        for c in contras:
            party_short = _short_party(c["party"])
            party_tag = f" {t(f'({party_short})')}" if party_short else ""
            summary = (c["summary"] or "").split("\n", 1)[0]
            if len(summary) > 200:
                summary = summary[:197].rstrip() + "…"
            tail = f"— {c['topic']} ({c['severity']}): {summary}"
            lines.append(f"{t('•')} {b(c['pname'])}{party_tag} {t(tail)}")

    db.close()
    return "\n".join(lines)


_VB_BLOCK_RE = re.compile(
    r"##\s*Viz[uū]ālais\s+brief\s*\n+(.*?)(?=\n##\s|\Z)",
    flags=re.IGNORECASE | re.DOTALL,
)
_VB_FIELD_RE = re.compile(r"^\s*-\s*\*\*([^*]+):\*\*\s*(.*?)\s*$")


def strip_visual_brief_block(content: str) -> str:
    """Remove `## Vizuālais brief` block from a brief's markdown content.

    The block is internal scaffolding consumed by parse_visual_brief() at
    store time and by @graphics-designer; it should not appear on the
    public blog rendering. Returns the content with the block removed
    (and surrounding blank lines collapsed).
    """
    cleaned = _VB_BLOCK_RE.sub("", content)
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

        if stat_raw in ("", "-", "—", "nav"):
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
