"""Hermetic tests for src/render/focus.py (Uzmanības centrā composite)."""
import sqlite3
from datetime import date
from pathlib import Path

SCHEMA = (Path(__file__).resolve().parents[1] / "src" / "schema.sql").read_text(encoding="utf-8")


def make_db() -> sqlite3.Connection:
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.executescript(SCHEMA)
    return db


def seed_pol(db, pid, name, party=None, rel="tracked"):
    db.execute(
        "INSERT INTO tracked_politicians (id, name, party, relationship_type) VALUES (?,?,?,?)",
        (pid, name, party, rel),
    )


def seed_party(db, name, short, status):
    db.execute(
        "INSERT INTO parties (name, short_name, coalition_status) VALUES (?,?,?)",
        (name, short, status),
    )


def seed_claim(db, pid, topic, sal, quote=None, days_ago=1, url="https://x.com/t/1"):
    db.execute(
        "INSERT INTO claims (opponent_id, topic, stance, confidence, salience, quote,"
        " stated_at, claim_type, source_url)"
        " VALUES (?,?,?,0.8,?,?, DATETIME('now', ?), 'position', ?)",
        (pid, topic, f"stance par {topic}", sal, quote, f"-{days_ago} days", url),
    )


def test_hot_topic_salience_weighted_beats_raw_count():
    """3 poz. ar sal 0.9 (skors 3+3.6=6.6) uzvar 5 poz. ar sal 0.3 (5+1.2=6.2)."""
    from src.render.focus import _hot_topic
    db = make_db()
    seed_pol(db, 1, "Anna Bērza", "Partija A")
    seed_pol(db, 2, "Jānis Ozols", "Partija B")
    for i in range(5):
        seed_claim(db, 1, "Budžets", 0.3, url=f"https://x.com/b/{i}")
    for i in range(3):
        seed_claim(db, 2, "Vēlēšanas", 0.9, quote="X" * 60, url=f"https://x.com/v/{i}")
    hot = _hot_topic(db)
    assert hot["topic"] == "Vēlēšanas"


def test_hot_topic_excludes_audience_accounts():
    from src.render.focus import _hot_topic
    db = make_db()
    seed_pol(db, 1, "Anna Bērza", "Partija A")
    seed_pol(db, 9, "LETA", None, rel="journalist")
    seed_claim(db, 1, "Budžets", 0.5, quote="Y" * 50)
    for i in range(9):
        seed_claim(db, 9, "Sports", 0.9, url=f"https://x.com/s/{i}")
    assert _hot_topic(db)["topic"] == "Budžets"


def test_hot_topic_quotes_verbatim_one_per_politician():
    from src.render.focus import _hot_topic
    db = make_db()
    seed_pol(db, 1, "Anna Bērza", "Partija A")
    typo_quote = "Steidamas izmaiņas ar kļūdu tekstā, kas paliek kā ir!!"
    seed_claim(db, 1, "Vēlēšanas", 0.9, quote=typo_quote, url="https://x.com/q/1")
    seed_claim(db, 1, "Vēlēšanas", 0.8, quote="Otrs citāts tam pašam politiķim garumā ok", url="https://x.com/q/2")
    hot = _hot_topic(db)
    assert [q["quote"] for q in hot["quotes"]] == [typo_quote]  # verbatim + 1/politiķi


def test_hot_topic_coalition_bar_counts_all_positions_not_just_quotes():
    from src.render.focus import _hot_topic
    db = make_db()
    seed_party(db, "Partija A", "PA", "coalition")
    seed_party(db, "Partija B", "PB", "opposition")
    seed_pol(db, 1, "Anna Bērza", "Partija A")
    seed_pol(db, 2, "Jānis Ozols", "Partija B")
    seed_pol(db, 3, "Zenta Liepa", None)  # bezpartejiska → joslā neskaitās
    seed_claim(db, 1, "Vēlēšanas", 0.9, quote="Q" * 50, url="https://x.com/1")
    seed_claim(db, 1, "Vēlēšanas", 0.2, url="https://x.com/2")   # bez quote — joslā TOMĒR skaitās
    seed_claim(db, 2, "Vēlēšanas", 0.4, url="https://x.com/3")
    seed_claim(db, 3, "Vēlēšanas", 0.4, url="https://x.com/4")
    hot = _hot_topic(db)
    assert (hot["koal_n"], hot["opoz_n"]) == (2, 1)


