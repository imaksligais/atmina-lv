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
    assert "nostājas maiņa" in md  # site-wide vocabulary (2026-09-28), not «reversija»
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


def test_weekly_votes_stat_excludes_attendance_registrations(tmp_path):
    """WEEKLY_STATS votes= counts cast-ballot events only. A sitting stores two
    «Deputātu klātbūtnes reģistrācija» rows (quorum checks, 0/0/0 totals) next to
    the real votes; counting them inflated the public stat card (2026-09-13:
    «16 balsojumi» for a day with 14 votes). Same class as Data Contract #4b —
    attendance is never a vote."""
    from src.briefs import generate_weekly_brief
    from src.saeima.schema import init_saeima_tables

    db_path = str(tmp_path / "t.db")
    db = _seed(db_path)
    init_saeima_tables(db_path)
    db = get_db(db_path)
    rows = [
        ("Par likumprojektu X (1/Lp14)", "2026-05-28", "10:00:00", 50, 20, 5),
        ("Deputātu klātbūtnes reģistrācija", "2026-05-28", "10:01:00", 0, 0, 0),
        ("Par likumprojektu Y (2/Lp14)", "2026-05-28", "10:05:00", 60, 10, 0),
        ("Deputātu klātbūtnes reģistrācija", "2026-05-28", "16:00:00", 0, 0, 0),
    ]
    for i, (motif, d, t, par, pret, att) in enumerate(rows, start=1):
        db.execute(
            "INSERT INTO saeima_votes (id, motif, vote_date, vote_time, total_par, "
            "total_pret, total_atturas, total_nebalso, url) VALUES (?,?,?,?,?,?,?,0,?)",
            (i, motif, d, t, par, pret, att, f"https://titania.saeima.lv/v{i}"),
        )
    db.commit()

    md = generate_weekly_brief(db_path=db_path, week_start="2026-05-26")
    assert "votes=2 " in md, md.split("\n")[8:14]


# ---------------------------------------------------------------------------
# 2026-09-27 — weekly_vote_breakdown, īsāka pretrunas šūna, pagājušās nedēļas
# «Skats uz priekšu». Divos no trim nedēļas pārskatiem frakciju sadalījums bija
# pārstāstīts ar roku un jālabo pēc publicēšanas (#625: «pret balsoja ZZS un
# LPV (27)», kad Pret=27 bija ZZS 9 + LPV 5 + AS 4 + ārpusfrakciju 9).
# ---------------------------------------------------------------------------

def _seed_votes(db_path, votes, ballots):
    """votes: (id, motif, date, time, par, pret, att, document_nr);
    ballots: (vote_id, faction, vote, count)."""
    from src.saeima.schema import init_saeima_tables
    init_db(db_path)
    init_saeima_tables(db_path)
    db = get_db(db_path)
    db.execute("INSERT INTO parties (name, short_name, coalition_status) VALUES ('Jaunā Vienotība','JV','coalition')")
    db.execute("INSERT INTO parties (name, short_name, coalition_status) VALUES ('Latvija Pirmajā Vietā','LPV','opposition')")
    for vid, motif, d, t, par, pret, att, doc in votes:
        db.execute(
            "INSERT INTO saeima_votes (id, motif, vote_date, vote_time, total_par, total_pret, "
            "total_atturas, total_nebalso, result, url, document_nr) VALUES (?,?,?,?,?,?,?,0,'Pieņemts',?,?)",
            (vid, motif, d, t, par, pret, att, f"https://titania.saeima.lv/v{vid}", doc),
        )
    n = 0
    for vid, faction, vote, count in ballots:
        for _ in range(count):
            n += 1
            db.execute("INSERT INTO saeima_individual_votes (vote_id, deputy_name, faction, vote) VALUES (?,?,?,?)",
                       (vid, f"Deputāts {n}", faction, vote))
    db.commit()
    db.close()


def _vote_block(out, vote_id):
    """Lines of one vote entry: the '- #id' line plus its indented lines."""
    lines = out.splitlines()
    i = next(k for k, ln in enumerate(lines) if ln.startswith(f"- #{vote_id} "))
    block = [lines[i]]
    for ln in lines[i + 1:]:
        if not ln.startswith("  "):
            break
        block.append(ln)
    return block


