"""
Wiki sync engine for atmina.
Syncs DB data into an Obsidian-compatible wiki vault.

Key design:
  - YAML frontmatter is auto-synced from DB.
  - Body content below frontmatter is MANUAL and never overwritten.
  - Pages grouped by party, not relationship_type.

Struktūra (2026-09-05, plāna 5.9 — bez uzvedības izmaiņām): šis modulis ir
ORKESTRATORS un tam pieder `wiki_sync()`. Lapu primitīvi dzīvo
`src/wiki_format.py`, personu un tēmu lapu būvētāji `src/wiki_pages.py`,
indeksi `src/wiki_index.py`. Sadalījums ir PLAKANS (blakus moduļi, NE pakotne
`src/wiki/`) ar nolūku: `src.wiki` un `src.wiki_lint` ir importa ceļi, ko
runbooki un `.claude/agents/quality-reviewer.md` raksta burtiski, tāpēc
pakotnes pārcēlums klusi salauztu publicēšanas vārtus.

Viss, ko jebkad kāds importējis no `src.wiki`, joprojām importējams no šejienes
— sk. `__all__`. NEnoņem re-eksportus: `src/tools.py:382` ņem `_slugify`, testi
ņem `_update_page`, `_gather_person_signal`, `_render_law_bills_block` u.c.
"""

import logging
from pathlib import Path

from src.db import get_db, now_lv
from src.lv_text import LV_TRANS, slugify
from src.wiki_format import (
    DEFAULT_DB_PATH,
    DEFAULT_WIKI_DIR,
    _BILLS_SYNC_END,
    _BILLS_SYNC_START,
    _SYNC_END,
    _SYNC_START,
    _parse_frontmatter,
    _render_frontmatter,
    _render_law_bills_block,
    _sanitize_body,
    _strip_legacy_biedri_section,
    _strip_sync_block,
    _update_page,
    _update_page_with_sync_block,
)
from src.wiki_index import (
    _build_index,
    _build_laws_index,
    _build_mediji_page,
    _build_parties_index,
    _build_persons_index,
    _build_topics_index,
)
from src.wiki_lint import lint_wiki_with_db
from src.wiki_pages import (
    _SYNTHESIS_MAX_CHARS,
    WikiSynthesisOverflow,
    _build_person_frontmatter,
    _build_topic_frontmatter,
    _gather_person_signal,
    _pluralize_lv,
    _render_person_synthesis,
)

logger = logging.getLogger(__name__)

# Vēsturiskie privātie nosaukumi. Tabula un slug funkcija dzīvoja te līdz
# 2026-09-05 (plāna 4.3); `src/tools.py:382` un testi importē tos no šejienes,
# tāpēc aliasi paliek. Vienīgā definīcija: `src/lv_text.py`.
_LV_TRANS = LV_TRANS
_slugify = slugify

