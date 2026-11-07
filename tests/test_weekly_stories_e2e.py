"""«Nedēļas stāsti» no gala līdz galam (spec 2026-11-01 § 5): iestādīta frakcijas
šķelšanās un tēmas lēciens → skelets tos piedāvā kā kandidātus → aizpildīts
pārskats iziet saglabāšanas vārtus → renderējas ar skaitļu kartītēm un
priekšskatu no pirmā stāsta, bez iekšējā kandidātu saraksta."""
import json
import re

from tests.test_weekly_story_candidates import WEEK, _claim, _vote_db


def _fill(skeleton: str) -> str:
    """Aģenta darbs: kandidātu un AGENT komentāri aizvākti, ielikti 3 stāsti."""
    md = re.sub(r"<!-- STORY_CANDIDATES.*?\n-->\n", "", skeleton, flags=re.S)
    md = re.sub(r"<!-- AGENT:.*?-->\n", "", md, flags=re.S)
    stories = "".join(
        f"## JV deputāti šķēlās balsojumā {i}\n\n"
        + ("Trešdien Saeima balsoja par grozījumiem likumā ([saeima.lv](https://saeima.lv/x)). " * 12)
        + "\n\n"
        for i in range(1, 4))
    head, rest = md.split("\n", 1)
    md = head + "\n\n" + stories + rest.lstrip("\n")
    md = md.replace("## Īsumā\n", "## Īsumā\n\n- Korupcijas tēmā nedēļā 8 pozīcijas "
                                   "([e.lv](https://e.lv/1)).\n", 1)
    md = md.replace("## Ko gaidīt\n", "", 1)
    return md.replace("## Vizuālais brief\n", "## Vizuālais brief\n\n- **Tēma:** Saeima\n"
                      "- **Galvenā tēze:** JV šķēlās\n- **Metaforas hint:** sadalīta zāle\n", 1)


def test_weekly_stories_end_to_end(tmp_path, monkeypatch):
    from src.briefs import generate_weekly_brief
    from src.render.blog import _brief_preview, _weekly_content_for_render
    import src.tools as tools_mod
    from src.db import get_db

    db = _vote_db(tmp_path, [("JV", "Par", 10), ("JV", "Pret", 2), ("ZZS", "Par", 8)])
    for _ in range(8):
        _claim(db, 1, "Korupcija un KNAB", "2026-05-27")
    db.commit()
    path = db.execute("PRAGMA database_list").fetchone()[2]

    skeleton = generate_weekly_brief(path, week_start=WEEK, chart_dir=str(tmp_path / "c"))
    start = skeleton.index("<!-- STORY_CANDIDATES (")
    comment = skeleton[start:skeleton.index("\n-->", start)]
    assert "- [vote_split] 123/Lp14" in comment
    assert "- [topic_surge] Korupcija un KNAB: 8 pozīcijas" in comment

    md = _fill(skeleton)
    assert "STORY_CANDIDATES" not in md and "<!-- AGENT" not in md

    monkeypatch.setattr(tools_mod, "get_db", lambda p=None: get_db(path))
    res = json.loads(tools_mod.store_context_note(
        topic="nedēļas analīze 2026-05-25 līdz 2026-05-31", note_type="weekly_brief", content=md))
    assert res.get("status") == "success", res
    stored = db.execute("SELECT content FROM context_notes WHERE note_type='weekly_brief'").fetchone()[0]
    assert stored == md

    html_md = _weekly_content_for_render(stored, is_weekly=True)
    assert "weekly-stats" in html_md
    assert "STORY_CANDIDATES" not in html_md and "Vizuālais brief" not in html_md
    body = stored.split("\n", 1)[1]
    assert _brief_preview(body).startswith("Trešdien Saeima balsoja par grozījumiem likumā.")

