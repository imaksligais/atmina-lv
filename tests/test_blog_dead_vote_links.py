"""Vecā `parentID=` balsojuma saite publicētā pārskatā.

Kļūme, ko tests ķer: pārskats lasītājam ved uz tukšu Saeimas lapu, vai saites
labojums maina pārskata tekstu DB un līdz ar to tā apstiprinājuma hešu (T15).

Īstais orķestrators, pagaidu DB; dzīvā DB netiek aiztikta.
"""

from __future__ import annotations

from pathlib import Path

from src.briefs import DAILY_BRIEF_TOPIC_PREFIX, brief_publish_key, publish_content_hash
from src.db import get_db, init_db
from src.saeima.schema import init_saeima_bills, init_saeima_tables

DAY = "2031-10-24"
OLD = "https://titania.saeima.lv/LIVS14/SaeimaLIVS2_DK.nsf/Voting?ReadForm&parentID=4e7fc213-d6f8-4532-8e4e-b5667fa18a97"
UNKNOWN = "https://titania.saeima.lv/LIVS14/SaeimaLIVS2_DK.nsf/Voting?ReadForm&parentID=00000000-0000-0000-0000-000000000000"
# Pārskats 584 (2026-09-14) rakstīts ar nogrieztu ID.
SHORT = OLD[: OLD.index("parentID=") + len("parentID=4e7fc213-d6f8-4532")]
BRIEF = (
    f"# Dienas pārskats — {DAY}\n\n## Galvenais\n\n"
    f"Saeima [balsoja]({OLD}), [vēlreiz]({SHORT}), arī [cits]({UNKNOWN}).\n"
)


def test_daily_brief_page_links_permanent_vote_url_and_hash_stays(tmp_path):
    import pytest

    import src.render._orchestrator as orch
    from src.saeima.vote_url_map import permanent_vote_url

    db_path = str(tmp_path / "t.db")
    init_db(db_path)
    init_saeima_tables(db_path)
    init_saeima_bills(db_path)
    db = get_db(db_path)
    db.execute(
        "INSERT INTO context_notes (topic, note_type, content, created_at) VALUES (?, 'daily_brief', ?, ?)",
        (f"{DAILY_BRIEF_TOPIC_PREFIX}{DAY}", BRIEF, f"{DAY} 21:00:00"),
    )
    db.commit()
    key = brief_publish_key("daily_brief", DAY)
    before = publish_content_hash(db, key)

    with pytest.MonkeyPatch.context() as mp:
        for name in ("_download_chart_js", "_download_annotation_plugin", "_download_d3"):
            mp.setattr(orch, name, lambda *a, **k: None)
        orch.generate_public_site(db_path=db_path, output_dir=str(tmp_path), only={"blog"}, include_drafts=True)

    page = Path(tmp_path / "atmina" / "blog" / f"{DAY}.html").read_text(encoding="utf-8")
    new = permanent_vote_url(OLD)
    assert new and new.endswith("?OpenDocument")
    assert page.count(new) == 2
    assert "4e7fc213" not in page
    # Nezināma saite paliek, nevis pazūd: labāk tukša lapa nekā izdomāts mērķis.
    assert "00000000-0000-0000-0000-000000000000" in page

    assert publish_content_hash(db, key) == before
    assert OLD in db.execute("SELECT content FROM context_notes").fetchone()[0]
    db.close()
