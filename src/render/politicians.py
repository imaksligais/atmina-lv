"""Render the per-politician profile pages.

Phase F3b (refactor-plan-2026-04-29 § Fāze 3) carve-out from
src/generate.py. Imports flow strictly from ``src.render._common`` —
no peer-module dependencies.

Outputs:
- ``output/atmina/politiki/<slug>.html`` — one detail page per
  tracked politician (~159 pages). The Personas index lives in
  src/render/personas.py.

Sibling module ``src.render.personas`` shares ``_get_last_activity``
via ``_common`` (F4 leaf rule — neither imports from the other).
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any

from jinja2 import Environment

from src.coalition import get_coalition_map
from src.profile_kind import profile_kind_label
from src.render._common import (
    TOPIC_COLORS,
    _topic_page_href,
    ASSETS_DIR,
    BASE_URL,
    _bill_slug,
    _date_sort_key,
    _enrich_contradiction,
    _initials_from_name,
    _load_wiki_profile,
    _lv_plural,
    _outlet_feed_map,
    _render_page,
    _slugify,
    norm_source_domain_sql,
    derive_profile_kind,
    faction_alignment_data,
    vote_alignment_data,
)
from src.render.bio import load_bios, load_mandate_notes
from src.render.vad import (
    VadDeclarationView,
    get_vad_data_for_politicians,
)

# Profila ciļņu būvētāji — izcelti uz src/render/politicians_tabs.py (5.6 fāze).
# Re-importēti šeit, lai vēsturiskais ceļš `from src.render.politicians import
# _build_parskats_data` (tests/test_render_politicians_parskats.py,
# tests/test_render_saites.py) turpina strādāt.
from src.render.politicians_tabs import (  # noqa: F401  re-exported: historical import path
    NOT_ATTENDANCE_SQL,
    PARSKATS_CONTRADICTION_SALIENCE_MIN,
    PARSKATS_TOPIC_COUNT_MIN,
    PARSKATS_TOPIC_WINDOW_DAYS,
    _build_parskats_data,
    _dominant_topics_block,
    _fetch_saites_for_profile,
    _format_relative_time_lv,
    _latest_activity_block,
    _monthly_activity,
    _profile_stat_tiles,
    _saites_neighbors_with_coords,
    _table_exists,
    _top_contradiction_block,
    _vote_alignment_for,
)

# Cik tēmu čipu Pozīciju filtrā redzami uzreiz; pārējie aiz «Vēl N tēmas»
# (ppv1.js atklāj; ?tema= uz sakļautu tēmu to atver automātiski).
TOPIC_FILTER_VISIBLE = 8




def _fetch_politicians(db: sqlite3.Connection) -> list[dict[str, Any]]:
    """Full politician list with per-person claim/contradiction/vote counts.

    ``claims_count`` is restricted to claim_type='position' so the label
    "pozīcijas" in templates reflects real rhetorical activity rather
    than bulk Saeima vote imports. ``votes_count`` comes from
    ``saeima_individual_votes`` (the raw vote ledger) and is unchanged.
    """
    rows = db.execute(
        "SELECT * FROM tracked_politicians "
        "WHERE relationship_type NOT IN ('inactive', 'commentator') "
        "ORDER BY name"
    ).fetchall()
    results = []
    for r in rows:
        p = dict(r)
        pid = p["id"]
        p["slug"] = _slugify(p["name"])
        p["claims_count"] = db.execute(
            "SELECT COUNT(*) FROM claims WHERE opponent_id = ? AND claim_type = 'position'",
            (pid,),
        ).fetchone()[0]
        # COALESCE(confirmed,1)=1 matches the public pretrunas/temas/search
        # filter — neapstiprinātās pretrunas neskaita, lai profila/typeahead
        # skaitlis nesadalītos no publiskajām lapām.
        p["contradictions_count"] = db.execute(
            "SELECT COUNT(*) FROM contradictions "
            "WHERE opponent_id = ? AND COALESCE(confirmed, 1) = 1",
            (pid,),
        ).fetchone()[0]
        p["votes_count"] = db.execute(
            "SELECT COUNT(*) FROM saeima_individual_votes WHERE politician_id = ?", (pid,)
        ).fetchone()[0]
        # profile_kind drives role-aware tab dispatch in the template.
        # Computed here so politician.profile_kind is available alongside
        # the rest of the politician row without an extra query per page.
        # votes_count is a 14. Saeima count in practice (saeima-tracker
        # is the only votes source; pre-2022 votes were never imported).
        p["profile_kind"] = derive_profile_kind(
            p.get("relationship_type") or "",
            p.get("role"),
            p["votes_count"],
        )
        # Fallback label for the role-chip when ``role`` is empty/None —
        # avoids the legacy ``'Politiķis'`` mis-label on journalist /
        # organization / inactive profiles.
        p["role_label"] = p.get("role") or profile_kind_label(p["profile_kind"])
        results.append(p)
    return results


def _fetch_commentary_about(db: sqlite3.Connection, pid: int) -> list[dict[str, Any]]:
    """Return third-party commentary claims about politician pid.

    A commentary claim has ``speaker_id IS NOT NULL`` and ``speaker_id != opponent_id``
    and ``claim_type = 'commentary'``. Joined with the speaker's tracked_politicians
    row so the template can render "X apgalvo par [this politician]" with a link
    to the speaker's own page.

    Ordering: most recent first (by stated_at, fallback created_at).
    """
    rows = db.execute(
        """
        SELECT c.id, c.topic, c.stance, c.quote, c.confidence, c.reasoning,
               c.source_url, c.stated_at, c.created_at, c.claim_type,
               c.speaker_id,
               sp.name AS speaker_name,
               sp.x_handle AS speaker_handle
        FROM claims c
        JOIN tracked_politicians sp ON sp.id = c.speaker_id
        WHERE c.opponent_id = ?
          AND c.claim_type = 'commentary'
          AND c.speaker_id IS NOT NULL
          AND c.speaker_id != c.opponent_id
        ORDER BY COALESCE(c.stated_at, c.created_at) DESC
        """,
        (pid,),
    ).fetchall()
    return [dict(r) for r in rows]


_VAD_KIND_ELIGIBLE = frozenset(
    {"deputy", "minister", "mep", "regional", "former", "politician"}
)


def _profile_tab_set(
    kind: str,
    has_contradictions: bool = False,
    has_saites_content: bool = False,
    has_vad_data: bool = False,
    has_parskats: bool = False,
    has_publikacijas: bool = False,
    has_saeima_content: bool = True,
) -> list[str]:
    """Return ordered tab IDs for a politician profile, keyed by profile_kind.

    ``tabs[0]`` is the default — both visually (active stat-bar button)
    and behaviorally (open tab on page-load when no URL hash). Per spec
    § 4.1 (2026-05-14):

    - Politiķi / inactive: ``parskats`` first when data exists, else
      ``timeline``.
    - Journalist / analyst: ``publikacijas`` first when data exists,
      else ``timeline``.
    - Organization: ``publikacijas`` first if data, then ``saites`` if
      data, else ``timeline``.

    ``deklaracijas`` is appended for VAD-eligible kinds when
    ``has_vad_data`` is true.
    """
    if kind in ("deputy", "minister", "mep", "regional", "politician", "former") and (
        not has_parskats and not has_saeima_content and has_publikacijas
    ):
        # Nav ne pozīciju, ne balsojumu, ne Saeimas darba, bet ir ziņas/X
        # (2026-10-08: 33 profili). Laika līnija un Pozīcijas būtu «0» —
        # atver uzreiz Publikācijas; Pretrunas/Saites templote rāda tikai ar saturu.
        tabs = ["publikacijas", "pretrunas", "saites"]
    elif kind in ("deputy", "minister", "mep", "regional", "politician", "former"):
        head = ["parskats"] if has_parskats else []
        tail = ["timeline", "pozicijas"]
        # Saeimā cilne rāda balsojumus, likumprojektus, amatus, debates un
        # jautājumus — tā ir jēgpilna tikai tad, ja ir kaut kas no tā.
        # Vārti ir TIKAI ``has_saeima_content``, ne profile_kind: kind izvēlas
        # pēc lomas teksta («ministr…» uzvar balsojumus), tāpēc aktīvs
        # deputāts ar lomu «Ministru prezidenta amata kandidāts» vai
        # «… parlamentārais sekretārs» kļūst par ``minister`` un agrāk
        # palika bez cilnes (2026-10-07: 10 deputāti, Šuvajevam 701
        # balsojums). ``former`` bez Saeimas datiem (bijušie mēri, TV
        # vadītāji) cilni joprojām nesaņem.
        if has_saeima_content:
            tail.append("saeima")
        tail.extend(["pretrunas", "saites"])
        tabs = head + tail
    elif kind in ("journalist", "analyst"):
        if has_publikacijas:
            tabs = ["publikacijas", "timeline", "komentari-by"]
        else:
            tabs = ["timeline", "komentari-by", "publikacijas"]
        if has_contradictions:
            tabs.append("pretrunas")
        if has_saites_content:
            tabs.append("saites")
    elif kind == "organization":
        if has_publikacijas:
            tabs = ["publikacijas", "timeline", "pozicijas", "saites"]
        elif has_saites_content:
            tabs = ["saites", "timeline", "pozicijas"]
        else:
            tabs = ["timeline", "pozicijas", "saites"]
    elif kind == "inactive":
        tabs = ["parskats", "timeline"] if has_parskats else ["timeline"]
    else:
        tabs = ["timeline"]

    if has_vad_data and kind in _VAD_KIND_ELIGIBLE:
        tabs.append("deklaracijas")
    return tabs
def _fetch_commentary_by(db: sqlite3.Connection, pid: int) -> list[dict[str, Any]]:
    """Claims authored BY this politician about OTHERS — journalist/analyst feed.

    Mirror image of ``_fetch_commentary_about``: speaker_id = pid (not
    opponent_id), opponent != speaker (filters first-party self-talk),
    claim_type = 'commentary'. Joined to ``tracked_politicians`` so the
    template can link to the target's profile page.
    """
    rows = db.execute(
        """
        SELECT c.id, c.topic, c.stance, c.quote, c.confidence,
               c.source_url, c.stated_at, c.created_at,
               c.opponent_id AS target_pid,
               target.name AS target_name,
               target.party AS target_party
        FROM claims c
        JOIN tracked_politicians target ON c.opponent_id = target.id
        WHERE c.speaker_id = ?
          AND c.opponent_id != c.speaker_id
          AND c.claim_type = 'commentary'
        ORDER BY COALESCE(c.stated_at, c.created_at) DESC
        LIMIT 50
        """,
        (pid,),
    ).fetchall()
    return [
        {**dict(r), "target_slug": _slugify(r["target_name"]) if r["target_name"] else ""}
        for r in rows
    ]


# Max individual-vote rows rendered inline in the Saeimā tab. The full
# per-deputy ledger (up to ~5700 rows) was ~82% of each heavy deputy page;
# the complete, filterable history lives at balsojumi.html (Balsojumu matrica).
VOTE_DISPLAY_CAP = 100

# Klātbūtnes reģistrācija nav balsojums (Data Contract 4b): biļetena vērtības
# Reģistrējies/Nereģistrējies ir klātbūtnes stāvokļi gan «Deputātu klātbūtnes
# reģistrācijā», gan «Kvoruma pārbaudē». Filtrs pēc vērtības, ne motīva — tā
# pati izvēle kā src/saeima/votes.py::_BALLOT_VALUES_THAT_ARE_POSITIONS.
# Nebalsoja paliek (klātesošs, nenobalsoja). Viens predikāts visām profila
# Saeimas balsojumu vietām, lai skaitļi sakrīt ar sarakstu.
_NOT_ATTENDANCE_SQL = NOT_ATTENDANCE_SQL

# Saeimas aktivitātes bloki Saeimā cilnē (docs/plans/2026-10-06-saeimas-aktivitate.md):
# pēdējo uzstāšanos / jautājumu saraksta garums.
SAEIMA_ACTIVITY_CAP = 10

# Profila Saites cilnē rādīto spriedžu/uzbrukumu/atbalsta kartiņu griesti
# (jaunākās); pilnais tīkls — saites.html.
TENSIONS_CAP = 20

# Amatu grupu secība un etiķetes (vienskaitlis, daudzskaitlis). Līmenis '10'
# (mandāts) netiek rādīts — deputāta profilā tas ir pašsaprotams.
_POSITION_GROUPS: tuple[tuple[str, str, str], ...] = (
    ("2", "Frakcija", "Frakcijas"),
    ("4", "Prezidijs", "Prezidijs"),
    ("3", "Komisija", "Komisijas"),
    ("5", "Apakškomisija", "Apakškomisijas"),
    ("11", "Izmeklēšanas komisija", "Izmeklēšanas komisijas"),
    ("6", "Delegācija", "Delegācijas"),
)
_PLAIN_MEMBER = frozenset({"Deputāts", "Deputāte"})


def _interval_contains(outer: dict[str, Any], inner: dict[str, Any]) -> bool:
    """True, ja ``outer`` periods pilnībā ietver ``inner`` (date_to NULL = turpinās)."""
    if outer["date_from"] > inner["date_from"]:
        return False
    if outer["date_to"] is None:
        return True
    return inner["date_to"] is not None and inner["date_to"] <= outer["date_to"]


def _group_deputy_positions(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Saeimas amati → {current: [grupas], ended: [amati]}.

    Vienkāršā «Deputāts/Deputāte» rinda tiek izmesta, ja tai pašai institūcijai
    ir vadošā amata rinda, kuras periods to pilnībā ietver (titania dod abas).
    Ietveršana, ne pārklāšanās: atgriešanās par ierindas locekli pēc
    priekšsēdētāja amata beigām ir patstāvīga rinda un paliek.
    """
    items = [
        {**r, "position": (r["position"] or "").strip()}
        for r in rows if r["level"] != "10"
    ]
    leads = [r for r in items if r["position"] not in _PLAIN_MEMBER]
    kept = [
        {**r, "role": None if r["position"] in _PLAIN_MEMBER else r["position"]}
        for r in items
        if r["position"] not in _PLAIN_MEMBER or not any(
            lead["level"] == r["level"] and lead["body"] == r["body"]
            and _interval_contains(lead, r)
            for lead in leads
        )
    ]
    current_rows = [r for r in kept if r["date_to"] is None]
    known = {lvl for lvl, _, _ in _POSITION_GROUPS}
    current: list[dict[str, Any]] = []
    for lvl, singular, plural in _POSITION_GROUPS:
        grp = sorted(
            (r for r in current_rows if r["level"] == lvl),
            key=lambda r: (r["date_from"], r["body"]),
        )
        if grp:
            current.append({"label": singular if len(grp) == 1 else plural, "roles": grp})
    other = [r for r in current_rows if r["level"] not in known]
    if other:
        current.append({"label": "Citi amati", "roles": other})
    ended = sorted(
        (r for r in kept if r["date_to"] is not None),
        key=lambda r: (r["date_to"], r["date_from"]),
        reverse=True,
    )
    return {"current": current, "ended": ended}


