"""Nedēļas stāstu kandidāti (spec 2026-11-01 § 2)."""
from src.db import init_db, get_db

WEEK = "2026-05-25"  # pirmdiena; nedēļa 05-25..05-31


def _db(tmp_path):
    tmp_path.mkdir(parents=True, exist_ok=True)  # testi padod tmp_path / "a"
    path = str(tmp_path / "t.db")
    init_db(path)
    db = get_db(path)
    db.execute("INSERT INTO parties (name, short_name, coalition_status) VALUES ('Jaunā Vienotība','JV','coalition')")
    for pid, name, rel in ((1, "Aļģis Bērziņš", "tracked"), (2, "Cits Kalniņš", "tracked"),
                           (3, "Žurnālists Ozols", "journalist"), (4, "Vecais Liepa", "inactive")):
        db.execute("INSERT INTO tracked_politicians (id, name, party, relationship_type) "
                   "VALUES (?,?,'Jaunā Vienotība',?)", (pid, name, rel))
    db.commit()
    return db


_DID = [1000]


def _claim(db, pid, topic, day, reasoning=None):
    _DID[0] += 1
    did = _DID[0]
    db.execute("INSERT INTO documents (id, platform, source_url, content, content_hash, scraped_at) "
               "VALUES (?, 'web', ?, 'x', ?, ?)", (did, f"https://e.lv/{did}", f"h{did}", day))
    cur = db.execute(
        "INSERT INTO claims (opponent_id, document_id, topic, stance, source_url, stated_at, "
        "claim_type, reasoning) VALUES (?,?,?,'s',?,?,'position',?)",
        (pid, did, topic, f"https://e.lv/{did}", day, reasoning))
    return cur.lastrowid


def _kinds(cands, kind):
    return [c for c in cands if c["kind"] == kind]


def _surge_db(tmp_path, week_n, prior_n):
    db = _db(tmp_path)
    for i in range(week_n):
        _claim(db, 1, "Korupcija un KNAB", "2026-05-27")
    for i in range(prior_n):  # iepriekšējās 4 nedēļas: 04-27..05-24
        _claim(db, 1, "Korupcija un KNAB", "2026-05-10")
    db.commit()
    return db


def test_topic_surge_needs_eight_positions(tmp_path):
    from src.briefs import weekly_story_candidates
    assert not _kinds(weekly_story_candidates(_surge_db(tmp_path / "a", 7, 0), WEEK), "topic_surge")
    assert _kinds(weekly_story_candidates(_surge_db(tmp_path / "b", 8, 0), WEEK), "topic_surge")


def test_topic_surge_needs_double_the_four_week_average(tmp_path):
    from src.briefs import weekly_story_candidates
    # 19 pret vidēji 10 (40/4) = ×1,9 → nav; 20 pret 10 = ×2,0 → ir
    assert not _kinds(weekly_story_candidates(_surge_db(tmp_path / "a", 19, 40), WEEK), "topic_surge")
    surge = _kinds(weekly_story_candidates(_surge_db(tmp_path / "b", 20, 40), WEEK), "topic_surge")
    assert surge and surge[0]["topic"] == "Korupcija un KNAB"


def test_topic_surge_without_history_counts_at_eight(tmp_path):
    from src.briefs import weekly_story_candidates
    (c,) = _kinds(weekly_story_candidates(_surge_db(tmp_path, 8, 0), WEEK), "topic_surge")
    assert "8" in c["fact"] and len(c["claim_ids"]) == 8


def test_needs_review_never_counts(tmp_path):
    from src.briefs import weekly_story_candidates
    db = _db(tmp_path)
    for _ in range(7):
        _claim(db, 1, "Korupcija un KNAB", "2026-05-27")
    nr = _claim(db, 1, "Korupcija un KNAB", "2026-05-27", reasoning="NEEDS_REVIEW: x")
    db.commit()
    cands = weekly_story_candidates(db, WEEK)
    assert not _kinds(cands, "topic_surge")
    assert all(nr not in c["claim_ids"] for c in cands)


