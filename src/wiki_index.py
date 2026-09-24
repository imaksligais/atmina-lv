"""
Wiki index builders — the four sub-indexes, the media register and index.md.

Carved out of ``src/wiki.py`` on 2026-09-05 (plāna 5.9) with no behaviour
change. ``src.wiki`` re-exports every name below; flat sibling module, NOT a
package. Every builder here is called exactly once, from ``wiki_sync``, and
every page it produces is FULLY overwritten on each sync — hand-edits are lost,
so patch the templates here, never the vault.
"""

import re
import sqlite3
from pathlib import Path

from src.db import now_lv
from src.lv_text import slugify as _slugify
from src.scope import queue_politician_sql
from src.wiki_format import DEFAULT_DB_PATH

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
    now = now_lv()

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
    now = now_lv()

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
    now = now_lv()

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
    now = now_lv()
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
        f"_Konfigurācijas spogulis no `sources.yaml` (`outlets:`); atjaunots: {now_lv()}_",
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
    now = now_lv()

    # --- Status overview ---
    # Real politicians only — this number is published as "N politiķi" and is
    # also the denominator of the media-coverage line below. `!= 'inactive'`
    # counted 27 audience slots (16 organizations incl. LETA/LTV Panorāma/
    # De Facto, 6 journalists, 5 neutral analysts) as politicians: 194 where
    # the truthful figure is 167 (operator decision 2026-08-15). Positive
    # predicate on purpose — an exclusion list grows with the taxonomy.
    total_politicians = db.execute(
        "SELECT COUNT(*) FROM tracked_politicians WHERE relationship_type = 'tracked'"
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
    # Both counters are QUEUE semantics, so the politician-side scope comes from
    # `src/scope.py` — a document nobody will ever be offered is not backlog.
    # Before 2026-08-02 this predicate was missing and the published figure read
    # 577 against a real queue backlog of 232: 58 docs on inactive politicians
    # and 287 on relay accounts, i.e. 60% of the headline number was work that
    # does not exist. That is the SECOND false-urgency conflation in this same
    # metric — the comment above records the first one (2026-04-10). CLAUDE.md
    # § Session Start points every new session at this file first, which is
    # exactly why it has to be the true number.
    true_backlog = db.execute(f"""
        SELECT COUNT(DISTINCT d.id)
        FROM documents d
        JOIN document_politicians dp ON dp.document_id = d.id
        WHERE d.reviewed_at IS NULL
          AND d.platform = 'web'
          AND dp.role = 'subject'
          AND {queue_politician_sql()}
    """).fetchone()[0]
    reviewed_empty = db.execute(f"""
        SELECT COUNT(DISTINCT d.id)
        FROM documents d
        JOIN document_politicians dp ON dp.document_id = d.id
        LEFT JOIN claims c ON c.document_id = d.id
        WHERE d.reviewed_at IS NOT NULL
          AND c.id IS NULL
          AND d.platform = 'web'
          AND dp.role = 'subject'
          AND {queue_politician_sql()}
    """).fetchone()[0]

    # Media coverage health — the headline metric for the rhetorical side of
    # the project. Median position claims per tracked politician is a better
    # health signal than raw totals because legislative votes dominate the
    # totals. `zero_media_count` surfaces politicians with no first-person
    # extracted statements at all. Uses claim_type='position' as the
    # authoritative filter post Phase A.
    #
    # Scoped to relationship_type='tracked' (2026-08-15). CLAUDE.md § Session
    # Start makes this the first number every session reads, and under
    # `!= 'inactive'` it was 34/194 — but 11 of those 34 were relay news slots
    # (LETA, LTV Panorāma, LTV Ziņas, TV3 Ziņas, De Facto, Krustpunktā, NRA,
    # IR žurnāls, Saeimas ziņas, Kas Notiek Latvijā, "Latvija latviešiem")
    # which by construction can never hold a first-party position — inv #11 and
    # src/scope.py exclude them from the extraction queue for exactly that
    # reason. Flagging work that is impossible by design is a gate that can
    # never go green. Truthful figure: 23/167 (median unchanged at 6).
    media_per_politician = [
        row[0] for row in db.execute("""
            SELECT COUNT(CASE WHEN c.claim_type = 'position' THEN 1 END)
            FROM tracked_politicians tp
            LEFT JOIN claims c ON c.opponent_id = tp.id
            WHERE tp.relationship_type = 'tracked'
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
        f"- Saucējs: «politiķi» = tikai `relationship_type='tracked'` ieraksti; "
        f"mediju, žurnālistu un iestāžu sloti nav ieskaitīti",
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

    # Report corruption unconditionally — the other counters are only printed
    # when non-zero, but "no corrupt pages" is the statement a reader most needs
    # to be able to trust, and an absent line reads as "not checked" rather than
    # "clean". Silence here is what let 22 NUL-damaged pages sit behind a
    # "0 broken links" all-clear for two months (2026-08-01 audit).
    if lint_s["total_issues"] > 0:
        lines.append(
            f"- Lint: {lint_s['orphans']} orphans, {lint_s['broken_links']} broken links, "
            f"{lint_s.get('stale', 0)} stale frontmatter, "
            f"{lint_s.get('isolated', 0)} izolētas tēmas, "
            f"{lint_s.get('corrupt', 0)} bojātas lapas"
        )
    if lint_s.get("corrupt"):
        lines.append(
            f"- ⚠ **{lint_s['corrupt']} bojātas wiki lapas** — palaid `wiki_sync()` "
            f"vēlreiz; ja paliek, sk. `src/wiki.py::_sanitize_body`"
        )

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

    # A link's count must be the count of the page it points at. This line used
    # `total_politicians` (`relationship_type='tracked'`, 167) while
    # persons/personas.md and the persona-page loop in wiki_sync() both filter
    # `relationship_type != 'inactive'` (196) — so the label under-reported the
    # linked page by 29 profiles (2026-09-05 docs-vs-code audit § 5). Same
    # predicate as _build_persons_index and as the wiki_sync() person loop:
    # this number IS the number of persona pages written.
    active_profiles = db.execute(
        "SELECT COUNT(*) FROM tracked_politicians WHERE relationship_type != 'inactive'"
    ).fetchone()[0]

    lines += [
        "",
        "## Struktūra",
        "",
        f"- [[persons/personas|Politiķi]] — {active_profiles} profili, {active_positions} pozīcijas (tikai aktīvie)",
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
    lines.append("- [[operations/atmina-ops|atmina ops]] — lokāls operatora dashboard (`.venv/Scripts/python.exe serve.py`)")
    lines.append("- [[log-ingest|Ielādes žurnāls]] — dokumentu ielādes vēsture")
    # Saucējs katram skaitlim (CLAUDE.md § „gate that cannot fail" korolārijs (b):
    # skaitlis ir uzticams tikai kopā ar vaicājumu, kas to radījis). Divi dažādi
    # politiķu skaitļi šajā lapā NAV kļūda — tie atbild uz diviem jautājumiem —
    # bet bez šīs rindas tie izskatās pēc pretrunas.
    lines.append("")
    lines.append(
        "> **Saucēji.** «Stāvoklis» politiķi = "
        "`SELECT COUNT(*) FROM tracked_politicians WHERE relationship_type='tracked'` "
        "(īstie politiķi; mediju, žurnālistu un iestāžu sloti nav ieskaitīti). "
        "«Struktūra» profili = "
        "`SELECT COUNT(*) FROM tracked_politicians WHERE relationship_type!='inactive'` "
        "— tieši tik personu lapu `wiki_sync()` uzraksta, tāpēc šis skaitlis "
        "atbilst [[persons/personas]] virsrakstam. «Struktūra» pozīcijas = "
        "`SELECT COUNT(*) FROM claims c JOIN tracked_politicians tp ON tp.id=c.opponent_id "
        "WHERE c.claim_type='position' AND tp.relationship_type!='inactive'`; "
        "«Stāvoklis» pozīcijas skaita arī neaktīvo politiķu rindas, tāpēc ir lielākas."
    )
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