# «… (iesniegts 23.09.2026.)» — datums jau ir savā kolonnā.
_QUESTION_DATE_TAIL_RE = re.compile(r"\s*\(iesniegts \d{2}\.\d{2}\.\d{4}\.?\)\s*$")
# Starpposms, ne iznākums («Atbilde pārcelta uz nākamo sēdi: Ministre informē, …»).
_QUESTION_INTERIM = "Atbilde pārcelta"


def _question_status_short(raw: str | None) -> str:
    """Titania rezultāta ķēde → pēdējais iznākums bez paskaidrojuma.

    «Nodots Pieprasījumu komisijai; Noraidīts» → «Noraidīts»;
    «Atbildēts rakstveidā: Saņemtā … apmierina.; Atbilde pārcelta …» → «Atbildēts rakstveidā».
    Pilnais teksts paliek title atribūtā.
    """
    labels = [seg.split(":", 1)[0].strip() for seg in (raw or "").split(";")]
    labels = [lab for lab in labels if lab and not lab.startswith(_QUESTION_INTERIM)]
    return labels[-1] if labels else (raw or "").strip()


def _lv_duration(seconds: int | None) -> str:
    """Sekundes → «2 st. 5 min» / «12 min» / «<1 min»; tukšs, ja nav datu."""
    if not seconds or seconds <= 0:
        return ""
    if seconds < 60:
        return "<1 min"
    hours, minutes = divmod(round(seconds / 60), 60)
    if not hours:
        return f"{minutes} min"
    return f"{hours} st. {minutes} min" if minutes else f"{hours} st."