# Publiskā virsma, ko `src.wiki` garantē kopš 2026-04: katrs nosaukums te ir vai
# nu definēts šajā failā, vai re-eksportēts no blakus moduļiem. `__all__` te ir
# gan dokumentācija, gan ruff vārti — izņem nosaukumu no saraksta, un tā imports
# kļūst neizmantots (F401), tāpēc lints noķer klusu re-eksporta zaudēšanu.
__all__ = [
    # orkestrators (definēts te)
    "wiki_sync",
    "get_db",
    "now_lv",
    "lint_wiki_with_db",
    "logger",
    "DEFAULT_DB_PATH",
    "DEFAULT_WIKI_DIR",
    # src/lv_text.py aliasi
    "_LV_TRANS",
    "_slugify",
    # src/wiki_format.py
    "_parse_frontmatter",
    "_render_frontmatter",
    "_sanitize_body",
    "_update_page",
    "_update_page_with_sync_block",
    "_strip_sync_block",
    "_strip_legacy_biedri_section",
    "_render_law_bills_block",
    "_SYNC_START",
    "_SYNC_END",
    "_BILLS_SYNC_START",
    "_BILLS_SYNC_END",
    # src/wiki_pages.py
    "_build_person_frontmatter",
    "_build_topic_frontmatter",
    "_gather_person_signal",
    "_render_person_synthesis",
    "_pluralize_lv",
    "WikiSynthesisOverflow",
    "_SYNTHESIS_MAX_CHARS",
    # src/wiki_index.py
    "_build_persons_index",
    "_build_topics_index",
    "_build_parties_index",
    "_build_laws_index",
    "_build_mediji_page",
    "_build_index",
]


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
    live_topic_slugs: set[str] = set()
    for row in topic_rows:
        topic = row["topic"]
        slug = _slugify(topic)
        live_topic_slugs.add(slug)
        page_path = topics_dir / f"{slug}.md"
        fm = _build_topic_frontmatter(db, topic)
        _update_page(page_path, fm)
        topics_synced += 1

    # Izmet tēmu lapas, kurām DB vairs nav neviena claim (2026-08-24; defekts
    # atrasts 08-23). Sync pārraksta lapas, kurām dati IR, bet līdz šim
    # nepārstaigāja mapi, lai izmestu tās, kurām datu vairs nav — tāpēc
    # `topics/uznemejdarbiba-un-valsts-iejauksanas.md` palika kokā pēc tam, kad
    # tās vienīgais claim tika dzēsts NEEDS_REVIEW triāžā, un lints to skaitīja
    # gan kā `orphan_page`, gan kā `isolated_topic` (orphans 0→1).
    #
    # Vārti ir SIMETRISKI ar izveidošanu: izmetam tieši to, ko šis pats
    # `topic_rows` vaicājums vairs neizveidotu — nekāds otrs, atšķirīgs
    # kritērijs, kas varētu aiznest lapu, kurai dati ir. Tikai `topics/`:
    # person/party lapām semantika ir cita (piem. `inactive` politiķiem lapu
    # apzināti neģenerē, bet esošu lapu nedrīkst klusi aiznest).
    #
    # Drīkst dzēst bez rezerves kopijas, jo tēmas lapa ir TIKAI ģenerēta
    # frontmatter — `_update_page` tur ar roku rakstītu tekstu neuztur —, un
    # `wiki/topics/` ir git izsekots, tātad atgriežams.
    topics_pruned: list[str] = []
    for page in sorted(topics_dir.glob("*.md")):
        if page.name == "temas.md":
            continue  # apakšindekss, ne tēmas lapa (to pārraksta zemāk)
        if page.stem in live_topic_slugs:
            continue
        page.unlink()
        topics_pruned.append(page.name)
    if topics_pruned:
        logger.info(
            "wiki_sync: izmestas %d tēmu lapas bez claims: %s",
            len(topics_pruned), ", ".join(topics_pruned),
        )

    # Sync party pages
    # claim_type='position' visos trijos partiju vaicājumos (Datu kontrakts #4).
    # Bez filtra šie skaitīja balsojumus: JV 131 026 „pozīcijas" īsto 832 vietā,
    # Stabilitātei! 56 794 īsto 16 vietā — un `ORDER BY claims DESC` tāpēc
    # sakārtoja partijas pēc nobalsoto biļetenu skaita, ne pēc izteiktajām
    # pozīcijām (mērīts 2026-08-01).
    party_rows = db.execute("""
        SELECT party, COUNT(DISTINCT id) AS members,
               (SELECT COUNT(*) FROM claims c WHERE c.claim_type = 'position'
                AND c.opponent_id IN
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
            WHERE p.party = ? AND c.claim_type = 'position'
            GROUP BY p.id ORDER BY cnt DESC LIMIT 5
        """, (party,)).fetchall()

        top_topics = db.execute("""
            SELECT c.topic, COUNT(*) AS cnt
            FROM claims c JOIN tracked_politicians p ON c.opponent_id = p.id
            WHERE p.party = ? AND c.claim_type = 'position' AND c.topic IS NOT NULL
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

        # Programmas solījumi (Datu kontrakts #4a) — atsevišķs lauks blakus
        # `claims`, NEVIS tā vietā (operatora verdikts 2026-08-17). `claims`
        # skaita tikai claim_type='position'; partijai, kurai ir TIKAI
        # programmas solījumi (Gobzema saraksts, Suverēnā vara/Jaunlatvieši),
        # lapa citādi rādīja `claims: 0` un izskatījās, ka partija neko nedara.
        # `program_promise` rindas piesaistās partijai caur claims.party_id,
        # nevis caur politiķa piederību, tāpēc `tracked_politicians.party`
        # teksts jāizšķir pret `parties.name` VAI `parties.short_name` —
        # tāpat kā src/render/parties.py (MMN/JKP glabājas kā īsie vārdi).
        program_promises = db.execute("""
            SELECT COUNT(*) FROM claims c
            JOIN parties pa ON pa.id = c.party_id
            WHERE c.claim_type = 'program_promise'
              AND (pa.name = ? OR pa.short_name = ?)
        """, (party, party)).fetchone()[0]

        fm = {
            "party": party,
            "members": pr["members"],
            "claims": pr["claims"],
            "program_promises": program_promises,
            "contradictions": pr["contradictions"],
            "votes_par": vote_stats["par"] or 0,
            "votes_pret": vote_stats["pret"] or 0,
            "votes_atturas": vote_stats["atturas"] or 0,
            "top_politicians": [t["name"] for t in top_pols],
            "top_topics": [t["topic"] for t in top_topics],
        }

        # "## Biedri" lives in the SYNC block since 2026-08-04 — the previous
        # _update_page() path made it write-once, so membership fixes reached
        # the DB and the briefs but never these pages (10 of 18 stale; Šmits
        # sat under Stabilitātei! a month after the 07-26 correction).
        biedri_block = "## Biedri\n\n" + "".join(
            f"- [[persons/{_slugify(m['name'])}|{m['name']}]]\n" for m in members
        )
        _strip_legacy_biedri_section(page_path)
        _update_page_with_sync_block(page_path, fm, biedri_block)
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
        # Saucējs, ne tikai atradums (CLAUDE.md § Working Conventions): sync
        # klusi dzēš failus no versionēta koka, tāpēc skaits IR jāatgriež — un
        # tukšs saraksts ir atšķirams no „solis nenostrādāja".
        "topics_pruned": topics_pruned,
        "parties": parties_synced,
        "updated_at": now_lv(),
    }

    logger.info("wiki_sync complete: %s", result)

    # Run wiki lint check (also used by _build_index for status)
    lint_result = lint_wiki_with_db(wiki_dir, db_path)

    result["lint"] = lint_result["stats"]

    return result