def test_published_contradiction_in_routine_window(tmp_path):
    from src.briefs import weekly_story_candidates
    db = _db(tmp_path)
    old = _claim(db, 1, "Budžets", "2026-03-01")
    new = _claim(db, 1, "Budžets", "2026-05-27")
    rows = [  # (confirmed, detected_at, withdrawn_at)
        (1, "2026-05-27 18:00:00", None),       # ir
        (None, "2026-06-01 02:00:00", None),    # mantota publicēta, svētdienas rutīna pēc pusnakts → ir
        (0, "2026-05-27 18:00:00", None),       # kandidāts → nav
        (-1, "2026-05-27 18:00:00", "2026-05-28"),  # atsaukta → nav
        (1, "2026-05-25 04:00:00", None),       # iepriekšējās nedēļas rutīnas diena → nav
    ]
    for conf, det, wd in rows:
        db.execute("INSERT INTO contradictions (opponent_id, claim_old_id, claim_new_id, topic, "
                   "summary, severity, confirmed, detected_at, withdrawn_at) "
                   "VALUES (1,?,?,'Budžets','Kopsavilkums --> x','reversal',?,?,?)",
                   (old, new, conf, det, wd))
    db.commit()
    got = _kinds(weekly_story_candidates(db, WEEK), "contradiction")
    assert len(got) == 2
    assert got[0]["claim_ids"] == [old, new]
    assert "Aļģis Bērziņš" in got[0]["fact"]


def test_tension_pair_needs_two_in_routine_week(tmp_path):
    from src.briefs import weekly_story_candidates
    db = _db(tmp_path)
    # UTC laiks: 2026-05-25 02:30 UTC = 05:30 LV → jau pirmdienas rutīnas diena;
    # bez 'localtime' 02:30 < 05:00 un rinda izkristu (tad būtu tikai 1 spriedze).
    for ts in ("2026-05-26 10:00:00", "2026-05-25 02:30:00"):
        db.execute("INSERT INTO political_tensions (source_pid, target_pid, topic, description, created_at) "
                   "VALUES (1, 2, 'Budžets', 'd', ?)", (ts,))
    db.execute("INSERT INTO political_tensions (source_pid, target_pid, topic, description, created_at) "
               "VALUES (2, 1, 'Budžets', 'd', '2026-05-26 10:00:00')")  # pretējā virzienā — viena
    db.commit()
    (c,) = _kinds(weekly_story_candidates(db, WEEK), "tension_pair")
    assert c["fact"].startswith("Aļģis Bērziņš → Cits Kalniņš")
    assert "2" in c["fact"]


def test_new_voice_excludes_inactive_and_audience(tmp_path):
    from src.briefs import weekly_story_candidates
    db = _db(tmp_path)
    _claim(db, 1, "A", "2026-05-27")           # 1: jauns
    _claim(db, 2, "A", "2026-05-27")
    _claim(db, 2, "A", "2026-05-10")           # 2: runāja 30 dienās → nav jauns
    _claim(db, 3, "A", "2026-05-27")           # žurnālists → nav
    _claim(db, 4, "A", "2026-05-27")           # inactive → nav
    db.commit()
    got = _kinds(weekly_story_candidates(db, WEEK), "new_voice")
    assert [c["fact"].split(" (")[0] for c in got] == ["Aļģis Bērziņš"]
    assert "1 pozīcija;" in got[0]["fact"]  # skaitļa saskaņa, ne «1 pozīcijas»