def _fetch_saeima_activity(db: sqlite3.Connection, pid: int) -> dict[str, Any]:
    """Amati, uzstāšanās debatēs un iesniegtie jautājumi Saeimā cilnei.

    Pa vienam vaicājumam blokam; kopskaitus dod loga funkcijas tajā pašā
    vaicājumā. Debašu ``opinion`` apzināti netiek nolasīts — tas nav nostāja.
    Adresāta loma (ministri) vēl netiek rādīta (plāna «Zināmie robi»).
    """
    roles: dict[str, Any] = {"current": [], "ended": []}
    speeches: dict[str, Any] = {"total": 0, "time": "", "rows": []}
    questions: dict[str, Any] = {"jautajumi": 0, "pieprasijumi": 0, "rows": []}
    try:
        pos_rows = db.execute("""
            SELECT level, body, position, date_from, date_to
            FROM saeima_deputy_positions
            WHERE politician_id = ?
        """, (pid,)).fetchall()
        roles = _group_deputy_positions([dict(r) for r in pos_rows])

        sp_rows = db.execute("""
            SELECT s.session_date, s.document_nr, s.item_title, s.duration_sec,
                   b.document_nr AS bill_nr,
                   COUNT(*) OVER () AS n_total,
                   SUM(s.duration_sec) OVER () AS sec_total
            FROM saeima_debate_speeches s
            LEFT JOIN saeima_bills b ON b.document_nr = s.document_nr
            WHERE s.politician_id = ?
            ORDER BY s.session_date DESC, s.dkp_id DESC, s.speaker_order DESC
            LIMIT ?
        """, (pid, SAEIMA_ACTIVITY_CAP)).fetchall()
        if sp_rows:
            speeches = {
                "total": sp_rows[0]["n_total"],
                "time": _lv_duration(sp_rows[0]["sec_total"]),
                "rows": [
                    {
                        "session_date": r["session_date"],
                        "document_nr": r["document_nr"],
                        "item_title": r["item_title"],
                        "duration": _lv_duration(r["duration_sec"]),
                        "bill_slug": _bill_slug(r["bill_nr"]) if r["bill_nr"] else None,
                    }
                    for r in sp_rows
                ],
            }

        q_rows = db.execute("""
            SELECT q.doc_nr, q.kind, q.title, q.status, q.result,
                   q.submitted_date, q.source_url,
                   SUM(q.kind = 'jautajums') OVER () AS n_j,
                   SUM(q.kind = 'pieprasijums') OVER () AS n_p
            FROM saeima_questions q
            JOIN saeima_question_politicians qp ON qp.question_id = q.id
            WHERE qp.politician_id = ? AND qp.role = 'submitter'
            ORDER BY q.submitted_date DESC, q.id DESC
            LIMIT ?
        """, (pid, SAEIMA_ACTIVITY_CAP)).fetchall()
        if q_rows:
            questions = {
                "jautajumi": q_rows[0]["n_j"],
                "pieprasijumi": q_rows[0]["n_p"],
                "rows": [
                    {**dict(r), "title": _QUESTION_DATE_TAIL_RE.sub("", r["title"] or ""),
                     "status_short": _question_status_short(r["result"] or r["status"])}
                    for r in q_rows
                ],
            }
    except sqlite3.OperationalError:
        # Saeimas aktivitātes tabulu nav (vecs testa DB) — bloki paliek tukši.
        pass
    return {"roles": roles, "speeches": speeches, "questions": questions}


