import tempfile
from pathlib import Path
from src.wiki_lint import lint_wiki


def _make_wiki(tmp: Path, persons: list[str], index_links: list[str]) -> Path:
    """Create minimal wiki structure for testing."""
    wiki = tmp / "wiki"
    (wiki / "persons").mkdir(parents=True)
    (wiki / "topics").mkdir(parents=True)
    for name in persons:
        (wiki / "persons" / f"{name}.md").write_text(f"---\nname: {name}\n---\n", encoding="utf-8")
    index_lines = ["# atmina — Indekss\n"]
    for link in index_links:
        index_lines.append(f"- [[persons/{link}|{link}]]\n")
    (wiki / "index.md").write_text("".join(index_lines), encoding="utf-8")
    return wiki


def test_orphan_person_detected():
    """Person page exists but is not linked from index.md."""
    with tempfile.TemporaryDirectory() as tmp:
        wiki = _make_wiki(
            Path(tmp),
            persons=["janis-berzins", "anna-kalve"],
            index_links=["janis-berzins"],
        )
        result = lint_wiki(str(wiki))
        orphans = [i for i in result["issues"] if i["type"] == "orphan_page"]
        assert len(orphans) == 1
        assert "anna-kalve" in orphans[0]["path"]


def test_no_orphans_when_all_linked():
    with tempfile.TemporaryDirectory() as tmp:
        wiki = _make_wiki(
            Path(tmp),
            persons=["janis-berzins", "anna-kalve"],
            index_links=["janis-berzins", "anna-kalve"],
        )
        result = lint_wiki(str(wiki))
        orphans = [i for i in result["issues"] if i["type"] == "orphan_page"]
        assert len(orphans) == 0


def test_broken_wikilink_detected():
    """Index references a person page that doesn't exist."""
    with tempfile.TemporaryDirectory() as tmp:
        wiki = _make_wiki(
            Path(tmp),
            persons=["janis-berzins"],
            index_links=["janis-berzins", "ghost-politician"],
        )
        result = lint_wiki(str(wiki))
        broken = [i for i in result["issues"] if i["type"] == "broken_link"]
        assert len(broken) == 1
        assert "ghost-politician" in broken[0]["target"]


def test_stale_page_detected(tmp_path):
    """Person page whose `positions` frontmatter disagrees with the DB.

    The key is `positions`. This test used to write `claims_count`, which
    wiki_sync has never emitted — so the fixture satisfied the checker while
    no real page could, and the check sat dead from the day it was added
    until 2026-08-02. See test_lint_reads_keys_wiki_sync_actually_writes.
    """
    wiki = tmp_path / "wiki"
    (wiki / "persons").mkdir(parents=True)
    (wiki / "topics").mkdir(parents=True)
    page = wiki / "persons" / "janis-berzins.md"
    page.write_text("---\nname: Jānis Bērziņš\npositions: 50\n---\n", encoding="utf-8")
    (wiki / "index.md").write_text("- [[persons/janis-berzins|Jānis Bērziņš]]\n", encoding="utf-8")
    result = lint_wiki(str(wiki), db_counts={"janis-berzins": 12})
    stale = [i for i in result["issues"] if i["type"] == "stale_frontmatter"]
    assert len(stale) == 1
    assert stale[0]["detail"]["wiki_count"] == 50
    assert stale[0]["detail"]["db_count"] == 12


def test_missing_cross_reference():
    """Topic page exists but no person page references that topic."""
    with tempfile.TemporaryDirectory() as tmp:
        wiki = Path(tmp) / "wiki"
        (wiki / "persons").mkdir(parents=True)
        (wiki / "topics").mkdir(parents=True)
        (wiki / "topics" / "imigracija.md").write_text("---\ntopic: Imigrācija\npositions: 5\n---\n", encoding="utf-8")
        (wiki / "persons" / "janis-berzins.md").write_text("---\nname: Jānis Bērziņš\ntop_topics: []\n---\n", encoding="utf-8")
        (wiki / "index.md").write_text("- [[persons/janis-berzins|J]]\n\n## Tēmas\n- [[topics/imigracija|Imigrācija]]\n", encoding="utf-8")
        result = lint_wiki(str(wiki))
        isolated = [i for i in result["issues"] if i["type"] == "isolated_topic"]
        assert len(isolated) == 1


def test_lint_summary_format():
    """lint_wiki returns printable summary."""
    with tempfile.TemporaryDirectory() as tmp:
        wiki = _make_wiki(
            Path(tmp),
            persons=["janis-berzins"],
            index_links=["janis-berzins", "ghost"],
        )
        result = lint_wiki(str(wiki))
        assert "stats" in result
        assert result["stats"]["total_issues"] == (
            result["stats"]["orphans"]
            + result["stats"]["broken_links"]
            + result["stats"]["stale"]
            + result["stats"]["isolated"]
            + result["stats"]["corrupt"]
        )