def test_hot_topic_and_quote_of_day_empty_db_return_none():
    from src.render.focus import _hot_topic, _quote_of_day
    db = make_db()
    assert _hot_topic(db) is None
    assert _quote_of_day(db) is None


def test_quote_of_day_falls_back_to_7d_window():
    from src.render.focus import _quote_of_day
    db = make_db()
    seed_pol(db, 1, "Anna Bērza", "Partija A")
    seed_claim(db, 1, "Budžets", 0.9, quote="Vakardienas spēcīgais citāts pietiekamā garumā", days_ago=3)
    q = _quote_of_day(db)
    assert q and q["quote"].startswith("Vakardienas")


def test_fresh_tensions_filters_14d_window_and_limit():
    from src.render.focus import _fresh_tensions
    old = {"created_at": "2026-01-01 10:00:00"}
    new1 = {"created_at": "2026-07-06 10:00:00", "source_name": "A", "target_name": "B"}
    new2 = {"created_at": "2026-07-05 10:00:00", "source_name": "C", "target_name": "D"}
    assert _fresh_tensions([old], 3, today=date(2026, 7, 7)) == []
    assert _fresh_tensions([new1, new2, old], 3, today=date(2026, 7, 7)) == [new1, new2]
    assert _fresh_tensions([new1, new2], 1, today=date(2026, 7, 7)) == [new1]
    assert _fresh_tensions([new1, new2], 3, exclude=new1, today=date(2026, 7, 7)) == [new2]


HOT = {"topic": "Vēlēšanas", "quotes": [{"source_url": "https://x.com/v/0"}]}
CON_FRESH = {"detected_at": "2026-07-06 17:40:18", "id": 42}
CON_OLD = {"detected_at": "2026-05-01 10:00:00", "id": 7}
TEN = {"created_at": "2026-07-05 10:00:00", "source_name": "A", "target_name": "B"}
QOD = {"quote": "Dienas citāts", "source_url": "https://x.com/q/9"}
TODAY = date(2026, 7, 7)


def _c_kinds(focus):
    return [s["kind"] for s in focus["slot_c_items"]]


def test_assemble_fresh_contradiction_then_c_stack():
    from src.render.focus import assemble_focus
    f = assemble_focus(HOT, [CON_FRESH, CON_OLD], [TEN], QOD, today=TODAY)
    assert f["slot_b"]["kind"] == "contradiction" and f["slot_b"]["item"]["id"] == 42
    assert _c_kinds(f) == ["tension", "quote"]  # citāts vienmēr pēdējais


def test_assemble_stale_contradiction_promotes_tension_to_b():
    from src.render.focus import assemble_focus
    f = assemble_focus(HOT, [CON_OLD], [TEN], QOD, today=TODAY)
    assert f["slot_b"]["kind"] == "tension"
    assert _c_kinds(f) == ["quote"]  # B spriedze neatkārtojas C stekā


def test_assemble_only_quote_goes_to_b():
    from src.render.focus import assemble_focus
    f = assemble_focus(HOT, [CON_OLD], [], QOD, today=TODAY)
    assert f["slot_b"]["kind"] == "quote"
    assert f["slot_c_items"] == []


def test_assemble_quote_never_duplicates_hot_topic_quote():
    from src.render.focus import assemble_focus
    dup = {"quote": "x", "source_url": "https://x.com/v/0"}  # jau A slotā
    f = assemble_focus(HOT, [CON_OLD], [], dup, today=TODAY)
    assert f["slot_b"] is None and f["slot_c_items"] == []


