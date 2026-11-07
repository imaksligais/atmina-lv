"""Neutral daily/weekly brief generator for atmina.lv blog."""

import re
from datetime import datetime, timedelta
from pathlib import Path

from src.coalition import party_short_name
from src.contradiction_labels import SEVERITY_LV, lower_first
from src.db import get_db, now_lv_dt
from src.lv_text import split_name

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


# `publish_approvals.subject_key`: pārskata blog slugs vai «Atradumu» lapa
# `analizes/<slug>` (2026-10-19; = ceļš kokā bez .html, sk. check_output.py).
# Analīzes slugs = .md faila stem bez pārveides (render/analyses.py), tāpēc
# atļauts jebkurš stem — citādi vārti bloķētu lapu, kuru nevar apstiprināt.
PUBLISH_KEY_RE = re.compile(
    r"^(?:(?:nedela-)?\d{4}-\d{2}-\d{2}|analizes/[^/\\\s]+)$"
)


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


def publish_content_hash(db, key: str, content_dir: Path | None = None) -> str | None:
    """SHA-256 saturam, ko apstiprina `publish_approvals[key]` (audits A1, 2026-11-03).

    Pārskats: jaunākā daily/weekly `context_notes` rinda ar šo lapas slugu
    (tā pati, ko izvēlas deploy publish-gate). Atradums: content/analizes/<slug>.md.
    Hešo avota saturu, nevis renderēto HTML. CRLF→LF pirms hešošanas: git
    konversija nav satura maiņa. None = šai atslēgai saturs nav atrodams.
    """
    import hashlib

    if key.startswith("analizes/"):
        from src.render._common.constants import CONTENT_DIR

        path = Path(content_dir or CONTENT_DIR) / "analizes" / f"{key.split('/', 1)[1]}.md"
        if not path.is_file():
            return None
        # read_bytes, ne read_text: teksta režīms pats pārvērš CRLF, un tad
        # zemāk esošā aizvietošana nebūtu pārbaudāma.
        text = path.read_bytes().decode("utf-8")
    else:
        text = None
        # Indeksi, ne nosaukumi — `db` var būt bez row_factory.
        for r in db.execute(
            "SELECT topic, content, created_at, note_type FROM context_notes"
            " WHERE note_type IN ('daily_brief','weekly_brief') ORDER BY created_at DESC"
        ):
            d = brief_subject_date(r[0], r[1], r[2])
            if d and brief_publish_key(r[3], d) == key:
                text = r[1] or ""
                break  # DESC — pirmā atbilstošā rinda ir jaunākā
        if text is None:
            return None
    return hashlib.sha256(text.replace("\r\n", "\n").encode("utf-8")).hexdigest()


# Eksplicītā publicēšanas atļauja (`publish_approvals`, T15) ieviesta 2026-08-18
# (commit 44642c84). Visi agrākie pārskati tobrīd jau bija publicēti bez
# atļaujas rindas. Dažiem to nevar ierakstīt arī tagad: 2026-05-19 un 2026-05-22
# `scripts/approve_publish.py` atsaka satura pārbaudes dēļ, un to neapejam.
# Tāpēc subjekta datums PIRMS šīs dienas = publicēts arī bez rindas.
PUBLISH_APPROVAL_SINCE = "2026-08-18"


def published_brief_keys(db) -> set[str]:
    """`publish_approvals.subject_key` kopa; tukša, ja tabulas nav (vecs DB bez
    migrācijas nepublicē neko jaunu). Lieto renderis un `_weekly_day_links`."""
    if not db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='publish_approvals'"
    ).fetchone():
        return set()
    return {r[0] for r in db.execute("SELECT subject_key FROM publish_approvals")}


def is_brief_published(note_type: str | None, subject_date: str, approved: set[str]) -> bool:
    """Vai pārskats drīkst parādīties publiskajā renderā.

    Jā, ja tā lapas slugs (`brief_publish_key`) ir `approved` kopā vai subjekta
    datums ir pirms `PUBLISH_APPROVAL_SINCE`. Neatpazīts datums ("unknown")
    nav pirms robežas — tas krīt kā neapstiprināts.

    WHY (2026-10-26): renderis emitēja arī neapstiprinātu pārskatu, un tas
    bloķēja JEBKURU deploy. Ar lapu kokā deploy preflight (T15,
    `scripts/check_output.py --publish-gate-only`) atteica; bez lapas
    `index.html`, `blog.html`, iepriekšējās dienas prev/next un `sitemap.xml`
    joprojām uz to saitēja, un saišu pārbaude krita. Melnraksts tagad nenonāk
    kokā vispār; korektūrai — `python -m src.render --drafts`.
    `brief_images.approved` šeit apzināti NEskatāmies — tas ir cits fakts,
    un to joprojām pārbauda publish-gate.
    """
    if brief_publish_key(note_type, subject_date) in approved:
        return True
    return bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", subject_date or "")) and (
        subject_date < PUBLISH_APPROVAL_SINCE
    )


_NOT_ALREADY_BRIEFED_SQL = (
    "NOT EXISTS ("
    "SELECT 1 FROM context_notes _nb "
    "WHERE _nb.note_type = 'daily_brief' "
    f"AND _nb.topic = '{DAILY_BRIEF_TOPIC_PREFIX}' || date(c.stated_at) "
    "AND _nb.created_at > c.created_at)"
)
_BRIEF_DAY_WINDOW_SQL = (
    "(date(c.stated_at) = ? OR "
    "(date(c.created_at) = ? AND date(c.stated_at) >= date(?, '-7 days') "
    f"AND {_NOT_ALREADY_BRIEFED_SQL}))"
)

# Skeleta pozīciju predikāts = dienas logs BEZ neizskatītajām (2026-10-10).
# Agrāk @brief-writer tās izņēma ar roku. `IS NOT`, ne `<>`: lielākajai daļai
# pozīciju review_status IS NULL, un `<>` tās klusi izmestu (NULL <> x = NULL).
# Izlaistās skelets nosauc komentārā NEEDS_REVIEW IZLAISTAS (needs_review_day_claims).
# Nedēļas pārskata vaicājumi lieto to pašu nosacījumu (bez komentāra).
_NOT_NEEDS_REVIEW_SQL = "c.review_status IS NOT 'needs_review'"
_BRIEF_DAY_CLAIM_SQL = f"({_BRIEF_DAY_WINDOW_SQL} AND {_NOT_NEEDS_REVIEW_SQL})"


def needs_review_day_claims(db, day: str) -> list:
    """Dienas loga `needs_review` pozīcijas (id, name, topic), ko skelets izlaiž.

    Tas pats loga predikāts un tie paši filtri kā skeleta tabulām, tikai ar
    pretējo review_status nosacījumu — skelets + šis saraksts = visa diena.
    """
    return db.execute(
        f"""SELECT c.id, p.name, c.topic FROM claims c
            JOIN tracked_politicians p ON c.opponent_id = p.id
            WHERE {_BRIEF_DAY_WINDOW_SQL} AND c.claim_type = 'position'
              AND c.review_status = 'needs_review'
              AND p.relationship_type != 'inactive'
            ORDER BY c.id""",
        _brief_day_params(day),
    ).fetchall()


# A ROUTINE day is not a calendar day. The evening routine routinely finishes
# after midnight — 26 of 130 stored briefs did — so rows created at 00:16 LV
# belong to the work of the PREVIOUS day, not to the day the clock says.
# `brief_subject_date()` already settled this for the brief's own identity;
# these two tables never followed, and the gap was a SILENT omission: tensions
# #244/#245 and context notes #503/#504 (all written 00:1x–00:2x LV on 08-27)
# simply did not appear in the 2026-08-26 skeleton. No error, no empty table —
# `@brief-writer` restored them by hand only because the orchestrator warned it.
#
# 05:00 is measured, not chosen for roundness. The LV-hour histogram of every
# row these queries read has a gap exactly there, between the evening tail and
# the next morning's ingest block:
#
#     political_tensions  03:00–05:00 →   2 rows of 226  (04:47, 03:53)
#     context_notes       03:00–05:00 →   2 rows         (both 04:48, one session)
#     daily_brief         03:00–06:00 →   0 rows
#
# and both 03/04 clusters are themselves late-night sessions, i.e. on the
# correct side of the cut. The rule is TOTAL: every timestamp maps to exactly
# one routine day, so there is no double-counting and no gap — which is why it
# needs no `already_briefed`-style guard of the kind _BRIEF_DAY_CLAIM_SQL
# carries on the claims side.
#
# DELIBERATE LIMIT: this window governs only the two tables that have nothing
# BUT `created_at`. `claims` carry `stated_at` and stay on _BRIEF_DAY_CLAIM_SQL —
# widening that predicate is a different decision with a much larger blast
# radius, and nothing measured here argues for it.
ROUTINE_DAY_START_HOUR = 5