def test_breakdown_names_the_no_faction_bucket(tmp_path):
    """#625 failure: deputies without a faction (NULL AND '') vanished from the
    faction split (the render query filters `faction IS NOT NULL AND != ''`), so
    «Pret 27» was attributed to two factions. They must appear as ONE named
    «ārpusfrakciju» bucket with both storage forms summed."""
    from src.briefs import weekly_vote_breakdown
    db_path = str(tmp_path / "t.db")
    _seed_votes(db_path,
                [(1, "Par likumprojektu X (1/Lp14)", "2026-09-24", "10:00:00", 3, 5, 0, "1/Lp14")],
                [(1, "JV", "Par", 3), (1, "LPV", "Pret", 1), (1, None, "Pret", 2), (1, "", "Pret", 2)])
    out = weekly_vote_breakdown(db_path, week_start="2026-09-21")
    factions = _vote_block(out, 1)[-1]
    assert "ārpusfrakciju 0/4/0/0" in factions, out
    assert "JV 3/0/0/0" in factions and "LPV 0/1/0/0" in factions
    assert factions.index("JV") < factions.index("LPV") < factions.index("ārpusfrakciju")
    assert "NESAKRĪT" not in out
    assert "Pārbaudīti balsojumi: 1 " in out


def test_breakdown_excludes_registration_by_prefix_only(tmp_path):
    """A '%reģistrācij%' filter would drop real votes such as «Civilstāvokļa
    aktu reģistrācijas likums»; only the «Deputātu klātbūtnes reģistrācija»
    quorum check (prefix) is not a vote."""
    from src.briefs import weekly_vote_breakdown
    db_path = str(tmp_path / "t.db")
    _seed_votes(db_path,
                [(1, "Deputātu klātbūtnes reģistrācija", "2026-09-24", "09:00:00", 0, 0, 0, None),
                 (2, "Grozījumi Civilstāvokļa aktu reģistrācijas likumā (7/Lp14), 2.lasījums",
                  "2026-09-24", "10:00:00", 2, 0, 0, "7/Lp14")],
                [(1, "JV", "Reģistrējies", 3), (2, "JV", "Par", 2)])
    out = weekly_vote_breakdown(db_path, week_start="2026-09-21")
    assert "Deputātu klātbūtnes reģistrācija" not in out
    assert "- #1 " not in out
    assert "Civilstāvokļa aktu reģistrācijas likumā" in out
    assert "Pārbaudīti balsojumi: 1 " in out


def test_breakdown_non_ballot_value_is_cits_not_nebalsoja(tmp_path):
    """Data Contract #4b: an attendance state ('Reģistrējies') scattered inside a
    real vote is not a ballot. Folding it into nebalsoja (the render query's
    `NOT IN (Par,Pret,Atturas)` bucket) would invent non-voters."""
    from src.briefs import weekly_vote_breakdown
    db_path = str(tmp_path / "t.db")
    _seed_votes(db_path,
                [(1, "Par likumprojektu X (1/Lp14)", "2026-09-24", "10:00:00", 2, 0, 0, "1/Lp14")],
                [(1, "JV", "Par", 2), (1, "JV", "Nebalsoja", 1), (1, "JV", "Reģistrējies", 2)])
    out = weekly_vote_breakdown(db_path, week_start="2026-09-21")
    assert "JV 2/0/0/1 (cits: 2)" in _vote_block(out, 1)[-1], out