# Vienotās aktivitātes saraksta griesti (Laika līnija cilne). Pārskatā rāda
# pirmās PARSKATS_TIMELINE_ROWS no tā paša saraksta.
TIMELINE_LIMIT = 50
PARSKATS_TIMELINE_ROWS = 6

# Laika līnijas tipi: (filtra nosaukums) — secība = filtra pogu secība.
TIMELINE_TYPES: tuple[tuple[str, str], ...] = (
    ("claim", "Pozīcijas"),
    ("speech", "Uzstāšanās"),
    ("question", "Jautājumi"),
    ("vote_day", "Saeimas sēdes"),
)


def _dmy(iso: str | None) -> str:
    s = (iso or "")[:10]
    return f"{s[8:10]}.{s[5:7]}.{s[:4]}" if len(s) == 10 and s[4] == "-" else s


def _fetch_activity_timeline(
    db: sqlite3.Connection, pid: int,
) -> tuple[list[dict[str, Any]], int]:
    """Vienotais aktivitātes avots: pozīcijas, uzstāšanās debatēs, iesniegtie
    jautājumi un Saeimas sēdes dienas (balsojumi SAKĻAUTI pa ``vote_date``).

    Atsevišķa balsojuma rindas šeit nav apzināti (T14 — procedurāls balsojums
    nav pozīcija; atsevišķie balsojumi paliek Saeimā cilnē). Uzstāšanās
    sakļautas pa (sēdes diena, darba kārtības punkts) — viens punkts var nest
    vairākas runas. Kopskaits = ``COUNT(*)`` no TĀ PAŠA UNION, tāpēc cilnes
    skaitlis un saraksts nevar izšķirties.

    claim_type='position' izmet 'saeima_vote' (dublē balsojumus, DD.MM.YYYY
    datumi lauž ISO kārtošanu) un 'commentary' (trešās personas runa — Saites
    cilnē).
    """
    arms = ["""
        SELECT stated_at AS date, 'claim' AS event_type, topic, stance AS detail,
               source_url, NULL AS n, NULL AS ref, 0 AS ord
        FROM claims
        WHERE opponent_id = ? AND claim_type = 'position' AND stated_at IS NOT NULL
    """]
    params: list[Any] = [pid]
    if _table_exists(db, "saeima_debate_speeches"):
        bill_join = (
            "LEFT JOIN saeima_bills b ON b.document_nr = s.document_nr"
            if _table_exists(db, "saeima_bills") else ""
        )
        bill_col = "MAX(b.document_nr)" if bill_join else "NULL"
        arms.append(f"""
            SELECT s.session_date, 'speech', NULL,
                   COALESCE(s.item_title, s.document_nr), NULL, COUNT(*),
                   {bill_col}, 1
            FROM saeima_debate_speeches s {bill_join}
            WHERE s.politician_id = ? AND s.session_date IS NOT NULL
            GROUP BY s.session_date, COALESCE(s.item_title, s.document_nr, '')
        """)
        params.append(pid)
    if _table_exists(db, "saeima_questions") and _table_exists(db, "saeima_question_politicians"):
        arms.append("""
            SELECT q.submitted_date, 'question', NULL, q.title, q.source_url, NULL,
                   q.kind, 2
            FROM saeima_questions q
            WHERE q.submitted_date IS NOT NULL
              AND q.id IN (SELECT question_id FROM saeima_question_politicians
                           WHERE politician_id = ? AND role = 'submitter')
        """)
        params.append(pid)
    arms.append(f"""
        SELECT sv.vote_date, 'vote_day', NULL, NULL, NULL, COUNT(*), NULL, 3
        FROM saeima_individual_votes siv
        JOIN saeima_votes sv ON siv.vote_id = sv.id
        WHERE siv.politician_id = ? AND {_NOT_ATTENDANCE_SQL}
          AND sv.vote_date IS NOT NULL
        GROUP BY sv.vote_date
    """)
    params.append(pid)
    union = " UNION ALL ".join(arms)

    total = db.execute(f"SELECT COUNT(*) FROM ({union})", params).fetchone()[0]
    # Līdz TIMELINE_LIMIT jaunākajiem KATRA tipa — lai tipa filtrs (ppv1.js)
    # rāda, piem., sēžu dienas arī tad, ja kopējos 50 jaunākos aizņem
    # pozīcijas. Rindas aiz kopējiem 50 jaunākajiem nes ``extra`` — templote
    # tās slēpj (bez JS redzami tieši 50 jaunākie, kā agrāk).
    rows = db.execute(
        f"""SELECT * FROM (
                SELECT u.*, ROW_NUMBER() OVER (
                    PARTITION BY event_type ORDER BY date DESC, ord) AS rn
                FROM ({union}) u)
            WHERE rn <= ? ORDER BY date DESC, ord""",
        [*params, TIMELINE_LIMIT],
    ).fetchall()

    timeline: list[dict[str, Any]] = []
    for i, r in enumerate(rows):
        e = dict(r)
        e["extra"] = i >= TIMELINE_LIMIT
        e["date_label"] = _dmy(e["date"])
        kind = e["event_type"]
        # link = ārēja adrese (templotē caur safe_url); href = iekšēja lapa;
        # tab_link = cilne šajā pašā profilā.
        e["link"] = e["href"] = e["link_label"] = e["tab_link"] = None
        if kind == "claim":
            e["title"] = "Pozīcija"
            if e["source_url"]:
                e["link"], e["link_label"] = e["source_url"], "Avots"
        elif kind == "speech":
            e["title"] = "Uzstāšanās debatēs"
            n = e["n"] or 1
            e["meta"] = f"{n} {_lv_plural(n, 'runa', 'runas')}" if n > 1 else None
            if e["ref"]:
                e["href"] = f"../likumprojekti/{_bill_slug(e['ref'])}.html"
                e["link_label"] = "Likumprojekts"
            else:
                e["tab_link"], e["link_label"] = "saeima", "Skatīt cilnē «Saeimā»"
        elif kind == "question":
            e["title"] = ("Iesniegts pieprasījums" if e["ref"] == "pieprasijums"
                          else "Iesniegts jautājums")
            e["detail"] = _QUESTION_DATE_TAIL_RE.sub("", e["detail"] or "")
            if e["source_url"]:
                e["link"], e["link_label"] = e["source_url"], "Saeimas dokuments"
        else:  # vote_day
            n = e["n"] or 0
            e["title"] = "Saeimas sēde"
            e["meta"] = f"{n} {_lv_plural(n, 'balsojums', 'balsojumi')}"
            e["tab_link"], e["link_label"] = "saeima", "Skatīt balsojumus"
        e.setdefault("meta", None)
        timeline.append(e)
    return timeline, total