def routine_day_window(day: str) -> tuple[str, str]:
    """LV half-open window ``[start, end)`` for the routine day *day*.

    Both bounds are LV wall-clock strings. ``political_tensions.created_at`` is
    UTC, so compare it as ``datetime(created_at, 'localtime')``;
    ``context_notes.created_at`` is LV (``now_lv()``), so compare the raw value
    — adding that modifier to an LV column is the defect, not the repair
    (CLAUDE.md § Schema invariants).

    NB for whoever edits this docstring: ``tests/test_timestamp_timezone_gate.py``
    scans every string literal in ``src/``, docstrings included, so prose here is
    read as if it were a query. Write the modifier ONLY inside a real call on a
    real column, as the line above does — a made-up sample column, or the bare
    word on its own, is read as a defective query and turns the gate red. Same
    shape as the CHANGELOG anchor sample and the ``review_status`` marker word:
    prose that names a pattern trips the scanner that hunts it.
    """
    start_day = datetime.strptime(day, "%Y-%m-%d").date()
    end_day = start_day + timedelta(days=1)
    return (
        f"{start_day.isoformat()} {ROUTINE_DAY_START_HOUR:02d}:00:00",
        f"{end_day.isoformat()} {ROUTINE_DAY_START_HOUR:02d}:00:00",
    )


def current_routine_day(now: datetime | None = None) -> str:
    """Rutīnas diena, kurai pieder LV brīdis *now* (pēc noklusējuma — tagad).

    Pirms ROUTINE_DAY_START_HOUR tā ir VAKARDIENA: vakara rutīna, kas beidzas
    00:40, joprojām strādā pie vakardienas (sk. routine_day_window).
    """
    from src.db import now_lv_dt
    now = now or now_lv_dt()
    day = now.date() if now.hour >= ROUTINE_DAY_START_HOUR else now.date() - timedelta(days=1)
    return day.isoformat()


def routine_day_contradiction_count(db, day: str) -> int:
    """Apstiprināto (vai mantoto, bez ``confirmed`` vērtības) pretrunu skaits
    rutīnas dienā *day*; ``confirmed=0`` kandidāti netiek skaitīti.

    ``contradictions.detected_at`` ir LV (now_lv()), tāpēc salīdzina neapstrādātu
    vērtību pret routine_day_window(). Pretruna, kas atrasta 00:30 LV, pieder
    iepriekšējās dienas darbam — kalendāra dienas filtrs to klusi pārnesa uz
    nākamo dienu (2026-09-25 mērījumā 3 no 35 pretrunām).
    """
    return db.execute(
        "SELECT COUNT(*) FROM contradictions WHERE detected_at >= ? AND detected_at < ? "
        "AND COALESCE(confirmed, 1) = 1",
        routine_day_window(day),
    ).fetchone()[0]


def brief_day_politician_ids(db) -> dict[str, set[int]]:
    """{dienas pārskata datums: politiķi ar pozīciju vai publisku pretrunu tajā dienā}.

    Viens vaicājums visām dienām (renderis, 2026-11-03), nevis
    `_BRIEF_DAY_CLAIM_SQL` katram pārskatam. Abi pozīciju zari ir tā paša
    predikāta izvērsums, kur `?` = attiecīgais datums; atbilstību skeletam tur
    `tests/test_blog_politician_links.py`. Pretruna pieder rutīnas dienai
    (`routine_day_window`); `COALESCE(confirmed, 1) = 1` izslēdz kandidātus un
    atsauktās.
    """
    routine_shift = f"-{ROUTINE_DAY_START_HOUR} hours"
    out: dict[str, set[int]] = {}
    for day, pid in db.execute(
        f"""SELECT date(c.stated_at), c.opponent_id FROM claims c
            WHERE c.claim_type = 'position' AND {_NOT_NEEDS_REVIEW_SQL}
            UNION
            SELECT date(c.created_at), c.opponent_id FROM claims c
            WHERE c.claim_type = 'position' AND {_NOT_NEEDS_REVIEW_SQL}
              AND date(c.stated_at) >= date(c.created_at, '-7 days')
              AND {_NOT_ALREADY_BRIEFED_SQL}
            UNION
            SELECT date(detected_at, ?), opponent_id FROM contradictions
            WHERE COALESCE(confirmed, 1) = 1""",
        (routine_shift,),
    ):
        if day and pid is not None:
            out.setdefault(day, set()).add(pid)
    return out


def routine_week_contradiction_count(db, week_start: str, week_end: str) -> int:
    """Tas pats kā routine_day_contradiction_count(), bet rutīnas dienām
    *week_start*..*week_end* ieskaitot: logs no pirmās dienas 05:00 līdz dienas
    pēc pēdējās 05:00, tātad arī pēdējās dienas pēcpusnakts pretrunas."""
    return db.execute(
        "SELECT COUNT(*) FROM contradictions WHERE detected_at >= ? AND detected_at < ? "
        "AND COALESCE(confirmed, 1) = 1",
        (routine_day_window(week_start)[0], routine_day_window(week_end)[1]),
    ).fetchone()[0]


def _source_link(url: str | None, source_domain: str | None = None) -> str:
    """Render a claim's source URL as a `[domain](url)` markdown link, or '—' when
    absent. Shared by the per-topic positions table and the Pārējās tēmas table so
    the formatting stays in one place.

    The label is ``documents.source_domain`` when the caller supplies it — the URL
    host is not always the publisher (TVNET articles served from ``pmo.ee``;
    verdikts 41, 2026-09-06). The URL itself is never rewritten: it is part of
    ``store_claim()``'s idempotency triple. Falls back to the host (www. stripped)
    for rows with no document, e.g. Saeima vote claims. Truncated to 20 chars.
    """
    url = url or ""
    if not url:
        return "—"
    domain = (source_domain or url.split("//")[-1].split("/")[0]).replace("www.", "")
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
# Izņēmums: Pretrunu «Apraksts» ir iezīmēts izvilkums + saite uz pretrunas
# lapu, kur ir pilnais teksts (contradiction_excerpt, 2026-10-09).


_LEADING_ORDINAL = re.compile(r"^(\d+)\. ")
_BLOC_EXPLAINER_ANCHOR = re.compile(
    r"(## Koalīcija vs Opozīcija\n+(?:\|[^\n]*\n)+)"
)

# Viena rinda zem «Koalīcija vs Opozīcija» tabulas, kas paskaidro dalījumu
# (2026-09-05). Iemesls: r/atminaLV lasītājs pie 09-01 pārskata jautāja, kā
# tiek lemts, kas ir opozīcija un kas «bez Saeimas frakcijas» — intuitīvi
# «visi ārpus koalīcijas = opozīcija». Patiesības avots ir
# `parties.coalition_status` (CLAUDE.md Data Contract #10), un tabula to
# lasītājam nekur nepasaka. Rindu emitē skelets (dienas + nedēļas) UN
# renderis (`src/render/blog.py`) glabātajiem pārskatiem — tas pats
# render-laika princips kā `format_context_note`. `<span class="bloc-explainer">`
# ir enkurs idempotencei un stilam; teksts ir MŪSU vārdi, tāpēc LV vārti attiecas.
BLOC_TABLE_EXPLAINER = (
    '<span class="bloc-explainer">*Bloki pēc partijas statusa Saeimā: '
    "«Opozīcija» — partijas ar Saeimas frakciju, kas nav valdībā; "
    "«Bez Saeimas frakcijas» — partijas, kurām pašreizējā Saeimā frakcijas nav, "
    "arī tad, ja tām ir atsevišķi deputāti; «Bezpartejiskie» — politiķi bez "
    "partijas; «Neitrāli» — komentētāji, analītiķi un organizācijas, ne "
    "politiķi.*</span>"
)


def add_bloc_table_explainer(content: str) -> str:
    """Ieliek `BLOC_TABLE_EXPLAINER` tieši aiz «Koalīcija vs Opozīcija» tabulas.

    Idempotents: ja rinda jau ir (skelets to emitē pats), teksts paliek
    nemainīts; ja tabulas nav, arī nekas nemainās. Renderis to sauc uz katra
    glabātā pārskata, tāpēc arī pirms 2026-09-05 rakstītie pārskati iegūst
    paskaidrojumu bez DB maiņas.
    """
    if BLOC_TABLE_EXPLAINER in content:
        return content
    return _BLOC_EXPLAINER_ANCHOR.sub(
        lambda m: m.group(1) + "\n" + BLOC_TABLE_EXPLAINER + "\n", content, count=1
    )


def _h2_section(content: str, heading: str) -> str | None:
    """`## <heading>` sadaļas teksts līdz nākamajam `## ` (ne `###`), vai None."""
    m = re.search(rf"^## {re.escape(heading)}[ \t]*$", content or "", re.M)
    if m is None:
        return None
    nxt = re.search(r"^## ", content[m.end():], re.M)
    return content[m.end():m.end() + nxt.start()] if nxt else content[m.end():]


def count_brief_position_rows(content: str) -> int:
    """Pozīciju rindas, ko lasītājs REDZ «Galvenās tēmas» tabulās (arī «Pārējās tēmas»).

    Skaita tabulas rindas (`|…`) ar avota saiti uz http(s). Konteksta kastes
    `- [x.com](…)` saites nav tabulas rindas, tāpēc neskaitās. Iemesls
    (2026-10-07): DIENAS STATS marķieris ir skeleta brīža skaitlis — kad
    brief-writer ar roku izņem NEEDS_REVIEW rindas, marķieris paliek vecs
    (#682: marķieris 79, tabulās 72). 0 = sadaļas nav (vecs pārskats).
    """
    section = _h2_section(content, "Galvenās tēmas")
    if section is None:
        return 0
    return sum(
        1 for line in section.splitlines()
        if line.lstrip().startswith("|") and re.search(r"\]\(https?://", line)
    )


