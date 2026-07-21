from src.db import init_db, get_db
from src.briefs import _weekly_movers


def _seed(db_path):
    init_db(db_path)
    db = get_db(db_path)
    db.execute("INSERT INTO parties (name, short_name, coalition_status) VALUES ('Test', 'T', 'coalition')")
    db.execute("INSERT INTO tracked_politicians (id, name, party, relationship_type) VALUES (1,'Aļģis','Test','tracked')")
    db.execute("INSERT INTO tracked_politicians (id, name, party, relationship_type) VALUES (2,'Bērziņš','Test','tracked')")
    # documents needed for FK on position claims
    for did in (10, 11, 12, 13, 20):
        db.execute(
            "INSERT INTO documents (id, platform, source_url, content, content_hash, scraped_at) "
            "VALUES (?, 'web', ?, 'x', ?, '2026-05-20')",
            (did, f"https://e.lv/{did}", f"hash{did}"),
        )
    # this week (2026-05-26..06-01): pid1=3 claims, pid2=1 claim
    db.execute("INSERT INTO claims (opponent_id, document_id, topic, stance, source_url, stated_at, claim_type) VALUES (1,10,'A','s','https://e.lv/10','2026-05-27','position')")
    db.execute("INSERT INTO claims (opponent_id, document_id, topic, stance, source_url, stated_at, claim_type) VALUES (1,11,'A','s','https://e.lv/11','2026-05-28','position')")
    db.execute("INSERT INTO claims (opponent_id, document_id, topic, stance, source_url, stated_at, claim_type) VALUES (1,12,'A','s','https://e.lv/12','2026-05-29','position')")
    db.execute("INSERT INTO claims (opponent_id, document_id, topic, stance, source_url, stated_at, claim_type) VALUES (2,13,'A','s','https://e.lv/13','2026-05-30','position')")
    # previous week (2026-05-19..25): pid1=1 claim (baseline), pid2=0 (no baseline)
    db.execute("INSERT INTO claims (opponent_id, document_id, topic, stance, source_url, stated_at, claim_type) VALUES (1,20,'A','s','https://e.lv/20','2026-05-20','position')")
    db.commit()
    return db


def test_weekly_movers_counts_and_deltas(tmp_path):
    db_path = str(tmp_path / "t.db")
    _seed(db_path)
    movers = _weekly_movers(db_path, "2026-05-26", "2026-06-01")
    by_name = {m["name"]: m for m in movers}
    # absolute counts this week
    assert by_name["Aļģis"]["count"] == 3
    assert by_name["Bērziņš"]["count"] == 1
    # delta vs prior week: Aļģis 1->3 = +2; Bērziņš no baseline => "jauns"
    assert by_name["Aļģis"]["delta"] == 2
    assert by_name["Bērziņš"]["delta"] == "jauns"
    # sorted by count desc
    assert movers[0]["name"] == "Aļģis"


def test_weekly_skeleton_has_new_sections(tmp_path):
    from src.briefs import generate_weekly_brief
    db_path = str(tmp_path / "t.db")
    _seed(db_path)
    md = generate_weekly_brief(db_path, week_start="2026-05-26",
                               chart_dir=str(tmp_path / "imgs"))
    assert md.startswith("# Nedēļas analīze — 2026-05-26 līdz 2026-06-01")
    assert "## Nedēļas stāsts" in md
    assert "## Nedēļā skaitļos" in md
    assert "<!-- WEEKLY_STATS:" in md
    assert "positions=4" in md          # 4 position claims seeded this week
    assert "## Kas kustējās" in md
    assert "## Nedēļas galvenās tēmas" in md
    # Bloc scaffold (coalition vs opposition) — seeded politicians are all
    # coalition, so at minimum the Koalīcija row must render.
    assert "## Koalīcija vs Opozīcija" in md
    assert "| Koalīcija |" in md
    # theme scaffold includes a source-linked candidate position
    assert "https://e.lv/" in md


def test_weekly_bloc_bar_counts_opposition_outside_top6(tmp_path):
    """Regression: the Koalīcija/Opozīcija strip must be computed over ALL of
    the week's position claims, not just the top-6 movers. An active opposition
    that falls outside the top-6 leaderboard (the leaderboard is structurally
    coalition-heavy) must still produce a non-zero opposition segment.

    Under the old code the strip summed only `movers` (top-6) → the opposition
    bar was empty whenever no opposition politician cracked the top-6.
    """
    import re
    import src.graphics.weekly_chart as wc
    db_path = str(tmp_path / "t.db")
    init_db(db_path)
    db = get_db(db_path)
    db.execute("INSERT INTO parties (name, short_name, coalition_status) VALUES ('Koal','K','coalition')")
    db.execute("INSERT INTO parties (name, short_name, coalition_status) VALUES ('Opoz','O','opposition')")
    docid = 100
    pid = 1
    # 7 coalition politicians × 3 claims each → all rank above the opposition
    for i in range(7):
        db.execute("INSERT INTO tracked_politicians (id,name,party,relationship_type) VALUES (?,?,'Koal','tracked')", (pid, f"K{i}"))
        for _ in range(3):
            db.execute("INSERT INTO documents (id,platform,source_url,content,content_hash,scraped_at) VALUES (?,'web',?,'x',?,'2026-05-27')", (docid, f"https://e.lv/{docid}", f"h{docid}"))
            db.execute("INSERT INTO claims (opponent_id,document_id,topic,stance,source_url,stated_at,claim_type) VALUES (?,?,'A','s',?,'2026-05-27','position')", (pid, docid, f"https://e.lv/{docid}"))
            docid += 1
        pid += 1
    # 1 opposition politician with a single claim → rank #8, outside top-6
    db.execute("INSERT INTO tracked_politicians (id,name,party,relationship_type) VALUES (?,'OppMP','Opoz','tracked')", (pid,))
    db.execute("INSERT INTO documents (id,platform,source_url,content,content_hash,scraped_at) VALUES (?,'web',?,'x',?,'2026-05-27')", (docid, f"https://e.lv/{docid}", f"h{docid}"))
    db.execute("INSERT INTO claims (opponent_id,document_id,topic,stance,source_url,stated_at,claim_type) VALUES (?,?,'A','s',?,'2026-05-27','position')", (pid, docid, f"https://e.lv/{docid}"))
    db.commit()

    from src.briefs import generate_weekly_brief
    out_dir = tmp_path / "imgs"
    generate_weekly_brief(db_path, week_start="2026-05-26", chart_dir=str(out_dir))
    svg = list(out_dir.glob("*-nedelas-movers.svg"))[0].read_text(encoding="utf-8")
    # The strip rect is height=18 (legend swatches are height=11), fill=_OPP.
    widths = [int(w) for w in re.findall(
        r'<rect x="\d+" y="\d+" width="(\d+)" height="18" fill="' + re.escape(wc._OPP) + '"', svg)]
    assert widths and widths[0] > 0, f"opposition strip width should be >0, got {widths}"


def test_weekly_skeleton_embeds_chart(tmp_path):
    from src.briefs import generate_weekly_brief
    db_path = str(tmp_path / "t.db")
    _seed(db_path)
    out_dir = tmp_path / "imgs"
    md = generate_weekly_brief(db_path, week_start="2026-05-26",
                               chart_dir=str(out_dir))
    assert "![Kas kustējās](../images/briefs/" in md
    # Reader-facing legend explaining the count + delta annotations.
    assert "izmaiņa pret iepriekšējo nedēļu" in md
    files = list(out_dir.glob("*-nedelas-movers.svg"))
    assert len(files) == 1
    assert files[0].read_bytes().startswith(b"<?xml")