def _fetch_politician_detail(
    db: sqlite3.Connection,
    pid: int,
    profile_kind: str = "politician",
    vad_data: list[VadDeclarationView] | None = None,
    feed_outlets: dict[int, dict[str, Any]] | None = None,
    align: dict[str, Any] | None = None,
    faction_alignment: dict[int, dict[str, int]] | None = None,
) -> dict[str, Any]:
    """Full detail for one politician: positions, contradictions, votes.

    After Phase D2 of the claim_type split: the Pozīcijas tab iterates
    ``positions`` (claim_type='position' only). The Balsojumi tab uses
    the ``votes`` list, which comes from the richer saeima_individual_votes
    ledger (with per-vote faction breakdown and result metadata) — a
    strictly better representation than would be possible from just the
    claims table. The legacy ``claims`` key is retained for any
    consumer that still expects a unified list.
    """
    claims_rows = db.execute("""
        SELECT c.*, COALESCE(d.platform, '') AS platform
        FROM claims c
        LEFT JOIN documents d ON c.document_id = d.id
        WHERE c.opponent_id = ? AND c.claim_type = 'position'
        ORDER BY c.stated_at DESC
    """, (pid,)).fetchall()
    positions = [dict(r) for r in claims_rows]
    # Sort by stated_at DESC, tiebreaker by salience DESC — ensures
    # same-day claims show in importance order. Without salience tiebreaker,
    # Pārskats Bloks A picked arbitrary claim when politiķim multiple
    # claims sharing stated_at (e.g., Siliņas 14.05 demisija sal=1.0
    # vs Melņa aizstāvība sal=0.9, both stated_at='2026-05-14').
    positions.sort(
        key=lambda c: (_date_sort_key(c.get("stated_at") or ""), c.get("salience") or 0.0),
        reverse=True,
    )
    # Back-compat alias for any consumer still reading `claims`. Same list
    # — Phase C/D cross-checks showed no site reader needs a union list.
    claims = positions

    # Contradictions
    # INNER JOIN tp is safe — this function is always called with a live pid
    # from the politicians list, so tp.id will resolve. Matches _fetch_contradictions.
    ct_rows = db.execute("""
        SELECT
            ct.id, ct.opponent_id, ct.topic, ct.summary, ct.severity,
            ct.detected_at, ct.salience, ct.confirmed,
            tp.name AS politician_name, tp.party, tp.role,
            c_old.stance AS old_stance, c_old.stated_at AS old_date,
            c_old.source_url AS old_source, c_old.quote AS old_quote,
            c_new.stance AS new_stance, c_new.stated_at AS new_date,
            c_new.source_url AS new_source, c_new.quote AS new_quote
        FROM contradictions ct
        JOIN tracked_politicians tp ON ct.opponent_id = tp.id
        LEFT JOIN claims c_old ON ct.claim_old_id = c_old.id
        LEFT JOIN claims c_new ON ct.claim_new_id = c_new.id
        WHERE ct.opponent_id = ?
          AND COALESCE(ct.confirmed, 1) = 1
        ORDER BY ct.detected_at DESC
    """, (pid,)).fetchall()
    # The count above was confirmed-gated since 2026-06-10; this LIST was not,
    # so unconfirmed candidates rendered as "≈ Pozīcijas maiņa" cards on the
    # live profile (#40 Judins since June, #47/#48/#49) — 2026-09-20.
    contradictions = []
    for r in ct_rows:
        d = dict(r)
        _enrich_contradiction(d, db)
        contradictions.append(d)

    # Individual votes — inline ledger capped at VOTE_DISPLAY_CAP most-recent
    # rows (the full history was the dominant deputy-page weight). votes_total
    # is the true count, kept for the profile stat chip + the "rādīti N no M"
    # link to the full Balsojumu matrica.
    votes_total = db.execute(
        "SELECT COUNT(*) FROM saeima_individual_votes siv "
        f"WHERE siv.politician_id = ? AND {_NOT_ATTENDANCE_SQL}",
        (pid,),
    ).fetchone()[0]
    votes_rows = db.execute(f"""
        SELECT siv.vote, sv.motif, sv.vote_date, sv.vote_time, sv.result
        FROM saeima_individual_votes siv
        JOIN saeima_votes sv ON siv.vote_id = sv.id
        WHERE siv.politician_id = ? AND {_NOT_ATTENDANCE_SQL}
        ORDER BY sv.vote_date DESC, sv.vote_time DESC
        LIMIT ?
    """, (pid, VOTE_DISPLAY_CAP)).fetchall()
    votes = [dict(r) for r in votes_rows]

    # Balsojumu ierakstu datumu diapazons (pilnais reģistrs, ne tikai
    # rādītais CAP). Neitrāls datu fakts Saeimā cilnes galvai — bijušam
    # deputātam (piem., Ainārs Šlesers, mandāts līdz 2025-06) beigu datums
    # uzreiz parāda, ka jaunāku balsojumu nav, bez politiskā statusa
    # apgalvojuma (ministriem mandāts ir tikai apturēts — T6 robi).
    vote_date_range = None
    if votes_total:
        rng = db.execute(f"""
            SELECT MIN(sv.vote_date) mn, MAX(sv.vote_date) mx
            FROM saeima_individual_votes siv
            JOIN saeima_votes sv ON siv.vote_id = sv.id
            WHERE siv.politician_id = ? AND {_NOT_ATTENDANCE_SQL}
        """, (pid,)).fetchone()
        if rng and rng["mn"]:
            vote_date_range = {"min": rng["mn"], "max": rng["mx"]}

    # Unique topics for filter (alphabetical list kept for existing readers)
    claim_topics = sorted(set(c["topic"] for c in claims if c.get("topic")))
    # Filter bar chips: biežākā pirmā, ar skaitu un tēmas krāsu; aiz
    # TOPIC_FILTER_VISIBLE sakļautas (templote liek `hidden`, ppv1.js atklāj).
    _topic_counts: dict[str, int] = {}
    for c in claims:
        if c.get("topic"):
            _topic_counts[c["topic"]] = _topic_counts.get(c["topic"], 0) + 1
    claim_topic_chips = [
        {"name": t, "count": n, "color": TOPIC_COLORS.get(t, "#9aa0a6")}
        for t, n in sorted(_topic_counts.items(), key=lambda kv: (-kv[1], kv[0]))
    ]

    timeline, timeline_total = _fetch_activity_timeline(db, pid)

    # Tensions involving this politician. Saraksts griests pie TENSIONS_CAP;
    # ``tensions_total`` = tas pats predikāts bez LIMIT — Saites cilnes
    # skaitlim un «Rādītas N no M» piezīmei (2026-10-08, backlog/vietne-ui.md).
    tension_from = """
        FROM political_tensions pt
        JOIN tracked_politicians s ON pt.source_pid = s.id
        JOIN tracked_politicians t ON pt.target_pid = t.id
        WHERE (pt.source_pid = ? OR pt.target_pid = ?)
          AND s.relationship_type NOT IN ('inactive', 'commentator')
          AND t.relationship_type NOT IN ('inactive', 'commentator')
    """
    tension_rows = db.execute(f"""
        SELECT pt.*, s.name AS source_name, s.party AS source_party,
               t.name AS target_name, t.party AS target_party
        {tension_from}
        ORDER BY pt.created_at DESC LIMIT ?
    """, (pid, pid, TENSIONS_CAP)).fetchall()
    tensions = [dict(r) for r in tension_rows]
    tensions_total = db.execute(
        f"SELECT COUNT(*) {tension_from}", (pid, pid)).fetchone()[0]

    # Recent news mentioning this politician (subject first, then mentioned).
    # GROUP BY d.id: junction PK ir (document_id, politician_id, role), tāpēc
    # vienam pārim var būt vairākas rindas ar dažādām lomām ('subject' +
    # 'mentioned') — bez sabrukšanas dokuments renderējas divreiz un apēd
    # vienu no TOP-10 slotiem (backlog/vietne-ui.md). Lomu sabrukšanā
    # 'subject' prioritārs — templote pēc n.role rāda «pieminēts» birku.
    news_rows = db.execute("""
        SELECT d.id, d.source_url, d.source_domain, d.scraped_at,
               SUBSTR(d.content, 1, 200) as preview,
               CASE WHEN MAX(dp.role = 'subject') THEN 'subject'
                    ELSE MIN(dp.role) END AS role
        FROM documents d
        JOIN document_politicians dp ON dp.document_id = d.id
        WHERE dp.politician_id = ? AND d.platform = 'web'
        GROUP BY d.id
        ORDER BY MAX(dp.role = 'subject') DESC,
                 d.scraped_at DESC
        LIMIT 10
    """, (pid,)).fetchall()
    news = [dict(r) for r in news_rows]
    news_total = db.execute(
        "SELECT COUNT(DISTINCT d.id) FROM documents d "
        "JOIN document_politicians dp ON dp.document_id = d.id "
        "WHERE dp.politician_id = ? AND d.platform = 'web'", (pid,)).fetchone()[0]

    # Medija paša publikācijas — tikai organizāciju profiliem, kuriem ir
    # outlets mapping (sources.yaml outlet, kura X feeds saskan ar profila
    # social_accounts.handle). Atlasa pēc source_domain (NE matcher-saiti),
    # tāpēc parādās arī raksti, kuros medijs nepiemin sevi. `news` saraksts
    # paliek pieminējumu signāls; šis ir paša satura signāls.
    own_pubs: list[dict[str, Any]] = []
    own_pubs_total = 0
    own_pubs_outlet: dict[str, str] | None = None
    if profile_kind == "organization":
        if feed_outlets is None:
            feed_outlets = _outlet_feed_map(db)
        outlet = feed_outlets.get(pid)
        if outlet:
            # Normalizē hostus Python-ā (nostrippo www.) — sakrīt ar SQL NORM.
            # Secība saglabāta: hosts[0] = primārais domēns sadaļas virsrakstam.
            hosts: list[str] = []
            for h in outlet.get("hosts") or []:
                h = (h or "").strip().lower()
                if h.startswith("www."):
                    h = h[4:]
                if h and h not in hosts:
                    hosts.append(h)
            if hosts:
                norm = norm_source_domain_sql("d.source_domain")
                ph = ",".join("?" * len(hosts))
                own_rows = db.execute(f"""
                    SELECT d.id, d.source_url, d.source_domain, d.scraped_at,
                           d.published_at, SUBSTR(d.content, 1, 200) AS preview
                    FROM documents d
                    WHERE d.platform = 'web' AND {norm} IN ({ph})
                    ORDER BY COALESCE(d.published_at, d.scraped_at) DESC
                    LIMIT 10
                """, hosts).fetchall()
                own_pubs = [dict(r) for r in own_rows]
                own_pubs_total = db.execute(
                    f"SELECT COUNT(*) FROM documents d "
                    f"WHERE d.platform = 'web' AND {norm} IN ({ph})", hosts,
                ).fetchone()[0]
            # `host` = primārais domēns virsrakstam "Publikācijas vietnē X" —
            # brenda nosaukums nominatīvā virsrakstā prasītu ģenitīva locījumu.
            own_pubs_outlet = {
                "name": outlet["name"], "slug": outlet["slug"],
                "host": hosts[0] if hosts else None,
            }

    # Party metadata (color, link to party page)
    party_meta = None
    politician_row = db.execute("SELECT party FROM tracked_politicians WHERE id = ?", (pid,)).fetchone()
    if politician_row:
        p_party = politician_row[0]
        if p_party:
            try:
                party_row = db.execute(
                    "SELECT * FROM parties WHERE name = ? OR short_name = ?",
                    (p_party, p_party)
                ).fetchone()
                if party_row:
                    party_meta = dict(party_row)
            except Exception:
                pass

    commentary_about = _fetch_commentary_about(db, pid)

    # External profiles (FB, website, ...) — fetch-ready shēma, pagaidām tikai UI.
    ext_rows = db.execute(
        "SELECT platform, url, handle, display_label "
        "FROM external_profiles WHERE opponent_id=? AND active=1 "
        "ORDER BY platform, id",
        (pid,),
    ).fetchall()
    external_profiles = [dict(r) for r in ext_rows]

    # X subtab: the politician's OWN tweets — role='subject' on twitter
    # platform docs. Excludes x_mention (always third-party-authored about
    # them) and 'mentioned' / 'mention_target' roles (where someone else
    # is the speaker). Distinct from `news` (web articles) and
    # `commentary_about` (curated commentary claims).
    x_posts_rows = db.execute("""
        SELECT d.id, d.content, d.source_url, d.source_domain,
               d.platform, d.published_at, d.scraped_at, d.language,
               dp.role
        FROM documents d
        JOIN document_politicians dp ON dp.document_id = d.id
        WHERE dp.politician_id = ?
          AND d.platform = 'twitter'
          AND dp.role = 'subject'
        ORDER BY COALESCE(d.published_at, d.scraped_at) DESC
        LIMIT 50
    """, (pid,)).fetchall()
    x_posts = [dict(r) for r in x_posts_rows]

    # Bills this politician is linked to via saeima_bill_politicians junction.
    # Currently empty in production (Phase 1A backfill didn't populate junction);
    # Phase 1C live agent will populate it going forward.
    # Guard against test DBs that haven't run init_saeima_bills().
    bills_involved = []
    try:
        for r in db.execute("""
            SELECT DISTINCT b.id, b.document_nr, b.bill_type, b.title, b.summary, b.topic,
                   b.current_stage, b.current_status, b.last_updated_at, b.first_seen_at,
                   b.institutional_submitter,
                   (SELECT COUNT(*) FROM saeima_bill_politicians WHERE bill_id=b.id AND role='submitter') AS submitter_count,
                   (SELECT COUNT(*) FROM saeima_bill_stages WHERE bill_id=b.id) AS stage_count,
                   (SELECT COUNT(*) FROM saeima_votes WHERE bill_id=b.id) AS vote_count
            FROM saeima_bills b
            JOIN saeima_bill_politicians bp ON bp.bill_id = b.id
            WHERE bp.politician_id = ?
            ORDER BY b.last_updated_at DESC
        """, (pid,)).fetchall():
            bills_involved.append({
                **dict(r),
                "slug": _bill_slug(r["document_nr"]),
            })
    except sqlite3.OperationalError:
        # saeima_bills tables not present (legacy test DB) — silently return empty
        bills_involved = []

    saeima_activity = _fetch_saeima_activity(db, pid)

    saites_data = _fetch_saites_for_profile(
        db, pid, profile_kind, tensions, commentary_about, align=align,
        has_votes=votes_total > 0,
    )
    has_saites_content = bool(
        saites_data["uzbrukumi"] or saites_data["spriedzes"]
        or saites_data["atbalsts"] or saites_data["commentary_about"]
        or saites_data["vote_alignment_top"]
    )
    commentary_by: list[dict[str, Any]] = []
    if profile_kind in ("journalist", "analyst"):
        commentary_by = _fetch_commentary_by(db, pid)
    vad_data = vad_data or []

    # Pārskats data — built only for kinds where the tab is offered
    # (politiķi + inactive; žurnālisti / analītiķi / organizācijas saglabā
    # Publikācijas / Saites kā primāro signālu — sk. _profile_tab_set base
    # mapping). Empty dict signals "no Pārskats" → tab_set excludes it.
    parskats_data: dict[str, Any] = {}
    if profile_kind not in ("journalist", "analyst", "organization"):
        parskats_data = _build_parskats_data(
            db, pid, positions, contradictions, faction_alignment=faction_alignment,
        )

    tab_set = _profile_tab_set(
        profile_kind,
        has_contradictions=bool(contradictions),
        has_saites_content=has_saites_content,
        has_vad_data=bool(vad_data),
        has_parskats=bool(parskats_data),
        has_publikacijas=bool(x_posts or news or own_pubs),
        has_saeima_content=(
            votes_total > 0 or bool(bills_involved)
            or bool(saeima_activity["roles"]["current"] or saeima_activity["roles"]["ended"])
            or bool(saeima_activity["speeches"]["rows"])
            or bool(saeima_activity["questions"]["rows"])
        ),
    )

    # Skaitļu josla (plāns 2026-10-07 B.3). Reālie kopskaiti, ne sarakstu
    # griesti: x_posts/news/commentary_by/tensions saraksti ir ar LIMIT.
    saites_count = tensions_total + sum(len(saites_data[k]) for k in (
        "commentary_about", "vote_alignment_top", "vote_alignment_bottom"))
    saites_data["tensions_shown"] = len(tensions)
    saites_data["tensions_total"] = tensions_total
    stat_counts = {
        "pozicijas": len(positions),
        "balsojumi": votes_total,
        "pretrunas": len(contradictions),
        # Visi saistītie dokumenti (jebkura loma: subjekts, pieminēts).
        "dokumenti": db.execute(
            "SELECT COUNT(DISTINCT document_id) FROM document_politicians "
            "WHERE politician_id = ?", (pid,)).fetchone()[0],
        "x": db.execute(
            "SELECT COUNT(DISTINCT d.id) FROM documents d "
            "JOIN document_politicians dp ON dp.document_id = d.id "
            "WHERE dp.politician_id = ? AND d.platform = 'twitter' AND dp.role = 'subject'",
            (pid,)).fetchone()[0],
        "komentari": db.execute(
            "SELECT COUNT(*) FROM claims WHERE speaker_id = ? AND opponent_id != speaker_id "
            "AND claim_type = 'commentary'", (pid,)).fetchone()[0]
        if profile_kind in ("journalist", "analyst") else 0,
        "saites": saites_count,
    }
    stat_tiles = _profile_stat_tiles(profile_kind, stat_counts, tab_set)
    monthly = _monthly_activity(db, pid) if "parskats" in tab_set else None

    return {
        "stat_tiles": stat_tiles,
        "monthly": monthly,
        "bills_involved": bills_involved,
        "saeima_roles": saeima_activity["roles"],
        "saeima_speeches": saeima_activity["speeches"],
        "saeima_questions": saeima_activity["questions"],
        "claims": claims,
        "commentary_about": commentary_about,
        "commentary_by": commentary_by,
        "contradictions": contradictions,
        "external_profiles": external_profiles,
        "news": news,
        "own_pubs": own_pubs,
        "own_pubs_outlet": own_pubs_outlet,
        # Publikāciju cilnes REĀLIE kopskaiti — saraksti augstāk ir ar LIMIT
        # (X 50, ziņas 10, paša publikācijas 10); cilnes skaitlim jāsakrīt
        # ar skaitļu joslu (2026-10-07).
        "pub_totals": {"x": stat_counts["x"], "news": news_total, "own": own_pubs_total},
        "party_meta": party_meta,
        "positions": positions,
        "claim_topics": claim_topics,
        "claim_topic_chips": claim_topic_chips,
        "claim_topic_chips_visible": TOPIC_FILTER_VISIBLE,
        "parskats_data": parskats_data,
        "saites_data": saites_data,
        "saites_count": saites_count,
        "tab_set": tab_set,
        "timeline": timeline,
        "timeline_total": timeline_total,
        "tensions": tensions,
        "vad_data": vad_data,
        "votes": votes,
        "votes_total": votes_total,
        "vote_date_range": vote_date_range,
        "x_posts": x_posts,
    }