def bloc_table_position_sum(content: str) -> int | None:
    """«Koalīcija vs Opozīcija» tabulas kolonnas «Pozīcijas» summa, vai None.

    None, ja tabulas nav vai kādu šūnu nevar nolasīt kā skaitli — tad vārtiem
    nav ar ko salīdzināt, nevis „sakrīt".
    """
    section = _h2_section(content, "Koalīcija vs Opozīcija")
    if section is None:
        return None
    rows = [
        [c.strip() for c in line.strip().strip("|").split("|")]
        for line in section.splitlines() if line.lstrip().startswith("|")
    ]
    if len(rows) < 3 or "Pozīcijas" not in rows[0]:
        return None
    col = rows[0].index("Pozīcijas")
    total = 0
    for row in rows[2:]:  # [0] galvene, [1] |---| atdalītājs
        if col >= len(row) or not row[col].isdigit():
            return None
        total += int(row[col])
    return total


_TENDENCE_PREFIX = re.compile(
    r"^Tendence \((?P<date>\d{4}-\d{2}-\d{2}),\s*(?P<title>[^)]+)\):\s*",
)


def format_context_note(content: str) -> str:
    """Sagatavo konteksta piezīmes tekstu Markdown renderim (2026-09-05).

    Divas lietas, abas tikai izkārtojums — vārdus nemaina:

    1. **Tukšas rindas ap ``- `` sarakstu.** Piezīmes raksta ievadu, tad
       ``- `` rindas, tad noslēguma teikumu bez tukšām rindām starp tiem.
       Python-Markdown bez tukšas rindas saraksta rindas uzskata par
       rindkopas turpinājumu (un noslēguma teikumu — par pēdējā punkta
       turpinājumu), tāpēc publiskajā lapā kastīte lasījās kā viens blīvs
       bloks. Šeit pirms pirmā un pēc pēdējā saraksta punkta ieliek tukšu
       rindu.
    2. **``Tendence (YYYY-MM-DD, virsraksts):`` prefikss** kļūst par kastes
       pirmo rindkopu treknrakstā ar datumu, nevis par ievada teikuma sākumu.

    Piezīme bez prefiksa un bez saraksta atgriežas nemainīta.
    Vārti: ``tests/test_brief_context_note_layout.py``.
    """
    text = (content or "").strip()
    m = _TENDENCE_PREFIX.match(text)
    heading = None
    if m:
        title = m.group("title").strip()
        # Lielais burts pirmajam BURTAM — virsraksts var sākties ar «.
        # Ja pirms burta ir cipars («2027. gada …»), burtu nemaina.
        i = next((k for k, ch in enumerate(title) if ch.isalnum()), 0)
        if title[i:i + 1].isalpha():
            title = title[:i] + title[i:i + 1].upper() + title[i + 1:]
        y, mo, d = m.group("date").split("-")
        heading = f"**{title}** · {d}.{mo}.{y}"
        text = text[m.end():]

    out: list[str] = []
    prev_list = False
    for line in text.split("\n"):
        is_list = line.startswith("- ")
        if is_list and not prev_list and out and out[-1].strip():
            out.append("")
        if not is_list and prev_list and line.strip():
            out.append("")
        # Rindkopa, kas sākas ar «21. augusta …», Markdown-am ir numurēts
        # saraksts (feedback: brief markdown ol trap) — aizsargā punktu.
        starts_paragraph = not out or not out[-1].strip()
        if starts_paragraph and _LEADING_ORDINAL.match(line):
            line = _LEADING_ORDINAL.sub(r"\1\\. ", line, count=1)
        out.append(line)
        prev_list = is_list
    body = "\n".join(out)
    return f"{heading}\n\n{body}" if heading else body