def test_assemble_c_stack_caps_three_tensions_quote_last():
    from src.render.focus import assemble_focus
    tensions = [
        {"created_at": f"2026-07-0{d} 10:00:00", "source_name": "A", "target_name": "B"}
        for d in (6, 5, 4, 3, 2)
    ]
    f = assemble_focus(HOT, [CON_FRESH], tensions, QOD, today=TODAY)
    assert _c_kinds(f) == ["tension", "tension", "tension", "quote"]
    assert [s["item"]["created_at"][:10] for s in f["slot_c_items"][:3]] == [
        "2026-07-06", "2026-07-05", "2026-07-04"]


def test_assemble_b_tension_excluded_from_c_stack():
    from src.render.focus import assemble_focus
    t1 = {"created_at": "2026-07-06 10:00:00", "source_name": "A", "target_name": "B"}
    t2 = {"created_at": "2026-07-05 10:00:00", "source_name": "C", "target_name": "D"}
    f = assemble_focus(HOT, [CON_OLD], [t1, t2], QOD, today=TODAY)
    assert f["slot_b"]["item"] is t1
    assert [s["item"] for s in f["slot_c_items"] if s["kind"] == "tension"] == [t2]


def test_focus_used_urls_reads_c_stack_quote():
    from src.render.focus import _focus_used_urls
    focus = {"hot": {"quotes": [{"source_url": "https://x.com/hot/1"}]},
             "slot_b": None,
             "slot_c_items": [
                 {"kind": "tension", "item": {"source_name": "A"}},
                 {"kind": "quote", "item": {"source_url": "https://x.com/q/9"}},
             ]}
    assert _focus_used_urls(focus) == {"https://x.com/hot/1", "https://x.com/q/9"}


# ── hero_feed (jauktais hero karuselis, spec 2026-07-07) ─────────────────

from datetime import timedelta


def _detected(days_ago: int) -> str:
    from src.db import today_lv
    return (today_lv() - timedelta(days=days_ago)).isoformat() + " 10:00:00"


def con(cid, days_ago):
    """Minimāla hero_cards pretrunu kartīte — hero_feed skatās tikai detected_at."""
    return {"id": cid, "detected_at": _detected(days_ago)}


def vote(vid, par=50, pret=30, att=5, result="Pieņemts", summary="Balsojums X", motif=None):
    return {"id": vid, "vote_date": "2026-06-18", "summary": summary, "motif": motif,
            "total_par": par, "total_pret": pret, "total_atturas": att, "result": result}


EMPTY_FOCUS = {"hot": None, "slot_b": None, "slot_c_items": []}


def test_hero_feed_fresh_contradictions_capped_at_two():
    from src.render.focus import hero_feed
    db = make_db()
    feed = hero_feed(db, [con(1, 1), con(2, 2), con(3, 3)], [], EMPTY_FOCUS)
    ids = [i["item"]["id"] for i in feed if i["kind"] == "contradiction"]
    assert ids == [1, 2]


def test_hero_feed_stale_contradictions_keep_one_anchor():
    from src.render.focus import hero_feed
    db = make_db()
    feed = hero_feed(db, [con(1, 60), con(2, 90)], [], EMPTY_FOCUS)
    ids = [i["item"]["id"] for i in feed if i["kind"] == "contradiction"]
    assert ids == [1]


def test_hero_feed_votes_filter_zero_ballots_and_dedup_summary():
    from src.render.focus import hero_feed
    db = make_db()
    votes = [
        vote(1, par=0, pret=0, att=0, summary="Kvoruma reģistrācija"),  # 0 balsis → ārā
        vote(2, summary="Grozījumi likumā"),
        vote(3, summary="Grozījumi likumā"),                            # dublēta summary → ārā
        vote(4, summary="Cits balsojums"),
        vote(5, summary="Trešais balsojums"),                           # limit 2 → ārā
    ]
    feed = hero_feed(db, [], votes, EMPTY_FOCUS)
    ids = [i["item"]["id"] for i in feed if i["kind"] == "vote"]
    assert ids == [2, 4]