class TestCorruptPageDetection:
    """The lint must look at page BODIES, across the WHOLE vault.

    Checks 1-4 read bodies only to parse frontmatter and only visit
    persons/topics/parties/laws. That blind spot let 22 NUL-damaged pages sit
    behind a "0 broken links" all-clear for two months (2026-05-31 →
    2026-08-01), which wiki/index.md published and CLAUDE.md tells every
    session to read first.
    """

    def test_nul_corrupted_page_is_flagged(self, tmp_path):
        from src.wiki_lint import lint_wiki

        wiki = tmp_path / "wiki"
        (wiki / "topics").mkdir(parents=True)
        (wiki / "topics" / "klimats.md").write_bytes(
            b"---\ntopic: Klimats\n---\n\n" + b"\x00" * 200
        )

        result = lint_wiki(str(wiki))

        corrupt = [i for i in result["issues"] if i["type"] == "corrupt_page"]
        assert len(corrupt) == 1
        assert "klimats.md" in corrupt[0]["path"]
        assert result["stats"]["corrupt"] == 1

    def test_clean_page_is_not_flagged(self, tmp_path):
        from src.wiki_lint import lint_wiki

        wiki = tmp_path / "wiki"
        (wiki / "topics").mkdir(parents=True)
        (wiki / "topics" / "klimats.md").write_text(
            "---\ntopic: Klimats\n---\n\n## Saturs\n", encoding="utf-8"
        )

        result = lint_wiki(str(wiki))
        assert result["stats"]["corrupt"] == 0

    def test_check_reaches_subdirs_the_other_checks_ignore(self, tmp_path):
        """synthesis/ and operations/ are outside the four indexed subdirs."""
        from src.wiki_lint import lint_wiki

        wiki = tmp_path / "wiki"
        (wiki / "synthesis").mkdir(parents=True)
        (wiki / "operations").mkdir(parents=True)
        (wiki / "synthesis" / "kaut-kas.md").write_bytes(b"# X\n\x00\x00")
        (wiki / "operations" / "runbook.md").write_bytes(b"# Y\n\x00")

        result = lint_wiki(str(wiki))
        paths = {i["path"] for i in result["issues"] if i["type"] == "corrupt_page"}
        assert len(paths) == 2, f"whole-vault walk missed something: {paths}"


def test_lint_reads_keys_wiki_sync_actually_writes(tmp_path):
    """Checks 3 and 4 must read frontmatter keys the writer really emits.

    This is the guard that was missing. Both checks were written against
    invented keys — `claims_count` on persons and topics, `topics` on persons
    — and their tests wrote those same invented keys into fixtures, so the
    suite was green while neither check could fire on a real page. wiki/index.md
    published "0 broken links" on the strength of that green for months.

    Asserting the real key names here means a rename in wiki.py breaks this
    test instead of silently switching the checks back off.
    """
    from src.db import init_db, get_db
    from src.wiki import _build_person_frontmatter, _build_topic_frontmatter

    db_file = tmp_path / "t.db"
    init_db(str(db_file))
    # init_db does not create the Saeima tables (src/saeima.py owns them) and
    # the frontmatter builders count votes — same note as tests/test_wiki.py.
    from src.saeima import init_saeima_tables

    init_saeima_tables(str(db_file))
    db = get_db(str(db_file))
    db.execute(
        "INSERT INTO tracked_politicians (id, name, name_forms, relationship_type) "
        "VALUES (1, 'Testa Politis', '[]', 'tracked')"
    )
    db.execute(
        """INSERT INTO claims (opponent_id, topic, stance, confidence, salience,
                               source_url, stated_at, claim_type)
           VALUES (1, 'Imigrācija', 's', 0.8, 0.5, 'https://x.lv/1',
                   date('now','-2 days'), 'position')"""
    )
    db.commit()

    politician = db.execute("SELECT * FROM tracked_politicians WHERE id=1").fetchone()
    person_fm = _build_person_frontmatter(db, politician)
    topic_fm = _build_topic_frontmatter(db, "Imigrācija")
    db.close()

    # Check 3 reads person `positions`; check 4 reads person `top_topics`
    # and topic `positions`.
    assert "positions" in person_fm, sorted(person_fm)
    assert "top_topics" in person_fm, sorted(person_fm)
    assert "positions" in topic_fm, sorted(topic_fm)

    # And the keys they must NOT drift back to.
    assert "claims_count" not in person_fm
    assert "claims_count" not in topic_fm
    assert "topics" not in person_fm


def test_topic_referenced_by_person_is_not_isolated(tmp_path):
    """top_topics holds display names, topic pages are slugs — compare via _slugify.

    A .lower() comparison (the pre-2026-08-02 form) would call every
    multi-word or diacritic topic isolated even when a person page lists it.
    """
    wiki = tmp_path / "wiki"
    (wiki / "persons").mkdir(parents=True)
    (wiki / "topics").mkdir(parents=True)
    (wiki / "topics" / "valsts-parvalde.md").write_text(
        "---\ntopic: Valsts pārvalde\npositions: 9\n---\n", encoding="utf-8"
    )
    (wiki / "persons" / "janis-berzins.md").write_text(
        "---\nname: Jānis Bērziņš\ntop_topics:\n- Valsts pārvalde\n---\n", encoding="utf-8"
    )
    (wiki / "index.md").write_text(
        "- [[persons/janis-berzins|J]]\n\n## Tēmas\n- [[topics/valsts-parvalde|Valsts pārvalde]]\n",
        encoding="utf-8",
    )
    result = lint_wiki(str(wiki))
    isolated = [i for i in result["issues"] if i["type"] == "isolated_topic"]
    assert isolated == [], isolated