def generate_daily_brief(db_path: str = None, date: str = None) -> str:
    """Generate a neutral daily brief in markdown. No campaign framing."""
    date = date or now_lv_dt().strftime("%Y-%m-%d")
    db = get_db(db_path)

    # Per-platform, never by subtraction: `doc_count - web_count` dumped every
    # non-web platform into the Twitter/X bucket — the 08-03 brief reported
    # "561 Twitter/X" where 24 were vestnesis (BACKLOG 2026-08-04). Unknown
    # platforms surface as `citi` instead of inflating a named bucket.
    platform_counts = dict(
        db.execute(
            "SELECT platform, COUNT(*) FROM documents"
            " WHERE scraped_at >= ? AND scraped_at < ? GROUP BY platform",
            routine_day_window(date),
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
    contradiction_count = routine_day_contradiction_count(db, date)

    # Active politicians: position-only so the leaderboard reflects who
    # actually spoke rather than who happened to be present for a bulk
    # vote import.
    #
    # The tie-break chain is load-bearing, not cosmetic. On a normal day most
    # politicians sit at cnt=1 (2026-08-07: 14 of 15 tied), so `cnt DESC` alone
    # left the cut to SQLite's `GROUP BY p.id` order — i.e. seeding recency.
    # That is not neutral: recently seeded cohorts cluster at high ids, and on
    # 2026-08-07 one party took 3 of the 7 rows on 4 of 18 positions while the
    # coalition took 2 rows on 8 of 18. Alphabetical fixed that but made the cut
    # blind to meaning: on 2026-09-12 the day's lead speaker (salience 0.85) was
    # cut while six alphabetically earlier cnt=1 politicians were listed, and
    # 09-13 repeated it (`@quality-reviewer` both days). So among ties the
    # politician's MAX(salience) decides first; `p.name` remains the final,
    # party-uncorrelated stable cut for exact ties.
    active = db.execute(f"""
        SELECT p.name, p.party, COUNT(*) as cnt,
            GROUP_CONCAT(DISTINCT c.topic) as topics
        FROM claims c
        JOIN tracked_politicians p ON c.opponent_id = p.id
        WHERE {_BRIEF_DAY_CLAIM_SQL}
          AND c.claim_type = 'position'
          AND p.relationship_type NOT IN ('journalist','influencer','neutral','inactive','organization')
        GROUP BY p.id ORDER BY cnt DESC, MAX(c.salience) DESC, p.name ASC LIMIT 7
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
            -- Routine-day window, not calendar day — see routine_day_window().
            SELECT topic, COUNT(*) as t_cnt FROM political_tensions
            WHERE datetime(created_at, 'localtime') >= ?
              AND datetime(created_at, 'localtime') <  ? GROUP BY topic
        ) tens ON tens.topic = c.topic
        LEFT JOIN (
            SELECT c2.topic, COUNT(*) as c_cnt FROM contradictions con
            JOIN claims c2 ON con.claim_old_id = c2.id OR con.claim_new_id = c2.id
            -- detected_at ir LV — rutīnas dienas logs, bez 'localtime'.
            WHERE con.detected_at >= ? AND con.detected_at < ?
              AND COALESCE(con.confirmed, 1) = 1
            GROUP BY c2.topic
        ) cont ON cont.topic = c.topic
        WHERE {_BRIEF_DAY_CLAIM_SQL} AND c.claim_type = 'position'
          AND p.relationship_type != 'inactive'
        GROUP BY c.topic ORDER BY interest_score DESC
    """, (*routine_day_window(date), *routine_day_window(date),
          *_brief_day_params(date))).fetchall()

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
        -- Routine-day window, not calendar day — see routine_day_window().
        WHERE datetime(t.created_at, 'localtime') >= ?
          AND datetime(t.created_at, 'localtime') <  ?
        GROUP BY t.topic ORDER BY cnt DESC LIMIT 3
    """, routine_day_window(date)).fetchall()

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
    from src.render._common.filters import _lv_plural

    plural_pos = _lv_plural(position_count, "pozīcija", "pozīcijas")
    plural_pret = _lv_plural(contradiction_count, "pretruna", "pretrunas")
    # Pozīciju skaits = dienas-loga politiķu pozīcijas (=emitētās ###-tabulas).
    # Ja dienā ir arī organizāciju pozīcijas, uzrādām sadalījumu skaidri
    # ('N pozīcijas (M politiķu + K org)'), lai nav klusa neatbilstība starp
    # STATS skaitli un emitētajām politiķu tabulām (Fix 2). doc_count mēra
    # rutīnas dienas logs (05:00 LV) visiem dokumentiem; web/X sadalījums pēc platform.
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
    skipped = needs_review_day_claims(db, date)
    skipped_list = "".join(
        (" — " if i == 0 else ", ") + f"#{r['id']} {r['name']} ({r['topic']})"
        for i, r in enumerate(skipped)
    )
    lines.append(f"<!-- NEEDS_REVIEW IZLAISTAS: {len(skipped)}{skipped_list} -->")

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
        -- created_at is LV (now_lv()) — compare raw, NEVER with 'localtime'.
        -- Routine-day window, not calendar day — see routine_day_window().
        WHERE note_type = 'context'
          AND created_at >= ? AND created_at < ?
        ORDER BY created_at DESC
    """, routine_day_window(date)).fetchall()

    # Skip raw JSON marker rows (e.g. synthesis_featured_image hints stored as
    # {"kind": "...", ...}) — they are scaffolding for a synthesis-card render
    # pipeline that doesn't yet exist, so dumping the JSON into a context-box
    # leaks structured data into the public HTML.
    context_notes = [
        cn for cn in context_notes
        if not (cn["content"] or "").lstrip().startswith("{")
    ]

    rendered_notes: set[int] = set()
    if by_topic:
        lines.append("\n## Galvenās tēmas\n")
        for t in full_topics:
            pos_word = _lv_plural(t["cnt"], "pozīcija", "pozīcijas")
            lines.append(f"### {t['topic']} ({t['cnt']} {pos_word})\n")

            # Embed EVERY matching context note, each once (2026-09-29: a
            # `break` here dropped the 2nd same-topic note — #659, also #377/#509).
            for idx, cn in enumerate(context_notes):
                if idx in rendered_notes:
                    continue
                if cn["topic"] and cn["topic"].lower() in t["topic"].lower() or \
                   t["topic"].lower() in (cn["topic"] or "").lower():
                    lines.append('<div class="context-box" markdown="1">')
                    lines.append('<div class="context-label">Konteksts</div>\n')
                    lines.append(format_context_note(cn["content"]))
                    lines.append('</div>\n')
                    rendered_notes.add(idx)

            # Claims with source URLs — positions only, excluding
            # audience accounts. Vote rows carry procedural stances
            # that make no sense in a rhetorical brief.
            samples = db.execute(f"""
                SELECT p.name, p.party, c.stance, c.source_url,
                       d.source_domain AS doc_source_domain FROM claims c
                JOIN tracked_politicians p ON c.opponent_id = p.id
                LEFT JOIN documents d ON c.document_id = d.id
                WHERE {_BRIEF_DAY_CLAIM_SQL} AND c.topic = ?
                  AND c.claim_type = 'position'
                  AND p.relationship_type != 'inactive'
                ORDER BY c.id
            """, (*_brief_day_params(date), t["topic"])).fetchall()

            if samples:
                lines.append("| Politiķis | Partija | Pozīcija | Avots |")
                lines.append("|-----------|---------|----------|-------|")
                for s in samples:
                    link = _source_link(s["source_url"], s["doc_source_domain"])
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
                SELECT p.name, p.party, c.topic, c.stance, c.source_url,
                       d.source_domain AS doc_source_domain
                FROM claims c
                JOIN tracked_politicians p ON c.opponent_id = p.id
                LEFT JOIN documents d ON c.document_id = d.id
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
            pos_word = _lv_plural(n_rows, "pozīcija", "pozīcijas")
            tema_word = _lv_plural(m_topics, "tēmā", "tēmās")
            lines.append(
                f"\n### Pārējās tēmas ({n_rows} {pos_word} {m_topics} {tema_word})\n"
            )
            lines.append("| Politiķis | Partija | Tēma | Pozīcija | Avots |")
            lines.append("|-----------|---------|------|----------|-------|")
            for r in rest_rows:
                link = _source_link(r["source_url"], r["doc_source_domain"])
                stance_full = (r["stance"] or "").strip()
                lines.append(
                    f"| {r['name']} | {r['party'] or ''} | {r['topic']} | "
                    f"{stance_full} | {link} |"
                )
            lines.append("")

    # Add remaining context notes that no FULL ### section rendered (T7): a
    # Pārējās-table topic's context note flows through this path unchanged.
    unmatched_context = [cn for idx, cn in enumerate(context_notes)
                         if idx not in rendered_notes]
    # Tā pati klase, kas spriedzēm zemāk: 0 konteksta piezīmju ir GAIDĀMS
    # iznākums, bet neatšķirams no „atlase pēc date(created_at) tās nesasniedza"
    # (2026-08-26: piezīmes #503/#504 rakstītas 00:2x LV un skeletā neparādījās).
    # Saucēju emitē vienmēr, arī tad, kad kaut kas tika ievilkts — skaitlis bez
    # saucēja neļauj pateikt, vai izlaišana notika.
    lines.append(
        f"\n<!-- KONTEKSTA PIEZĪMES: {len(context_notes)} rindas rutīnas dienas logā "
        f"[{routine_day_window(date)[0]} -> {routine_day_window(date)[1]}) LV "
        f"(tēmās iekļautas {len(rendered_notes)}, "
        f"Papildu kontekstā {len(unmatched_context)}). Logs sākas 05:00, tāpēc "
        "pēcpusnakts rindas JAU ir ieskaitītas šajā dienā. -->"
    )
    if unmatched_context:
        lines.append("\n## Papildu konteksts\n")
        for cn in unmatched_context:
            lines.append('<div class="context-box" markdown="1">')
            lines.append(f'<div class="context-label">{cn["topic"] or "Konteksts"}</div>\n')
            lines.append(format_context_note(cn["content"]))
            lines.append('</div>\n')

    # Coalition vs opposition split — renderē kā kompaktu tabulu.
    # Pārveidots 2026-04-19 no 3 paragrāfiem uz 5-kolonnu tabulu, lai padarītu
    # skenējamu. Aģents ZEM tabulas pievieno 1-2 teikumu sintēzi.
    all_day_rows = db.execute(f"""
        SELECT p.id AS pid, p.name, p.party, c.topic, c.stance, p.relationship_type
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
        lines.append(BLOC_TABLE_EXPLAINER)
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
        -- Routine-day window, not calendar day — see routine_day_window().
        WHERE datetime(t.created_at, 'localtime') >= ?
          AND datetime(t.created_at, 'localtime') <  ?
        ORDER BY t.id
    """, routine_day_window(date)).fetchall()
    # Nulle ir jāREDZ, ne jāsecina no sadaļas trūkuma. Kad spriedžu nav, skelets
    # līdz 2026-08-27 vienkārši neemitēja `## Spriedzes` — nav tabulas, nav
    # nulles rindas, nav brīdinājuma —, tāpēc aģents nevarēja atšķirt „šodien
    # spriedžu nebija" no „atlases atslēga tās neatrada". 2026-08-26 tā bija
    # otrā: spriedzes #244/#245 tapa 00:16 LV (t.i. ar nākamās dienas
    # `created_at`), sadaļas skeletā nebija, un `@brief-writer` tās ielika ar
    # roku TIKAI tāpēc, ka orkestrators eksplicīti brīdināja. Komentārs, ne
    # tukša tabula: publiskajā lapā tukša „Spriedzes" tabula būtu troksnis, bet
    # aģents skeleta markdown lasa neapstrādātu (sk. DIENAS STATS formu augstāk).
    if not tension_rows:
        lines.append(
            f"\n<!-- SPRIEDZES: 0 rindu rutīnas dienas logā "
            f"[{routine_day_window(date)[0]} -> {routine_day_window(date)[1]}) LV. "
            "Nulle ir iznākums, ne klusēšana. Logs sākas 05:00, tāpēc pēcpusnakts "
            "rindas JAU ir ieskaitītas šajā dienā — ja te ir 0, spriedžu tiešām nebija. -->"
        )
    # Publisher label = documents.source_domain, the positions tables' rule
    # (verdikts 41: pmo.ee → tvnet.lv). Tensions carry no document_id, so the
    # lookup goes by URL; a URL with no document falls back to its host.
    tension_urls = sorted({t["source_url"] for t in tension_rows if t["source_url"]})
    tension_domains: dict[str, str] = {}
    if tension_urls:
        marks = ",".join("?" * len(tension_urls))
        for row in db.execute(
            f"SELECT source_url, source_domain FROM documents "
            f"WHERE source_url IN ({marks}) AND source_domain IS NOT NULL",
            tension_urls,
        ).fetchall():
            tension_domains.setdefault(row["source_url"], row["source_domain"])
    if tension_rows:
        lines.append("\n## Spriedzes\n")
        lines.append("| Tips | Avots | Mērķis | Tēma | Apraksts | Saite |")
        lines.append("|------|-------|--------|------|----------|-------|")
        for t in tension_rows:
            link = _source_link(t["source_url"], tension_domains.get(t["source_url"]))
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
        WHERE c.detected_at >= ? AND c.detected_at < ?
          AND COALESCE(c.confirmed, 1) = 1
        ORDER BY c.id
    """, routine_day_window(date)).fetchall()

    if contra_rows:
        lines.append("\n## Pretrunas\n")
        lines.append("| Politiķis | Partija | Tēma | Veids | Apraksts | Avoti |")
        lines.append("|-----------|---------|------|-------|----------|-------|")
        for r in contra_rows:
            severity_lv = _SEVERITY_LV.get(r["severity"] or "", "pretruna")
            # Apraksts — ≤50 vārdu izvilkums + saite uz pretrunas lapu
            # (2026-10-09; pilnais teksts ir lapā, sk. contradiction_excerpt).
            summary = contradiction_excerpt(r["summary"], r["id"])

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


CONTRA_EXCERPT_WORDS = 50


def contradiction_excerpt_text(summary: str | None,
                               max_words: int = CONTRA_EXCERPT_WORDS) -> str:
    """The plain-text part of :func:`contradiction_excerpt`, without the link.

    Also the collapsed-row text on ``pretrunas.html`` (a ``<button>``, where a
    link cannot live), so the register and the briefs preview the same words.
    """
    text = (summary or "").split("\n\n", 1)[0]
    text = text.split("[Konteksts:", 1)[0]
    text = " ".join(text.replace("|", "/").split())
    words = text.split(" ") if text else []
    if len(words) > max_words:
        text = " ".join(words[:max_words]).rstrip(",;:—-").rstrip() + "…"
    return text


def contradiction_excerpt(summary: str | None, contra_id: int,
                          max_words: int = CONTRA_EXCERPT_WORDS) -> str:
    """The ``Apraksts`` cell of the daily ``## Pretrunas`` table (the weekly
    one left with the «Nedēļas stāsti» skeleton, 2026-11-01).

    First paragraph of ``contradictions.summary``, cut before ``[Konteksts:``,
    whitespace-collapsed (a newline splits a markdown table row), ``|`` replaced
    (a raw pipe opens a new cell), capped at ``max_words`` on a word boundary with
    «…» only when cut, and always followed by a root-relative link to the full
    contradiction page. Contradiction #53 put 213 words into one cell.

    The 2026-06-10 no-truncation rule (see the note above ``_LEADING_ORDINAL``)
    was made when the cell was the only copy of the text and was cut mid-sentence
    without a marker. Here the cell is a preview: the cut is marked and the full
    text is one click away (weekly since 2026-09-27, daily since 2026-10-09).
    """
    text = contradiction_excerpt_text(summary, max_words)
    link = f"[pilnā pretruna](/pretrunas/{contra_id}.html)"
    return f"{text} {link}" if text else link


_FORWARD_LOOK_HEADING = "## Skats uz priekšu"
# Jaunā forma (2026-11-01) sauc to pašu sadaļu «Ko gaidīt»; abas jālasa, citādi
# nedēļa pēc pirmā jaunā pārskata paliek bez followup kandidātiem.
_FORWARD_LOOK_HEADINGS = (_FORWARD_LOOK_HEADING, "## Ko gaidīt")


def _previous_forward_look(db, week_start: str) -> list[str]:
    """Bullet lines of the PREVIOUS weekly brief's «Skats uz priekšu» section.

    The previous brief is found by its SUBJECT identity (the topic names the week
    it covers), never by ``created_at`` — a weekly brief is often stored after
    midnight, on the next week's first day. Returns [] when there is no such
    brief or no such section. ``-->`` is defused so a bullet cannot close the
    HTML comment it is quoted in.
    """
    start = datetime.strptime(week_start, "%Y-%m-%d")
    topic = (f"nedēļas analīze {(start - timedelta(days=7)).strftime('%Y-%m-%d')} "
             f"līdz {(start - timedelta(days=1)).strftime('%Y-%m-%d')}")
    row = db.execute(
        "SELECT content FROM context_notes WHERE note_type = 'weekly_brief' "
        "AND topic = ? ORDER BY id DESC LIMIT 1", (topic,)
    ).fetchone()
    if not row or not row[0]:
        return []
    bullets: list[str] = []
    inside = False
    for line in row[0].splitlines():
        if line.strip() in _FORWARD_LOOK_HEADINGS:
            inside = True
            continue
        if not inside:
            continue
        if line.startswith("## ") or line.startswith("**Dienu pārskati:**"):
            break
        if line.lstrip().startswith(("- ", "* ")):
            bullets.append(line.strip().replace("-->", "—>"))
    return bullets


SURGE_MIN_POSITIONS = 8
SURGE_MIN_RATIO = 2.0
NEW_VOICE_LOOKBACK_DAYS = 30
# «atkārtojas»: tēma vadīja ≥3 dienas. Ar ≥2 atzīmi 2026-10-26…11-01 nesa 29 no
# 35 punktiem (plaša tēma valdības veidošanas laikā vada katru dienu).
LEAD_REPEAT_MIN_DAYS = 3
_STORY_KIND_ORDER = ("contradiction", "vote_split", "daily_lead", "topic_surge",
                     "tension_pair", "followup", "new_voice")
_AUDIENCE_REL_TYPES = ("journalist", "influencer", "neutral", "inactive", "organization")


def _cand(kind: str, fact: str, *, topic=None, days=(), claim_ids=(), vote_ids=(),
          contradiction_ids=(), repeated=False) -> dict:
    """Viens nedēļas stāsta kandidāts; visiem veidiem viena forma."""
    return {
        "kind": kind,
        "fact": " ".join(str(fact).split()),
        "topic": topic,
        "days": sorted({d for d in days if d}),
        "claim_ids": list(claim_ids),
        "vote_ids": list(vote_ids),
        "contradiction_ids": list(contradiction_ids),
        "repeated": repeated,
    }


def _ids(csv: str | None) -> list[int]:
    return [int(x) for x in (csv or "").split(",") if x]


def _cands_contradiction(db, week_start, week_end):
    lo, hi = routine_day_window(week_start)[0], routine_day_window(week_end)[1]
    out = []
    for r in db.execute(
        "SELECT c.id, c.topic, c.severity, c.headline, c.summary, c.claim_old_id, "
        "c.claim_new_id, c.detected_at, p.name, p.party FROM contradictions c "
        "JOIN tracked_politicians p ON p.id = c.opponent_id "
        "WHERE c.detected_at >= ? AND c.detected_at < ? "
        "AND COALESCE(c.confirmed, 1) = 1 AND c.withdrawn_at IS NULL ORDER BY c.id",
        (lo, hi),
    ):
        label = _SEVERITY_LV.get(r["severity"] or "", "pretruna")
        what = r["headline"] or contradiction_excerpt_text(r["summary"], 25)
        out.append(_cand(
            "contradiction",
            f"{r['name']} ({r['party'] or '—'}), {r['topic']}: {label} — {what}",
            topic=r["topic"], days=[str(r["detected_at"])[:10]],
            claim_ids=[i for i in (r["claim_old_id"], r["claim_new_id"]) if i],
            contradiction_ids=[r["id"]]))
    return out


def _cands_topic_surge(db, week_start, week_end):
    from src.render._common.filters import _lv_plural
    prior_start = (datetime.strptime(week_start, "%Y-%m-%d") - timedelta(days=28)).strftime("%Y-%m-%d")
    prior_end = (datetime.strptime(week_start, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
    prior = {r["topic"]: r["n"] for r in db.execute(
        "SELECT c.topic, COUNT(*) AS n FROM claims c WHERE date(c.stated_at) BETWEEN ? AND ? "
        f"AND c.claim_type = 'position' AND {_NOT_NEEDS_REVIEW_SQL} GROUP BY c.topic",
        (prior_start, prior_end))}
    out = []
    for r in db.execute(
        "SELECT c.topic, COUNT(*) AS n, GROUP_CONCAT(c.id) AS ids, "
        "GROUP_CONCAT(DISTINCT date(c.stated_at)) AS days FROM claims c "
        "WHERE date(c.stated_at) BETWEEN ? AND ? "
        f"AND c.claim_type = 'position' AND {_NOT_NEEDS_REVIEW_SQL} "
        "GROUP BY c.topic ORDER BY n DESC, c.topic", (week_start, week_end)):
        avg = prior.get(r["topic"], 0) / 4
        if r["n"] < SURGE_MIN_POSITIONS or (avg and r["n"] < SURGE_MIN_RATIO * avg):
            continue
        base = (f"4 iepriekšējās nedēļās vidēji {avg:.1f}".replace(".", ",") if avg
                else "4 iepriekšējās nedēļās nebija")
        out.append(_cand("topic_surge", f"{r['topic']}: {r['n']} {_lv_plural(r['n'], 'pozīcija', 'pozīcijas')}; {base}",
                         topic=r["topic"], days=(r["days"] or "").split(","),
                         claim_ids=sorted(_ids(r["ids"]))))
    return out


def _cands_tension_pair(db, week_start, week_end):
    from src.render._common.filters import _lv_plural
    # political_tensions.created_at ir UTC, robežas — LV laikā (T17).
    lo, hi = routine_day_window(week_start)[0], routine_day_window(week_end)[1]
    out = []
    for r in db.execute(
        "SELECT t.source_pid, t.target_pid, s.name AS src, g.name AS tgt, COUNT(*) AS n, "
        "GROUP_CONCAT(DISTINCT t.topic) AS topics, "
        "GROUP_CONCAT(DISTINCT date(datetime(t.created_at, 'localtime'))) AS days "
        "FROM political_tensions t "
        "JOIN tracked_politicians s ON s.id = t.source_pid "
        "JOIN tracked_politicians g ON g.id = t.target_pid "
        "WHERE datetime(t.created_at, 'localtime') >= ? AND datetime(t.created_at, 'localtime') < ? "
        "GROUP BY t.source_pid, t.target_pid HAVING COUNT(*) >= 2 ORDER BY n DESC, src, tgt",
        (lo, hi)):
        topics = (r["topics"] or "").split(",")
        out.append(_cand("tension_pair",
                         f"{r['src']} → {r['tgt']}: {r['n']} {_lv_plural(r['n'], 'spriedze', 'spriedzes')} "
                         f"({', '.join(topics)})",
                         topic=topics[0] if len(topics) == 1 else None,
                         days=(r["days"] or "").split(",")))
    return out


def _cands_new_voice(db, week_start, week_end):
    from src.render._common.filters import _lv_plural
    lookback = (datetime.strptime(week_start, "%Y-%m-%d")
                - timedelta(days=NEW_VOICE_LOOKBACK_DAYS)).strftime("%Y-%m-%d")
    marks = ",".join("?" * len(_AUDIENCE_REL_TYPES))
    out = []
    for r in db.execute(
        f"""SELECT p.id, p.name, p.party, COUNT(*) AS n, GROUP_CONCAT(c.id) AS ids,
                   GROUP_CONCAT(DISTINCT date(c.stated_at)) AS days
            FROM claims c JOIN tracked_politicians p ON p.id = c.opponent_id
            WHERE date(c.stated_at) BETWEEN ? AND ? AND c.claim_type = 'position'
              AND {_NOT_NEEDS_REVIEW_SQL}
              AND COALESCE(p.relationship_type, '') NOT IN ({marks})
              AND NOT EXISTS (SELECT 1 FROM claims c2 WHERE c2.opponent_id = p.id
                    AND c2.claim_type = 'position' AND date(c2.stated_at) >= ?
                    AND date(c2.stated_at) < ?)
            GROUP BY p.id ORDER BY n DESC, p.name""",
        (week_start, week_end, *_AUDIENCE_REL_TYPES, lookback, week_start)):
        out.append(_cand("new_voice",
                         f"{r['name']} ({r['party'] or '—'}): {r['n']} "
                         f"{_lv_plural(r['n'], 'pozīcija', 'pozīcijas')}; iepriekšējās "
                         f"{NEW_VOICE_LOOKBACK_DAYS} dienās 0",
                         days=(r["days"] or "").split(","), claim_ids=sorted(_ids(r["ids"]))))
    return out


_LEAD_RE = re.compile(r"^\s*[-*]\s+\*\*(.+?)\*\*")
_MD_LINK_URL_RE = re.compile(r"\]\((https?://[^)\s]+)\)")


def _galvenais_section(content: str) -> list[str]:
    lines, inside = [], False
    for line in (content or "").splitlines():
        if line.strip() == "## Galvenais":
            inside = True
            continue
        if inside and line.startswith("## "):
            break
        if inside:
            lines.append(line)
    return lines


def _cands_daily_lead(db, week_start, week_end):
    """Katrs nedēļas dienas pārskata «## Galvenais» punkts ``- **…**`` (jaunākais
    pārskats katrai subjekta dienai). Tēma = biežākā tēma pozīcijām, kuru
    ``source_url`` ir punkta saitēs (vienādos — alfabētiski pirmā); bez
    atbilstības ``topic=None``. ``repeated`` — tēma vadīja ≥LEAD_REPEAT_MIN_DAYS dažādās dienās."""
    latest: dict[str, tuple[int, str]] = {}
    for r in db.execute("SELECT id, topic, content, created_at FROM context_notes "
                        "WHERE note_type = 'daily_brief' ORDER BY id"):
        day = brief_subject_date(r["topic"], r["content"], r["created_at"])
        if day and week_start <= day <= week_end:
            latest[day] = (r["id"], r["content"])
    leads = []  # (day, fact, topic, claim_ids)
    for day in sorted(latest):
        for line in _galvenais_section(latest[day][1]):
            m = _LEAD_RE.match(line)
            if not m:
                continue
            urls = _MD_LINK_URL_RE.findall(line)
            rows = db.execute(
                f"SELECT c.id, c.topic FROM claims c WHERE c.source_url IN ({','.join('?' * len(urls))}) "
                f"AND c.claim_type = 'position' AND {_NOT_NEEDS_REVIEW_SQL} ORDER BY c.id",
                urls).fetchall() if urls else []
            counts: dict[str, int] = {}
            for r in rows:
                counts[r["topic"]] = counts.get(r["topic"], 0) + 1
            topic = min(counts, key=lambda t: (-counts[t], t)) if counts else None
            leads.append((day, m.group(1).strip(), topic, [r["id"] for r in rows]))
    topic_days: dict[str, set] = {}
    for day, _fact, topic, _cids in leads:
        if topic:
            topic_days.setdefault(topic, set()).add(day)
    return [_cand("daily_lead", fact, topic=topic, days=[day], claim_ids=cids,
                  repeated=bool(topic) and len(topic_days[topic]) >= LEAD_REPEAT_MIN_DAYS)
            for day, fact, topic, cids in leads]


def weekly_story_candidates(db, week_start: str) -> list[dict]:
    """Nedēļas stāstu kandidāti aģentam (spec 2026-11-01 § 2). Tīra lasīšana;
    savienojumu neaizver. NEEDS_REVIEW pozīcijas izslēgtas visos veidos.
    Secība: `_STORY_KIND_ORDER`, veida iekšienē — kā katrs palīgs sakārtoja."""
    week_end = (datetime.strptime(week_start, "%Y-%m-%d") + timedelta(days=6)).strftime("%Y-%m-%d")
    cands: list[dict] = []
    cands += _cands_contradiction(db, week_start, week_end)
    cands += _cands_vote_split(db, week_start, week_end)
    cands += _cands_daily_lead(db, week_start, week_end)
    cands += _cands_topic_surge(db, week_start, week_end)
    cands += _cands_tension_pair(db, week_start, week_end)
    cands += [_cand("followup", b) for b in _previous_forward_look(db, week_start)]
    cands += _cands_new_voice(db, week_start, week_end)
    order = {k: i for i, k in enumerate(_STORY_KIND_ORDER)}
    return sorted(cands, key=lambda c: order[c["kind"]])  # sorted() ir stabils


_NO_FACTION_LABEL = "ārpusfrakciju"
_BALLOT_VALUES = ("Par", "Pret", "Atturas", "Nebalsoja")


def _week_vote_data(db, week_start: str, week_end: str):
    """Nedēļas balsojumi un to frakciju sadalījums — viens avots gan
    ``weekly_vote_breakdown()``, gan ``vote_split`` kandidātiem, lai abi nekad
    neatšķiras. Atgriež ``(votes, indiv)``: balsojumi bez klātbūtnes
    reģistrācijām (pēc datuma/laika/id) un ``{vote_id: {frakcija: {"Par",
    "Pret", "Atturas", "Nebalsoja", "cits": int}}}``; tukša frakcija →
    ``_NO_FACTION_LABEL``. Bez Saeimas tabulām → ``([], {})``."""
    tables = {r[0] for r in db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name IN ('saeima_votes', 'saeima_individual_votes')")}
    votes = []
    indiv: dict[int, dict[str, dict[str, int]]] = {}
    if tables != {"saeima_votes", "saeima_individual_votes"}:
        return votes, indiv
    from src.saeima.votes import _REGISTRATION_MOTIF_PREFIX
    votes = db.execute(
        "SELECT id, vote_date, vote_time, motif, result, total_par, total_pret, "
        "total_atturas, total_nebalso, document_nr, url FROM saeima_votes "
        "WHERE date(vote_date) BETWEEN ? AND ? AND COALESCE(motif, '') NOT LIKE ? "
        "ORDER BY vote_date, vote_time, id",
        (week_start, week_end, _REGISTRATION_MOTIF_PREFIX + "%"),
    ).fetchall()
    ids = [v["id"] for v in votes]
    if ids:
        marks = ",".join("?" * len(ids))
        for r in db.execute(
            "SELECT vote_id, NULLIF(TRIM(faction), '') AS faction, vote, "
            f"COUNT(*) AS n FROM saeima_individual_votes WHERE vote_id IN ({marks}) "
            "GROUP BY vote_id, NULLIF(TRIM(faction), ''), vote", ids,
        ):
            fac = r["faction"] or _NO_FACTION_LABEL
            bucket = indiv.setdefault(r["vote_id"], {}).setdefault(
                fac, {"Par": 0, "Pret": 0, "Atturas": 0, "Nebalsoja": 0, "cits": 0})
            key = r["vote"] if r["vote"] in _BALLOT_VALUES else "cits"
            bucket[key] += r["n"]
    return votes, indiv


def _vote_mismatch(v, facs: dict) -> list[str]:
    """Σ individuālo Par/Pret/Atturas pret ``saeima_votes`` kopsummām; tukšs = sakrīt."""
    diffs = []
    for field, total_col in (("Par", "total_par"), ("Pret", "total_pret"),
                             ("Atturas", "total_atturas")):
        got = sum(c[field] for c in facs.values())
        want = v[total_col] or 0
        if got != want:
            diffs.append(f"individuālie {field} {got} ≠ kopā {want}")
    return diffs


SPLIT_MIN_MINORITY = 2
_SPLIT_BALLOTS = ("Par", "Pret", "Atturas")


def _majority(c: dict) -> tuple[str, int, int]:
    """(vairākuma balsojums, tā skaits, otrā lielākā skaits) starp Par/Pret/Atturas."""
    ranked = sorted(((c[b], b) for b in _SPLIT_BALLOTS), reverse=True)
    return ranked[0][1], ranked[0][0], ranked[1][0]


def _cands_vote_split(db, week_start, week_end):
    """Frakcija, kas šķēlās (≥2 deputāti mazākumā), vai koalīcijas frakcija,
    kuras vairākums balsoja citādi nekā koalīcijas bloks. Ķēde pēc
    ``document_nr`` (T14); ``⚠ NESAKRĪT`` balsojumi izlaisti; bez
    ``coalition_periods`` koalīciju nenosauc. Balsojums rakstīts kā reģistrēts
    («Atturas» nav «pret»)."""
    from src.coalition import coalition_at, coalition_periods
    votes, indiv = _week_vote_data(db, week_start, week_end)
    periods = coalition_periods(db)
    chains: dict[str, list] = {}
    for v in votes:
        key = (v["document_nr"] or "").strip() or f"motif:{v['motif'] or ''}"
        chains.setdefault(key, []).append(v)
    out = []
    for key, chain in chains.items():
        notes, days = [], set()
        for v in chain:
            all_facs = indiv.get(v["id"], {})
            if _vote_mismatch(v, all_facs):
                continue
            facs = {f: c for f, c in all_facs.items() if f != _NO_FACTION_LABEL}
            when = f"{v['vote_date']} {v['vote_time'] or ''}".strip()
            for f, c in sorted(facs.items()):
                _maj, _n_maj, n_second = _majority(c)
                if n_second >= SPLIT_MIN_MINORITY:
                    notes.append(f"{when}: {f} šķēlās (par/pret/atturas "
                                 f"{c['Par']}/{c['Pret']}/{c['Atturas']})")
                    days.add(str(v["vote_date"])[:10])
            coal = coalition_at(periods, v["vote_date"], v["vote_time"] or "") if periods else None
            if coal:
                bloc = {b: sum(facs[f][b] for f in facs if f in coal) for b in _SPLIT_BALLOTS}
                bloc_maj = _majority(bloc)[0]
                for f in sorted(facs):
                    if f not in coal:
                        continue
                    maj, n_maj, _ = _majority(facs[f])
                    if maj != bloc_maj and n_maj >= SPLIT_MIN_MINORITY:
                        notes.append(f"{when}: koalīcijas {f} {maj} ({n_maj}), "
                                     f"koalīcijas bloks {bloc_maj}")
                        days.add(str(v["vote_date"])[:10])
        if notes:
            label = key[6:] if key.startswith("motif:") else key
            out.append(_cand("vote_split", f"{label} ({chain[0]['motif']}): " + "; ".join(notes),
                             days=days, vote_ids=[v["id"] for v in chain]))
    return out


def weekly_vote_breakdown(db_path: str | None = None, week_start: str | None = None) -> str:
    """Per-faction ballot counts for every Saeima vote in the week — the ONLY
    source the weekly brief may quote faction/vote numbers from.

    Two of three weekly briefs before 2026-09-27 needed a post-publish fix
    because a faction split was paraphrased by hand («pret balsoja ZZS un LPV
    (27)» when Pret=27 was ZZS 9 + LPV 5 + AS 4 + ārpusfrakciju 9).

    - Attendance registrations are excluded by motif PREFIX (a
      '%reģistrācij%' filter would also drop «… reģistrācijas likums»).
    - Ballots are counted by EXACT value (Par/Pret/Atturas/Nebalsoja); any other
      value (attendance states inside a real vote, Data Contract #4b) is shown
      as «cits: N», never folded into nebalsoja.
    - Deputies with no faction (NULL or '') form the named «ārpusfrakciju»
      bucket — the balsojumi page (src/render/votes.py) does the same since
      2026-09-28 (``votes_matrix.NO_FACTION_LABEL``).
    - Σ Par/Pret/Atturas over all buckets is reconciled against the
      saeima_votes totals; a mismatch is printed on the vote, and the header
      carries the denominator (votes examined, votes with a mismatch).
    - Votes are grouped by document_nr (else by motif), each group in time
      order, so the whole procedural chain is visible (T14).

    Pure read; the connection is closed before returning.
    """
    if week_start is None:
        today = now_lv_dt()
        week_start = (today - timedelta(days=today.weekday())).strftime("%Y-%m-%d")
    week_end = (datetime.strptime(week_start, "%Y-%m-%d") + timedelta(days=6)).strftime("%Y-%m-%d")

    db = get_db(db_path)
    try:
        votes, indiv = _week_vote_data(db, week_start, week_end)
        from src.coalition import get_coalition_map
        cmap = get_coalition_map(db)
    finally:
        db.close()

    status_order = {"coalition": 0, "opposition": 1}

    def _fac_key(item):
        name, c = item
        if name == _NO_FACTION_LABEL:
            return (9, 0, name)
        return (status_order.get(cmap.get(name), 2), -sum(c.values()), name)

    groups: dict[tuple[str, str], list] = {}
    for v in votes:
        doc = (v["document_nr"] or "").strip()
        key = ("doc", doc) if doc else ("motif", v["motif"] or "")
        groups.setdefault(key, []).append(v)

    body: list[str] = []
    mismatches = 0
    for (kind, label), group in groups.items():
        body.append(f"\n## {label}" if kind == "doc" else f"\n## Bez dokumenta numura: {label}")
        for v in group:
            facs = indiv.get(v["id"], {})
            body.append(
                f"- #{v['id']} · {v['vote_date']} {v['vote_time'] or ''} · {v['motif']} · "
                f"{v['result'] or '—'} · kopā {v['total_par'] or 0}:{v['total_pret'] or 0}:"
                f"{v['total_atturas'] or 0} (nebalsoja {v['total_nebalso'] or 0}) · {v['url'] or '—'}"
            )
            diffs = _vote_mismatch(v, facs)
            if diffs:
                mismatches += 1
                body.append(f"  ⚠ NESAKRĪT: {'; '.join(diffs)}")
            parts = []
            for name, c in sorted(facs.items(), key=_fac_key):
                s = f"{name} {c['Par']}/{c['Pret']}/{c['Atturas']}/{c['Nebalsoja']}"
                if c["cits"]:
                    s += f" (cits: {c['cits']})"
                parts.append(s)
            body.append("  " + (" · ".join(parts) if parts else "individuālo balsu rindu nav"))

    head = [
        f"# Saeimas balsojumi pa frakcijām — {week_start} līdz {week_end}",
        "",
        f"Pārbaudīti balsojumi: {len(votes)} (bez klātbūtnes reģistrācijām); "
        f"individuālās balsis nesakrīt ar kopsummām: {mismatches}.",
        "Frakciju skaitļi: par/pret/atturas/nebalsoja. «cits» — rindas ar vērtību, "
        "kas nav balsojums (piemēram, reģistrācijas statuss). «ārpusfrakciju» — "
        "deputāti, kuri šajā balsojumā nebija nevienā frakcijā. "
        "«kopā» — Saeimas publicētās kopsummas par:pret:atturas.",
    ]
    return "\n".join(head + body) + "\n"


def generate_weekly_brief(db_path: str = None, week_start: str = None,
                          chart_dir: str = "output/images/briefs") -> str:
    """Generate a neutral weekly brief in markdown covering 7 days from week_start.

    Writes the deterministic movers chart SVG into `chart_dir` and references it
    from the markdown. The chart is data (never enters brief_images)."""
    if week_start is None:
        today = now_lv_dt()
        week_start = (today - timedelta(days=today.weekday())).strftime("%Y-%m-%d")
    week_end_dt = datetime.strptime(week_start, "%Y-%m-%d") + timedelta(days=6)
    week_end = week_end_dt.strftime("%Y-%m-%d")

    db = get_db(db_path)

    position_count = db.execute(
        "SELECT COUNT(*) FROM claims c WHERE date(c.stated_at) BETWEEN ? AND ? "
        f"AND c.claim_type = 'position' AND {_NOT_NEEDS_REVIEW_SQL}",
        (week_start, week_end),
    ).fetchone()[0]
    # Count DISTINCT Saeima vote events that occurred this week (saeima_votes by
    # vote_date) — NOT per-deputy saeima_vote claims. The latter has ~one row per
    # deputy per vote (~100×), so a normal 70-vote week reported "votes=5692",
    # an absurd figure that also happened to sit near the all-time vote total.
    # saeima_votes is created by init_saeima_tables (not init_db), so guard for
    # DBs that lack it (brief unit-test fixtures) → 0. Attendance registrations
    # («Deputātu klātbūtnes reģistrācija», two per sitting, 0/0/0 totals) are
    # stored in the same table but are quorum checks, not votes — Data Contract
    # #4b keeps them out of claims; keep them out of the public stat too
    # (2026-09-13 the card said «16 balsojumi» for a sitting with 14).
    if db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='saeima_votes'"
    ).fetchone():
        from src.saeima.votes import _REGISTRATION_MOTIF_PREFIX
        vote_count = db.execute(
            "SELECT COUNT(*) FROM saeima_votes WHERE date(vote_date) BETWEEN ? AND ? "
            "AND COALESCE(motif, '') NOT LIKE ?",
            (week_start, week_end, _REGISTRATION_MOTIF_PREFIX + '%'),
        ).fetchone()[0]
    else:
        vote_count = 0
    contradiction_count = routine_week_contradiction_count(db, week_start, week_end)

    by_topic = db.execute(f"""
        SELECT c.topic, COUNT(*) as cnt FROM claims c
        WHERE date(c.stated_at) BETWEEN ? AND ?
          AND c.claim_type = 'position' AND {_NOT_NEEDS_REVIEW_SQL}
        GROUP BY c.topic ORDER BY cnt DESC, topic
    """, (week_start, week_end)).fetchall()

    top_topic = by_topic[0]["topic"] if by_topic else "—"
    top_party_row = db.execute(f"""
        SELECT p.party, COUNT(*) AS cnt FROM claims c
        JOIN tracked_politicians p ON c.opponent_id = p.id
        WHERE date(c.stated_at) BETWEEN ? AND ? AND c.claim_type='position'
          AND {_NOT_NEEDS_REVIEW_SQL}
          AND p.relationship_type != 'inactive' AND p.party IS NOT NULL
        GROUP BY p.party ORDER BY cnt DESC LIMIT 1
    """, (week_start, week_end)).fetchone()
    top_party = top_party_row["party"] if top_party_row else "—"

    lines = [f"# Nedēļas stāsti — {week_start} līdz {week_end}\n"]

    # «Nedēļas stāsti» (2026-11-01, docs/superpowers/specs/2026-11-01-nedelas-stasti-design.md):
    # aģents izvēlas 3–5 stāstus no koda kandidātiem, nevis aizpilda tēmu un
    # bloku sadaļas. Kandidāti ir HTML komentārā — validators atsaka glabāt
    # pārskatu, kurā tas palicis. Pagājušās nedēļas «Skats uz priekšu» / «Ko
    # gaidīt» punkti ir `followup` kandidāti.
    lines.append(_story_candidates_comment(weekly_story_candidates(db, week_start)))
    lines.append("<!-- AGENT: 3–5 stāsti, katrs ar savu `## ` virsrakstu (kas ko "
                 "izdarīja), 60–220 vārdi. Aizvāc šo komentāru. -->\n")
    lines.append("## Īsumā\n")
    lines.append("<!-- AGENT: 0–5 teikumi, katrs ar saiti; ja nav ko teikt, sadaļu "
                 "dzēs. Aizvāc šo komentāru. -->\n")
    lines.append("## Ko gaidīt\n")
    lines.append("<!-- AGENT: tikai datēti notikumi ar nedēļas dienu un datumu; ja "
                 "tādu nav, sadaļu dzēs. Aizvāc šo komentāru. -->\n")

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
        f"""SELECT p.party, COUNT(*) AS cnt
           FROM claims c JOIN tracked_politicians p ON c.opponent_id = p.id
           WHERE date(c.stated_at) BETWEEN ? AND ? AND c.claim_type = 'position'
             AND {_NOT_NEEDS_REVIEW_SQL}
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
    lines.append(
        f"<!-- WEEKLY_BLOC coalition={coalition['coalition']} "
        f"opposition={coalition['opposition']} -->\n"
    )
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
    lines.append("")  # saraksts beidzas; nākamais bloks nav tā turpinājums

    # Frakciju skaitļi tikai no weekly_vote_breakdown (2026-09-27): divos no
    # trim pārskatiem pārstāstīts frakciju sadalījums bija jālabo pēc
    # publicēšanas. Norāde, ne pati tabula — tā ir izziņa aģentam, ne lasītājam.
    if vote_count:
        lines.append(
            "<!-- AGENT: frakciju un balsojumu skaitļus ņem TIKAI no "
            f'weekly_vote_breakdown(week_start="{week_start}"); pārstāstīts '
            "skaitlis bez šī avota nav atļauts. Aizvāc šo komentāru. -->\n"
        )

    # Dienu pārskati — one line of weekday links to the PUBLISHED daily pages
    # of this week (2026-09-06). Only days with a publish_approvals row are
    # linked: the weekly goes live after the dailies, and a link to an
    # unapproved day would 404 on the live site. Root-relative so the link
    # checker (scripts/check_output.py) resolves it from the site root.
    day_links = _weekly_day_links(db, week_start)
    if day_links:
        lines.append("**Dienu pārskati:** " + " · ".join(day_links) + "\n")

    lines.append("## Vizuālais brief\n")
    lines.append("<!-- AGENT: Tēma / Galvenā tēze / Skaitlis / Metaforas hint. "
                 "Aizvāc šo komentāru. -->\n")

    db.close()
    return "\n".join(lines)


def _story_candidates_comment(cands: list[dict]) -> str:
    """Kandidātu saraksts kā HTML komentārs skeletā (renderētājs to nerāda).
    ``-->`` kandidāta tekstā kļūst par ``—>``, lai komentārs neaizvērtos agri un
    iekšējais saraksts nenonāktu publiskajā lapā; komentārs aizveras tikai ar
    savu ``-->`` rindu."""
    lines = [f"<!-- STORY_CANDIDATES ({len(cands)}) — aģentam: izvēlies 3–5 stāstus, "
             "tad šo komentāru aizvāc."]
    if not cands:
        lines.append("- kandidātu nav")
    for c in cands:
        parts = [f"- [{c['kind']}] {c['fact']}"]
        if c["topic"]:
            parts.append(f"tēma: {c['topic']}")
        for label, key in (("dienas", "days"), ("pozīcijas", "claim_ids"),
                           ("balsojumi", "vote_ids"), ("pretrunas", "contradiction_ids")):
            if c[key]:
                parts.append(f"{label}: {', '.join(map(str, c[key]))}")
        if c["repeated"]:
            parts.append("atkārtojas")
        lines.append(" · ".join(parts).replace("-->", "—>"))
    lines.append("-->")
    return "\n".join(lines) + "\n"


_WEEKDAY_ABBR = ("P.", "O.", "T.", "C.", "Pk.", "S.", "Sv.")


def _weekly_day_links(db, week_start: str) -> list[str]:
    """``[P.](/blog/YYYY-MM-DD.html)`` for each day of the week that has BOTH a
    daily brief (by subject date, never created_at) and a publish approval."""
    approved = published_brief_keys(db)
    if not approved:
        return []
    have_brief = set()
    for r in db.execute(
        "SELECT topic, content, created_at FROM context_notes WHERE note_type='daily_brief'"
    ):
        d = brief_subject_date(r["topic"], r["content"], r["created_at"])
        if d:
            have_brief.add(d)
    start = datetime.strptime(week_start, "%Y-%m-%d")
    out = []
    for i in range(7):
        day = start + timedelta(days=i)
        d = day.strftime("%Y-%m-%d")
        if d in have_brief and d in approved:
            # Label from the calendar weekday, not the loop index — week_start
            # is a Monday in production but nothing enforces it.
            out.append(f"[{_WEEKDAY_ABBR[day.weekday()]}](/blog/{d}.html)")
    return out


def _weekly_movers(db_path: str, week_start: str, week_end: str, limit: int = 6) -> list[dict]:
    """Top `limit` politicians by position-claims this week, with delta vs the
    prior 7-day window. delta is an int, or the string "jauns" when the prior
    window has zero baseline. Absolute counts only — never percentages."""
    db = get_db(db_path)
    prev_start = (datetime.strptime(week_start, "%Y-%m-%d") - timedelta(days=7)).strftime("%Y-%m-%d")
    prev_end = (datetime.strptime(week_start, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")

    def counts(start, end):
        rows = db.execute(f"""
            SELECT p.id, p.name, p.party, COUNT(*) AS cnt
            FROM claims c JOIN tracked_politicians p ON c.opponent_id = p.id
            WHERE date(c.stated_at) BETWEEN ? AND ? AND c.claim_type = 'position'
              AND {_NOT_NEEDS_REVIEW_SQL}
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


# Mid-table (lower-case) form of the site-wide vocabulary — never a private map
# (until 2026-09-28 this said «reversija» while the site said «Apvērsums»).
_SEVERITY_LV = {k: lower_first(v) for k, v in SEVERITY_LV.items()}


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
    """Party label for brief tables — canonical ``parties.short_name``.

    Until 2026-09-05 this held a 10-entry map that rendered ``Stabilitātei!``
    as ``S!`` while the site rendered ``ST`` for the same faction, and passed
    eight other parties through at full length. Unknown labels still pass
    through unchanged (``party_short_name``'s own fallback).
    """
    if not party:
        return ""
    return party_short_name(party)


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
    pid_by_name: dict[str, int] = {}
    for r in rows:
        key = (r["name"], r["party"] or "")
        by_person[key] = by_person.get(key, 0) + 1
        if "relationship_type" in r.keys() and r["relationship_type"] == "organization":
            org_names.add(r["name"])
        if "pid" in r.keys():
            pid_by_name[r["name"]] = r["pid"]
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
    #
    # Uzvārds nāk no `split_name()` (pid izņēmumi, piem. 161 «Abu Meri» —
    # 2026-10-13 skeletā stāvēja «Meri (3)»), ne no pēdējā vārda.
    def _surname(name: str) -> str:
        pid = pid_by_name.get(name)
        if pid is not None:
            try:
                return split_name(pid, name)[1]
            except ValueError:
                pass
        return name.split()[-1]

    colliding = set()
    seen_surnames: dict[str, str] = {}
    for name, _party in by_person:
        if name in org_names:
            continue
        surname = _surname(name)
        other = seen_surnames.setdefault(surname, name)
        if other != name:
            colliding.add(surname)
    people_str = ", ".join(
        f"{name if (name in org_names or _surname(name) in colliding) else _surname(name)} ({cnt})"
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
