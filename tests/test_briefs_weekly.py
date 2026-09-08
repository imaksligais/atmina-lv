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
    assert "## Nedēļa skaitļos" in md
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


# ---------------------------------------------------------------------------
# 2026-09-06 — three skeleton additions (operatora lēmums pēc 10 nedēļu
# pārskatu mērījuma): Pārējās tēmas rinda, Pretrunas tikai ar apstiprinātu
# rindu, Dienu pārskati saites tikai uz publicētām dienas lapām.
# ---------------------------------------------------------------------------

def _seed_topics(db_path, topics):
    """Seed one politician with `count` claims per topic (topics: dict)."""
    init_db(db_path)
    db = get_db(db_path)
    db.execute("INSERT INTO parties (name, short_name, coalition_status) VALUES ('Test','T','coalition')")
    db.execute("INSERT INTO tracked_politicians (id, name, party, relationship_type) VALUES (1,'Aļģis','Test','tracked')")
    did = 100
    for topic, n in topics.items():
        for _ in range(n):
            db.execute("INSERT INTO documents (id, platform, source_url, content, content_hash, scraped_at) VALUES (?, 'web', ?, 'x', ?, '2026-05-27')",
                       (did, f"https://e.lv/{did}", f"h{did}"))
            db.execute("INSERT INTO claims (opponent_id, document_id, topic, stance, source_url, stated_at, claim_type) VALUES (1,?,?,'s',?,'2026-05-27','position')",
                       (did, topic, f"https://e.lv/{did}"))
            did += 1
    db.commit()
    return db


def test_weekly_rest_topics_line_lists_topics_outside_top4(tmp_path):
    from src.briefs import generate_weekly_brief
    db_path = str(tmp_path / "t.db")
    _seed_topics(db_path, {"A": 6, "B": 5, "C": 4, "D": 3, "E": 2, "F": 1})
    md = generate_weekly_brief(db_path, week_start="2026-05-26", chart_dir=str(tmp_path / "imgs"))
    assert "### E —" not in md and "### F —" not in md
    rest = [ln for ln in md.splitlines() if ln.startswith("**Pārējās tēmas")]
    assert len(rest) == 1, md
    # E (2) and F (1) fall under the ≥3 threshold → folded into one count
    assert "un vēl 2 tēmas ar 1–2 pozīcijām (3 pozīcijas kopā)" in rest[0]
    assert "E (2)" not in rest[0]
    assert "A (" not in rest[0]  # top-4 topics never repeat in the rest line


def test_weekly_rest_topics_names_topics_with_3plus(tmp_path):
    from src.briefs import generate_weekly_brief
    db_path = str(tmp_path / "t.db")
    _seed_topics(db_path, {"A": 6, "B": 5, "C": 4, "D": 3, "E": 3, "F": 1})
    md = generate_weekly_brief(db_path, week_start="2026-05-26", chart_dir=str(tmp_path / "imgs"))
    rest = [ln for ln in md.splitlines() if ln.startswith("**Pārējās tēmas")][0]
    assert rest == "**Pārējās tēmas:** E (3) · un vēl 1 tēma ar 1–2 pozīcijām (1 pozīcija kopā)"


def test_weekly_rest_topics_line_absent_when_nothing_left(tmp_path):
    from src.briefs import generate_weekly_brief
    db_path = str(tmp_path / "t.db")
    _seed_topics(db_path, {"A": 2, "B": 1})
    md = generate_weekly_brief(db_path, week_start="2026-05-26", chart_dir=str(tmp_path / "imgs"))
    assert "Pārējās tēmas" not in md


def test_weekly_pretrunas_only_with_confirmed_rows(tmp_path):
    from src.briefs import generate_weekly_brief
    db_path = str(tmp_path / "t.db")
    db = _seed_topics(db_path, {"A": 2})
    md = generate_weekly_brief(db_path, week_start="2026-05-26", chart_dir=str(tmp_path / "imgs"))
    assert "## Pretrunas" not in md

    ids = [r[0] for r in db.execute("SELECT id FROM claims ORDER BY id").fetchall()]
    db.execute("INSERT INTO contradictions (opponent_id, claim_old_id, claim_new_id, topic, summary, severity, confirmed, detected_at) "
               "VALUES (1, ?, ?, 'A', 'Vispirms par, tad pret.', 'reversal', 1, '2026-05-28 10:00:00')", (ids[0], ids[1]))
    db.execute("INSERT INTO contradictions (opponent_id, claim_old_id, claim_new_id, topic, summary, severity, confirmed, detected_at) "
               "VALUES (1, ?, ?, 'A', 'NEAPSTIPRINĀTA', 'reversal', 0, '2026-05-28 10:00:00')", (ids[0], ids[1]))
    db.commit()
    md = generate_weekly_brief(db_path, week_start="2026-05-26", chart_dir=str(tmp_path / "imgs"))
    assert "## Pretrunas" in md
    assert "Vispirms par, tad pret." in md
    assert "NEAPSTIPRINĀTA" not in md
    assert "reversal" not in md  # enum never leaks; LV label instead
    assert "reversija" in md
    assert "contradictions=1" in md


def test_weekly_day_links_only_for_published_dailies(tmp_path):
    from src.briefs import generate_weekly_brief
    db_path = str(tmp_path / "t.db")
    db = _seed_topics(db_path, {"A": 2})
    md = generate_weekly_brief(db_path, week_start="2026-05-26", chart_dir=str(tmp_path / "imgs"))
    assert "Dienu pārskati" not in md

    for d in ("2026-05-26", "2026-05-27", "2026-05-29"):
        db.execute("INSERT INTO context_notes (opponent_id, note_type, topic, content, created_at) "
                   "VALUES (NULL, 'daily_brief', ?, ?, ?)",
                   (f"dienas analīze {d}", f"# Dienas analīze — {d}\n\nx", f"{d} 23:00:00"))
    # only two of the three are approved for publishing
    db.execute("INSERT INTO publish_approvals (subject_key, approved_at) VALUES ('2026-05-26', 'x')")
    db.execute("INSERT INTO publish_approvals (subject_key, approved_at) VALUES ('2026-05-29', 'x')")
    db.commit()
    md = generate_weekly_brief(db_path, week_start="2026-05-26", chart_dir=str(tmp_path / "imgs"))
    lines = [ln for ln in md.splitlines() if ln.startswith("**Dienu pārskati")]
    assert len(lines) == 1, md
    assert "[O.](/blog/2026-05-26.html)" in lines[0]  # 2026-05-26 is a Tuesday
    assert "[Pk.](/blog/2026-05-29.html)" in lines[0]
    assert "2026-05-27" not in lines[0]