def _keep_digging_for_profile(
    p: dict[str, Any],
    politicians: list[dict[str, Any]],
    idx: int,
    db: sqlite3.Connection,
    coalition_map: dict[str, str],
) -> dict[str, Any]:
    """"Turpini rakt" columns for a profile page (hrefs relative to
    ``politiki/<slug>.html``). Deterministic — no runtime randomness — so the
    char baselines stay byte-stable across rebuilds.

    Link enrichment consumed by ``_keep_digging.html.j2``:
    profile links carry ``initials`` + ``coalition`` (avatar + ring/dot colour);
    topic links carry ``count`` + ``bar`` (0–100, ∝ position count → underline).
    """
    columns: list[dict[str, Any]] = []
    party = p.get("party") or ""
    slug = p.get("slug")
    photos_dir = ASSETS_DIR / "photos"

    def _profile_link(q: dict[str, Any], with_party: bool) -> dict[str, Any]:
        q_party = q.get("party") or ""
        return {
            "label": q["name"],
            "href": f"{q['slug']}.html",
            "initials": _initials_from_name(q["name"]),
            "slug": q["slug"],
            "photo": (photos_dir / f"{q['slug']}.jpg").exists(),
            "coalition": coalition_map.get(q_party, "other"),
            "sub": (q_party or None) if with_party else None,
        }

    if party:
        same = [
            q for q in politicians
            if (q.get("party") or "") == party and q.get("slug") != slug
        ][:6]
        if same:
            columns.append({
                "title": "Citi šajā partijā",
                "links": [_profile_link(q, with_party=False) for q in same],
            })

    topic_rows = db.execute(
        """
        SELECT topic, COUNT(*) AS n FROM claims
        WHERE opponent_id = ? AND claim_type = 'position' AND topic IS NOT NULL
        GROUP BY topic ORDER BY n DESC, topic LIMIT 4
        """,
        (p["id"],),
    ).fetchall()
    if topic_rows:
        max_n = max(r["n"] for r in topic_rows) or 1
        columns.append({
            "title": "Tēmas",
            "links": [
                {
                    "label": r["topic"],
                    "href": _topic_page_href(r["topic"]),
                    "count": r["n"],
                    "bar": round(r["n"] / max_n * 100),
                }
                for r in topic_rows
            ],
        })

    # "Vēl profili" — deterministic spread across the roster (no randomness).
    n = len(politicians)
    others: list[dict[str, Any]] = []
    seen = {slug}
    for off in (40, 87, 134, 61, 23):
        if n == 0 or len(others) >= 3:
            break
        q = politicians[(idx + off) % n]
        if q.get("slug") not in seen:
            seen.add(q.get("slug"))
            others.append(q)
    if others:
        columns.append({
            "title": "Vēl profili",
            "links": [_profile_link(q, with_party=True) for q in others],
        })

    return {"columns": columns}