def test_followup_reads_both_forward_look_headings(tmp_path):
    from src.briefs import weekly_story_candidates
    db = _db(tmp_path)
    prev = ("# Nedēļas stāsti — 2026-05-18 līdz 2026-05-24\n\n## Stāsts\n\nx\n\n"
            "## Ko gaidīt\n\n- Otrdien, 26. maijā, Saeimas sēde.\n\n"
            "## Nedēļa skaitļos\n\n")
    db.execute("INSERT INTO context_notes (opponent_id, note_type, topic, content, created_at) "
               "VALUES (NULL, 'weekly_brief', 'nedēļas analīze 2026-05-18 līdz 2026-05-24', ?, "
               "'2026-05-25 09:00:00')", (prev,))
    db.commit()
    (c,) = _kinds(weekly_story_candidates(db, WEEK), "followup")
    assert c["fact"] == "- Otrdien, 26. maijā, Saeimas sēde."


def _vote_db(tmp_path, ballots, periods=True, totals=None):
    """Viens balsojums #1 (2026-05-27 10:00, dok. 123/Lp14) + ķēdes balsojums #2 bez šķelšanās."""
    from src.saeima.schema import init_saeima_tables
    db = _db(tmp_path)
    path = db.execute("PRAGMA database_list").fetchone()[2]
    init_saeima_tables(path)
    par = sum(n for f, v, n in ballots if v == "Par")
    pret = sum(n for f, v, n in ballots if v == "Pret")
    att = sum(n for f, v, n in ballots if v == "Atturas")
    if totals:
        par, pret, att = totals
    for vid, t, p, pr, a in ((1, "10:00", par, pret, att), (2, "11:00", 2, 0, 0)):
        db.execute("INSERT INTO saeima_votes (id, motif, vote_date, vote_time, total_par, total_pret, "
                   "total_atturas, total_nebalso, result, url, document_nr) "
                   "VALUES (?, 'Grozījumi likumā', '2026-05-27', ?, ?, ?, ?, 0, 'Pieņemts', ?, '123/Lp14')",
                   (vid, t, p, pr, a, f"u{vid}"))
    n = 0
    for faction, vote, count in ballots:
        for _ in range(count):
            n += 1
            db.execute("INSERT INTO saeima_individual_votes (vote_id, deputy_name, faction, vote) "
                       "VALUES (1, ?, ?, ?)", (f"D{n}", faction, vote))
    for k in range(2):
        db.execute("INSERT INTO saeima_individual_votes (vote_id, deputy_name, faction, vote) "
                   "VALUES (2, ?, 'JV', 'Par')", (f"E{k}",))
    if periods:
        db.execute("INSERT INTO coalition_periods (valid_from_date, valid_from_time, factions) "
                   "VALUES ('2026-01-01', '00:00', 'JV,ZZS')")
    db.commit()
    return db


def test_vote_split_inside_faction(tmp_path):
    from src.briefs import weekly_story_candidates
    db = _vote_db(tmp_path, [("JV", "Par", 10), ("JV", "Pret", 2), ("ZZS", "Par", 8)])
    (c,) = _kinds(weekly_story_candidates(db, WEEK), "vote_split")
    assert c["vote_ids"] == [1, 2]          # visa document_nr ķēde (T14)
    assert "JV" in c["fact"] and "123/Lp14" in c["fact"]


def test_one_dissenter_is_not_a_split(tmp_path):
    from src.briefs import weekly_story_candidates
    db = _vote_db(tmp_path, [("JV", "Par", 10), ("JV", "Pret", 1), ("ZZS", "Par", 8)])
    assert not _kinds(weekly_story_candidates(db, WEEK), "vote_split")


def test_coalition_faction_against_its_bloc(tmp_path):
    from src.briefs import weekly_story_candidates
    db = _vote_db(tmp_path, [("JV", "Par", 20), ("ZZS", "Atturas", 8)])
    (c,) = _kinds(weekly_story_candidates(db, WEEK), "vote_split")
    assert "ZZS" in c["fact"] and "Atturas" in c["fact"]


def test_no_coalition_periods_names_no_bloc(tmp_path):
    from src.briefs import weekly_story_candidates
    db = _vote_db(tmp_path, [("JV", "Par", 20), ("ZZS", "Atturas", 8)], periods=False)
    assert not _kinds(weekly_story_candidates(db, WEEK), "vote_split")