def test_hero_feed_vote_without_result_skipped():
    from src.render.focus import hero_feed
    db = make_db()
    feed = hero_feed(db, [], [vote(1, result=None)], EMPTY_FOCUS)
    assert feed == []


def test_hero_feed_positions_dedup_focus_urls_and_one_per_politician():
    from src.render.focus import hero_feed
    db = make_db()
    seed_pol(db, 1, "Anna Bērza", "Partija A")
    seed_pol(db, 2, "Jānis Ozols", "Partija B")
    seed_claim(db, 1, "Budžets", 0.9, quote="A" * 50, url="https://x.com/hot/1")  # jau kompozītā
    seed_claim(db, 1, "Vēlēšanas", 0.8, quote="B" * 50, url="https://x.com/a/2")
    seed_claim(db, 1, "Nodokļi", 0.7, quote="C" * 50, url="https://x.com/a/3")    # 2. tam pašam politiķim → ārā
    seed_claim(db, 2, "Budžets", 0.6, quote="D" * 50, url="https://x.com/b/1")
    focus = {"hot": {"quotes": [{"source_url": "https://x.com/hot/1"}]},
             "slot_b": None, "slot_c_items": []}
    feed = hero_feed(db, [], [], focus)
    pos = [i["item"] for i in feed if i["kind"] == "position"]
    assert [p["source_url"] for p in pos] == ["https://x.com/a/2", "https://x.com/b/1"]


def test_hero_feed_position_skips_slot_quote_url():
    from src.render.focus import hero_feed
    db = make_db()
    seed_pol(db, 1, "Anna Bērza", "Partija A")
    seed_claim(db, 1, "Budžets", 0.9, quote="A" * 50, url="https://x.com/q/9")
    focus = {"hot": None, "slot_b": {"kind": "quote", "item": {"source_url": "https://x.com/q/9"}},
             "slot_c_items": []}
    feed = hero_feed(db, [], [], focus)
    assert [i for i in feed if i["kind"] == "position"] == []


def test_hero_feed_interleaves_and_caps_at_six():
    from src.render.focus import hero_feed
    db = make_db()
    for pid in (1, 2, 3):
        seed_pol(db, pid, f"Politiķis {pid}", "Partija A")
        seed_claim(db, pid, "Budžets", 0.9, quote="Q" * 50, url=f"https://x.com/p/{pid}")
    cons = [con(1, 1), con(2, 2)]
    votes = [vote(1, summary="Pirmais"), vote(2, summary="Otrais")]
    feed = hero_feed(db, cons, votes, EMPTY_FOCUS)
    kinds = [i["kind"] for i in feed]
    assert kinds == ["contradiction", "position", "vote",
                     "contradiction", "position", "vote"]  # sāk ar pretrunu; pos_limit=6-2-2=2


def test_hero_feed_position_gets_third_slot_when_others_underfill():
    from src.render.focus import hero_feed
    db = make_db()
    for pid in (1, 2, 3, 4):
        seed_pol(db, pid, f"Politiķis {pid}", "Partija A")
        seed_claim(db, pid, "Budžets", 0.9, quote="Q" * 50, url=f"https://x.com/p/{pid}")
    feed = hero_feed(db, [con(1, 1)], [vote(1)], EMPTY_FOCUS)
    kinds = [i["kind"] for i in feed]
    assert kinds.count("position") == 3 and len(feed) == 5


def test_hero_feed_all_empty_returns_empty():
    from src.render.focus import hero_feed
    db = make_db()
    assert hero_feed(db, [], [], EMPTY_FOCUS) == []