def render_politicians(
    env: Environment,
    db: sqlite3.Connection,
    atmina_dir: Path,
    politicians: list[dict[str, Any]],
    pid_to_syntheses: dict[int, list[dict[str, Any]]],
) -> int:
    """Render one politiki/<slug>.html per tracked politician.

    Mirrors the inline block previously at ``src/generate.py`` lines
    3146-3173. Returns the count of pages emitted (one per politician).
    """
    politiki_dir = atmina_dir / "politiki"
    politiki_dir.mkdir(parents=True, exist_ok=True)
    photos_dir = ASSETS_DIR / "photos"
    photos_exist = photos_dir.exists()

    # Pre-load VAD declarations for all politicians in one batch (F4 leaf-vs-fan-out).
    # Returns empty dict if vad_* tables don't exist yet (Phase 0 not run).
    all_pids = [p["id"] for p in politicians]
    vad_by_pid = get_vad_data_for_politicians(db, all_pids)
    # Galvenes bio (CVK kandidāta ziņas + amati pēc VID deklarācijām).
    bio_by_pid = load_bios(db, all_pids)
    # Saeimā cilne: kāpēc balsojumi beidzas (pārbaudīts ieraksts + novecošanas sargs).
    mandate_notes = load_mandate_notes(db, all_pids)

    # Coalition status per party (one query) — colours the "Turpini rakt"
    # avatar rings + dots. Source of truth: parties.coalition_status.
    coalition_map = get_coalition_map(db)

    feed_outlets = _outlet_feed_map(db)  # opponent_id -> outlet {name, slug}

    # Balsojumu sakritības matrica VIENREIZ visam domēnam — per-pid SQL
    # self-join šeit maksāja ~60s pār 195 profiliem (BACKLOG § Render
    # self-join lēnās stadijas; benchmark 2026-08-20: identiski skaitļi ~2s).
    align = vote_alignment_data(db)
    # «Balso kopā ar savu frakciju» — arī VIENREIZ visiem (~4 s; per-pid būtu ~60 s+).
    faction_alignment = faction_alignment_data(db)

    count = 0
    for idx, p in enumerate(politicians):
        profile_kind = p.get("profile_kind", "politician")
        vad_for_pid = vad_by_pid.get(p["id"], [])
        detail = _fetch_politician_detail(
            db, p["id"], profile_kind, vad_data=vad_for_pid,
            feed_outlets=feed_outlets, align=align,
            faction_alignment=faction_alignment,
        )
        wiki_profile = _load_wiki_profile(p["slug"])
        has_photo = (photos_dir / f"{p['slug']}.jpg").exists() if photos_exist else False
        keep_digging = _keep_digging_for_profile(p, politicians, idx, db, coalition_map)

        _render_page(env, "politician.html.j2", politiki_dir / f"{p['slug']}.html", {
            "politician": p,
            "feed_outlet": feed_outlets.get(p["id"]),
            "BASE_URL": BASE_URL,
            "share_url": f"{BASE_URL}/politiki/{p['slug']}.html",
            "digging": keep_digging,
            "bills_involved": detail["bills_involved"],
            "saeima_roles": detail["saeima_roles"],
            "saeima_speeches": detail["saeima_speeches"],
            "saeima_questions": detail["saeima_questions"],
            "claims": detail["claims"],
            "positions": detail["positions"],
            "contradictions": detail["contradictions"],
            "votes": detail["votes"],
            "votes_total": detail["votes_total"],
            "vote_date_range": detail["vote_date_range"],
            "claim_topics": detail["claim_topics"],
            "claim_topic_chips": detail["claim_topic_chips"],
            "claim_topic_chips_visible": detail["claim_topic_chips_visible"],
            "timeline": detail["timeline"],
            "timeline_types": [
                t for t in TIMELINE_TYPES
                if any(e["event_type"] == t[0] for e in detail["timeline"])
            ],
            "timeline_shown": sum(not e["extra"] for e in detail["timeline"]),
            "parskats_timeline_rows": PARSKATS_TIMELINE_ROWS,
            "stat_tiles": detail["stat_tiles"],
            "monthly": detail["monthly"],
            "timeline_total": detail["timeline_total"],
            "tensions": detail["tensions"],
            "news": detail["news"],
            "own_pubs": detail["own_pubs"],
            "own_pubs_outlet": detail["own_pubs_outlet"],
            "pub_totals": detail["pub_totals"],
            "party_meta": detail["party_meta"],
            "commentary_about": detail["commentary_about"],
            "commentary_by": detail["commentary_by"],
            "external_profiles": detail["external_profiles"],
            "parskats_data": detail["parskats_data"],
            "saites_data": detail["saites_data"],
            "saites_count": detail["saites_count"],
            "tab_set": detail["tab_set"],
            "vad_data": detail["vad_data"],
            "x_posts": detail["x_posts"],
            "wiki_profile": wiki_profile,
            "has_photo": has_photo,
            "bio": bio_by_pid.get(p["id"]),
            "mandate_note": mandate_notes.get(p["id"]),
            "syntheses": pid_to_syntheses.get(p["id"], []),
        })
        count += 1
    return count