def test_mismatched_vote_is_skipped(tmp_path):
    from src.briefs import weekly_story_candidates
    db = _vote_db(tmp_path, [("JV", "Par", 10), ("JV", "Pret", 3)], totals=(10, 4, 0))
    assert not _kinds(weekly_story_candidates(db, WEEK), "vote_split")


def test_daily_lead_marks_topic_that_led_three_days(tmp_path):
    """«atkārtojas» = tēma vadīja ≥3 dienas (2026-11-02: ar ≥2 atzīmi nesa 29 no
    35 punktiem valdības veidošanas nedēļā — atzīme neko neatšķīra)."""
    from src.briefs import weekly_story_candidates
    db = _db(tmp_path)
    a = _claim(db, 1, "Valdības veidošana", "2026-05-26")
    b = _claim(db, 2, "Valdības veidošana", "2026-05-28")
    c = _claim(db, 1, "Budžets", "2026-05-28")
    d = _claim(db, 2, "Valdības veidošana", "2026-05-30")
    e = _claim(db, 1, "Budžets", "2026-05-30")

    def daily(day, bullets):
        body = (f"# Dienas pārskats — {day}\n\n## Galvenais\n\n<!-- x -->\n\n" + "\n".join(bullets)
                + "\n\n## Aktīvākie politiķi\n\n- **Nav šis** ([e](https://e.lv/x))\n")
        db.execute("INSERT INTO context_notes (opponent_id, note_type, topic, content, created_at) "
                   "VALUES (NULL, 'daily_brief', ?, ?, ?)", (f"dienas analīze {day}", body, f"{day} 21:00:00"))

    def url(cid):
        return db.execute("SELECT source_url FROM claims WHERE id=?", (cid,)).fetchone()[0]

    daily("2026-05-26", [f"- **Kulbergs sola darba plānu.** Teksts ([e]({url(a)}))."])
    daily("2026-05-28", [f"- **Valdība vēl nav.** ([e]({url(b)}))", f"- **Budžets.** ([e]({url(c)}))"])
    daily("2026-05-30", [f"- **Sarunas turpinās.** ([e]({url(d)}))", f"- **Budžets atkal.** ([e]({url(e)}))"])
    daily("2026-05-20", ["- **Cita nedēļa.** x"])
    db.commit()
    got = _kinds(weekly_story_candidates(db, WEEK), "daily_lead")
    assert [g["fact"] for g in got] == ["Kulbergs sola darba plānu.", "Valdība vēl nav.", "Budžets.",
                                        "Sarunas turpinās.", "Budžets atkal."]
    # Valdības veidošana 3 dienas → atzīme; Budžets 2 dienas → nav
    assert [g["repeated"] for g in got] == [True, True, False, True, False]
    assert got[0]["topic"] == "Valdības veidošana" and got[0]["claim_ids"] == [a]


def test_skeleton_lists_candidates_and_defuses_comment_close(tmp_path):
    from src.briefs import generate_weekly_brief
    db = _surge_db(tmp_path, 8, 0)
    db.execute("UPDATE claims SET topic = 'Tēma --> x'")
    db.commit()
    path = db.execute("PRAGMA database_list").fetchone()[2]
    md = generate_weekly_brief(path, week_start=WEEK, chart_dir=str(tmp_path / "c"))
    start = md.index("<!-- STORY_CANDIDATES (")
    block = md[start:md.index("\n-->", start)]
    assert "[topic_surge] Tēma —> x: 8 pozīcijas" in block
    assert "-->" not in block


def test_skeleton_of_empty_week(tmp_path):
    from src.briefs import generate_weekly_brief
    db = _db(tmp_path)
    path = db.execute("PRAGMA database_list").fetchone()[2]
    md = generate_weekly_brief(path, week_start=WEEK, chart_dir=str(tmp_path / "c"))
    assert "<!-- STORY_CANDIDATES (0)" in md and "- kandidātu nav" in md
    assert "## Nedēļa skaitļos" in md