def test_breakdown_warns_when_individual_rows_do_not_add_up(tmp_path):
    """A breakdown built from incomplete per-deputy rows must say so on the vote
    and in the header denominator; a complete one must not cry wolf."""
    from src.briefs import weekly_vote_breakdown
    db_path = str(tmp_path / "t.db")
    _seed_votes(db_path,
                [(1, "Par likumprojektu X (1/Lp14)", "2026-09-24", "10:00:00", 3, 1, 0, "1/Lp14"),
                 (2, "Par likumprojektu Y (2/Lp14)", "2026-09-24", "11:00:00", 2, 0, 1, "2/Lp14")],
                # vote 1: one Par row missing (2 of 3); vote 2 complete
                [(1, "JV", "Par", 2), (1, "LPV", "Pret", 1),
                 (2, "JV", "Par", 2), (2, "LPV", "Atturas", 1)])
    out = weekly_vote_breakdown(db_path, week_start="2026-09-21")
    assert "  ⚠ NESAKRĪT: individuālie Par 2 ≠ kopā 3" in _vote_block(out, 1)
    assert not any("NESAKRĪT" in ln for ln in _vote_block(out, 2))
    assert ("Pārbaudīti balsojumi: 2 (bez klātbūtnes reģistrācijām); "
            "individuālās balsis nesakrīt ar kopsummām: 1.") in out


def test_breakdown_groups_document_chain_in_time_order(tmp_path):
    """T14: a procedural chain (committee referral → reading) shares one
    document_nr. It must be read whole, so its votes sit under one heading in
    time order even when another bill's vote falls between them."""
    from src.briefs import weekly_vote_breakdown
    db_path = str(tmp_path / "t.db")
    _seed_votes(db_path,
                [(3, "Likumprojekts A (5/Lp14), 1.lasījums", "2026-09-24", "12:00:00", 1, 0, 0, "5/Lp14"),
                 (2, "Cits likums (6/Lp14)", "2026-09-24", "11:00:00", 1, 0, 0, "6/Lp14"),
                 (1, "Likumprojekts A (5/Lp14), nodošana komisijām", "2026-09-24", "10:00:00", 1, 0, 0, "5/Lp14"),
                 (4, "Par Saeimas paziņojumu", "2026-09-25", "09:00:00", 1, 0, 0, None)],
                [(1, "JV", "Par", 1), (2, "JV", "Par", 1), (3, "JV", "Par", 1), (4, "JV", "Par", 1)])
    out = weekly_vote_breakdown(db_path, week_start="2026-09-21")
    headings = [ln for ln in out.splitlines() if ln.startswith("## ")]
    assert headings == ["## 5/Lp14", "## 6/Lp14",
                        "## Bez dokumenta numura: Par Saeimas paziņojumu"], out
    chain = out.split("## 5/Lp14", 1)[1].split("## 6/Lp14", 1)[0]
    assert chain.index("- #1 ") < chain.index("- #3 ")
    assert "- #2 " not in chain


def test_weekly_skeleton_points_to_breakdown_only_when_votes(tmp_path):
    """The pointer tells the writer where faction numbers come from; it names
    the concrete week and is absent in a week without votes."""
    from src.briefs import generate_weekly_brief
    db_path = str(tmp_path / "t.db")
    _seed_votes(db_path,
                [(1, "Par likumprojektu X (1/Lp14)", "2026-09-24", "10:00:00", 1, 0, 0, "1/Lp14")],
                [(1, "JV", "Par", 1)])
    md = generate_weekly_brief(db_path, week_start="2026-09-21", chart_dir=str(tmp_path / "imgs"))
    assert 'weekly_vote_breakdown(week_start="2026-09-21")' in md
    md = generate_weekly_brief(db_path, week_start="2026-09-28", chart_dir=str(tmp_path / "imgs"))
    assert "weekly_vote_breakdown" not in md


def test_contradiction_excerpt_long_summary_is_cut_and_linked():
    """Contradiction #53 put 213 words, incl. its [Konteksts: …] block, into one
    table cell. The weekly cell is a ≤50-word preview + link; a newline or raw
    `|` inside it would split or shift the markdown table row."""
    from src.briefs import contradiction_excerpt
    lead = " ".join(f"vārds{i}" for i in range(70))
    summary = (f"vārds| {lead}\nun jaunu rindu [Konteksts: garš skaidrojums]"
               "\n\nOtrā rindkopa.")
    cell = contradiction_excerpt(summary, 53)
    text, link = cell.rsplit(" [pilnā pretruna]", 1)
    assert link == "(/pretrunas/53.html)"
    assert "Konteksts" not in cell and "Otrā rindkopa" not in cell
    assert "\n" not in cell and "|" not in cell
    assert text.endswith("…")
    assert len(text.split()) <= 50
    assert text.startswith("vārds/ vārds0 vārds1")


