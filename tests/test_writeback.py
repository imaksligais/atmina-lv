import tempfile
from pathlib import Path
from src.wiki_writeback import enrich_person_page


def test_enrich_adds_insight_to_body():
    with tempfile.TemporaryDirectory() as tmp:
        page = Path(tmp) / "janis-berzins.md"
        page.write_text(
            "---\nname: Jānis Bērziņš\nparty: JV\n---\n\n## Piezīmes\n\nExisting note.\n",
            encoding="utf-8",
        )
        enrich_person_page(
            str(page),
            insight="Mainījis pozīciju par Rail Baltica 2x pēdējo 3 mēnešu laikā.",
            source="query writeback",
        )
        text = page.read_text(encoding="utf-8")
        assert "Rail Baltica" in text
        assert "query writeback" in text
        assert "name: Jānis Bērziņš" in text


def test_enrich_does_not_duplicate():
    with tempfile.TemporaryDirectory() as tmp:
        page = Path(tmp) / "janis-berzins.md"
        page.write_text("---\nname: J\n---\n\n## Writeback\n\n- insight A\n", encoding="utf-8")
        enrich_person_page(str(page), insight="insight A", source="test")
        text = page.read_text(encoding="utf-8")
        assert text.count("insight A") == 1


def test_enrich_creates_section_if_missing():
    with tempfile.TemporaryDirectory() as tmp:
        page = Path(tmp) / "janis-berzins.md"
        page.write_text("---\nname: J\n---\n\nSome body text.\n", encoding="utf-8")
        enrich_person_page(str(page), insight="New insight", source="query")
        text = page.read_text(encoding="utf-8")
        assert "## Writeback" in text
        assert "New insight" in text