def test_contradiction_excerpt_short_summary_untouched():
    """A summary under the cap passes through whole — no «…» invented."""
    from src.briefs import contradiction_excerpt
    cell = contradiction_excerpt("Vispirms par, tad pret. [Konteksts: x]", 7)
    assert cell == "Vispirms par, tad pret. [pilnā pretruna](/pretrunas/7.html)"


def test_weekly_pretrunas_cell_uses_excerpt(tmp_path):
    """The generator, not only the helper, must emit the capped cell: one table
    row, no «Konteksts», link to the contradiction page."""
    from src.briefs import generate_weekly_brief
    db_path = str(tmp_path / "t.db")
    db = _seed_topics(db_path, {"A": 2})
    ids = [r[0] for r in db.execute("SELECT id FROM claims ORDER BY id").fetchall()]
    long = " ".join(f"v{i}" for i in range(120)) + "\n[Konteksts: skaidrojums | ar caurulīti]"
    cur = db.execute("INSERT INTO contradictions (opponent_id, claim_old_id, claim_new_id, topic, summary, severity, confirmed, detected_at) "
                     "VALUES (1, ?, ?, 'A', ?, 'reversal', 1, '2026-05-28 10:00:00')", (ids[0], ids[1], long))
    cid = cur.lastrowid
    db.commit()
    md = generate_weekly_brief(db_path, week_start="2026-05-26", chart_dir=str(tmp_path / "imgs"))
    rows = [ln for ln in md.split("## Pretrunas", 1)[1].splitlines() if ln.startswith("| Aļģis")]
    assert len(rows) == 1, md
    assert f"(/pretrunas/{cid}.html)" in rows[0]
    assert "Konteksts" not in rows[0] and "v119" not in rows[0] and "…" in rows[0]
    assert rows[0].count("|") == 7  # 6 cells → 7 pipes


def test_weekly_skeleton_carries_previous_forward_look(tmp_path):
    """A forward-look bullet is a promise to the reader; next week must check it.
    The previous brief is found by its SUBJECT topic, not created_at, and a
    `-->` in a bullet must not close the comment early."""
    from src.briefs import generate_weekly_brief
    db_path = str(tmp_path / "t.db")
    db = _seed_topics(db_path, {"A": 2})
    md = generate_weekly_brief(db_path, week_start="2026-05-26", chart_dir=str(tmp_path / "imgs"))
    assert "pagājušās nedēļas «Skats uz priekšu»" not in md

    prev = ("# Nedēļas analīze — 2026-05-19 līdz 2026-05-25\n\n## Nedēļas stāsts\n\n- nav šis\n\n"
            "## Skats uz priekšu\n\n- Otrdien, 26. maijā, Saeimas sēde --> x.\n"
            "- Ceturtdien, 28. maijā, komisijas termiņš.\n\n"
            "**Dienu pārskati:** [P.](/blog/2026-05-19.html)\n\n## Vizuālais brief\n\n- **Tēma:** y\n")
    # created_at is the NEXT week's first day — the lookup must still find it.
    db.execute("INSERT INTO context_notes (opponent_id, note_type, topic, content, created_at) "
               "VALUES (NULL, 'weekly_brief', 'nedēļas analīze 2026-05-19 līdz 2026-05-25', ?, "
               "'2026-05-26 01:10:00')", (prev,))
    db.commit()
    md = generate_weekly_brief(db_path, week_start="2026-05-26", chart_dir=str(tmp_path / "imgs"))
    start = md.index("<!-- AGENT: pagājušās nedēļas «Skats uz priekšu»")
    comment = md[start:md.index("-->", start) + 3]
    assert "- Otrdien, 26. maijā, Saeimas sēde" in comment
    assert "- Ceturtdien, 28. maijā, komisijas termiņš." in comment
    assert "nav šis" not in comment and "Tēma" not in comment
    assert "Dienu pārskati" not in comment
    assert comment.endswith("termiņš. -->")
