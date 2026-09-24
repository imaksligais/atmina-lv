"""Lapas līmeņa dedup sākumlapā (2026-09-23).

Viena un tā pati pretruna/citāts nedrīkst atkārtoties hero karuselī,
«Svaigajā pretrunā» (focus slot_b), «Karstās tēmas» citātos un
«Dienas citātā». Prioritāte: karuselis > slot_b > pārējie citātu sloti;
sakritība pēc claim id / source_url / normalizēta teksta (_Shown).

Hermetiski testi uz in-memory DB + vienam pilnam render_dashboard
skrējienam tmp mapē (mazās datu dienas gadījums: DB ar tieši 1 pretrunu).
"""
import sqlite3
from datetime import timedelta
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


def seed_claim(db, pid, topic, sal, quote=None, days_ago=1, url="https://x.com/t/1",
               claim_id=None, stance=None):
    vals = (pid, topic, stance or f"stance par {topic}", sal, quote,
            f"-{days_ago} days", url)
    if claim_id is None:
        db.execute(
            "INSERT INTO claims (opponent_id, topic, stance, confidence, salience, quote,"
            " stated_at, claim_type, source_url)"
            " VALUES (?,?,?,0.8,?,?, DATETIME('now', ?), 'position', ?)",
            vals,
        )
    else:
        db.execute(
            "INSERT INTO claims (id, opponent_id, topic, stance, confidence, salience, quote,"
            " stated_at, claim_type, source_url)"
            " VALUES (?,?,?,?,0.8,?,?, DATETIME('now', ?), 'position', ?)",
            (claim_id, *vals),
        )
    return db.execute("SELECT MAX(id) FROM claims").fetchone()[0]


def _detected(days_ago: int) -> str:
    from src.db import today_lv
    return (today_lv() - timedelta(days=days_ago)).isoformat() + " 10:00:00"


def con(cid, days_ago, **kw):
    """Minimāla pretrunas kartīte ar claim id / avotiem / citātiem dedupam."""
    d = {"id": cid, "detected_at": _detected(days_ago)}
    d.update(kw)
    return d


# ── _Shown reģistrs ──────────────────────────────────────────────────


def test_shown_matches_by_claim_id_url_and_text():
    from src.render.focus import _Shown
    s = _Shown()
    s.add_contradiction(con(
        1, 1, claim_old_id=10, claim_new_id=20,
        old_source="https://a.lv/1", new_source="https://b.lv/2",
        old_quote="Vecā nostāja  ar   divām atstarpēm",
        new_quote="Jaunā nostāja",
    ))
    assert s.seen({"claim_id": 20})                       # claim id
    assert s.seen({"claim_id": 10})
    assert s.seen({"source_url": "https://b.lv/2"})       # avots
    assert s.seen({"quote": "vecā nostāja ar divām atstarpēm"})  # norm. teksts
    assert not s.seen({"claim_id": 99, "source_url": "https://c.lv/9",
                       "quote": "kas cits"})
    assert not s.seen({})                                  # bez atslēgām — nesakrīt


def test_shown_add_card_covers_quote_cards():
    from src.render.focus import _Shown
    s = _Shown()
    s.add_card({"claim_id": 5, "source_url": "https://x.com/p/5",
                "quote": "Citāts ar pietiekamu garumu šeit"})
    assert s.seen({"claim_id": 5})
    assert s.seen({"quote": "Citāts ar pietiekamu garumu šeit"})


# ── slot_b: pretruna ārpus karuseļa ──────────────────────────────────


def ten(days_ago):
    return {"created_at": _detected(days_ago), "source_name": "A", "target_name": "B"}


def test_slot_b_takes_first_fresh_contradiction_outside_hero():
    from src.render.focus import assemble_focus
    cons = [con(1, 1), con(2, 2), con(3, 3)]
    f = assemble_focus(None, cons, [], None, exclude_con_ids={1, 2})
    assert f["slot_b"]["kind"] == "contradiction" and f["slot_b"]["item"]["id"] == 3


def test_slot_b_falls_back_when_all_fresh_cons_in_hero():
    """Karuselī abas svaigās pretrunas → B slots iet pa esošo rezerves ceļu
    (spriedze → citāts), nevis rāda dubļa vai tukšu pretrunas karti."""
    from src.render.focus import assemble_focus
    cons = [con(1, 1), con(2, 2)]
    t = ten(2)
    qod = {"quote": "Dienas citāts", "source_url": "https://x.com/q/9"}
    f = assemble_focus(None, cons, [t], qod, exclude_con_ids={1, 2})
    assert f["slot_b"] == {"kind": "tension", "item": t}
    # bez spriedzes → dienas citāts; bez neviena → tukšs slots (veidne to izlaiž)
    f2 = assemble_focus(None, cons, [], qod, exclude_con_ids={1, 2})
    assert f2["slot_b"] == {"kind": "quote", "item": qod}
    f3 = assemble_focus(None, cons, [], None, exclude_con_ids={1, 2})
    assert f3["slot_b"] is None


def test_slot_b_prediction_matches_assemble_choice():
    """_slot_b_contradiction (render_dashboard paredzēšanai) un assemble_focus
    vienmēr izvēlas to pašu — citādi dedup reģistrs rīkotos pret citu karti."""
    from src.render.focus import _slot_b_contradiction, assemble_focus
    cons = [con(1, 1), con(2, 60), con(3, 3)]   # 2. ir vecs — nedrīkst būt B
    predicted = _slot_b_contradiction(cons, {1})
    f = assemble_focus(None, cons, [], None, exclude_con_ids={1})
    assert predicted["id"] == 3 == f["slot_b"]["item"]["id"]
    assert _slot_b_contradiction(cons, {1, 3}) is None


# ── citātu dedup pret jau rādīto ─────────────────────────────────────


def test_hot_topic_skips_quote_already_shown_by_claim_id():
    from src.render.focus import _Shown, _hot_topic
    db = make_db()
    seed_pol(db, 1, "Anna Bērza", "Partija A")
    shown_id = seed_claim(db, 1, "Vēlēšanas", 0.95, quote="Tas pats citāts, kas jau karuselī redzams",
                          url="https://x.com/v/1")
    seed_claim(db, 1, "Vēlēšanas", 0.8, quote="Cits citāts tam pašam politiķim garumā ok",
               url="https://x.com/v/2")
    s = _Shown()
    s.add_contradiction(con(9, 1, claim_new_id=shown_id))
    hot = _hot_topic(db, exclude=s)
    assert [q["quote"] for q in hot["quotes"]] == [
        "Cits citāts tam pašam politiķim garumā ok"]


def test_hot_topic_skips_quote_by_normalized_text():
    """Bez claim id (vecāks rinda) — tas pats verbatim citāts ar citu
    atstarpu skaitu joprojām tiek atpazīts un izlaists."""
    from src.render.focus import _Shown, _hot_topic
    db = make_db()
    seed_pol(db, 1, "Anna Bērza", "Partija A")
    seed_claim(db, 1, "Vēlēšanas", 0.95,
               quote="Svarīgs   citāts  ar   lūzumiem un garumu šeit klāt",
               url="https://x.com/v/1")
    s = _Shown()
    s.add_contradiction(con(9, 1, new_quote="Svarīgs citāts ar lūzumiem un garumu šeit klāt"))
    hot = _hot_topic(db, exclude=s)
    assert hot["quotes"] == []


def test_quote_of_day_falls_to_next_when_top_is_shown():
    from src.render.focus import _Shown, _quote_of_day
    db = make_db()
    seed_pol(db, 1, "Anna Bērza", "Partija A")
    top_id = seed_claim(db, 1, "Budžets", 0.99, quote="Top citāts, kas jau ir karuselī redzams šodien",
                        url="https://x.com/t/1")
    seed_claim(db, 1, "Budžets", 0.5, quote="Otrais citāts ar mazāku salience, bet pieejams",
               url="https://x.com/t/2")
    s = _Shown()
    s.add_contradiction(con(9, 0, claim_new_id=top_id))
    q = _quote_of_day(db, exclude=s)
    assert q and q["quote"].startswith("Otrais citāts")


def test_quote_of_day_returns_none_when_all_shown():
    from src.render.focus import _Shown, _quote_of_day
    db = make_db()
    seed_pol(db, 1, "Anna Bērza", "Partija A")
    only_id = seed_claim(db, 1, "Budžets", 0.9, quote="Vienīgais citāts šodien, jau redzams karuselī",
                         url="https://x.com/t/1")
    s = _Shown()
    s.add_contradiction(con(9, 0, claim_new_id=only_id))
    assert _quote_of_day(db, exclude=s) is None


def test_hero_feed_positions_skip_contradiction_claim_and_quote():
    """Karuselī redzamās pretrunas claim/citāts nedrīkst parādīties vēlreiz
    kā pozīcijas kartīte (jauns dedup virziens, 2026-09-23)."""
    from src.render.focus import _Shown, hero_feed
    db = make_db()
    seed_pol(db, 1, "Anna Bērza", "Partija A")
    seed_pol(db, 2, "Jānis Ozols", "Partija B")
    dup_id = seed_claim(db, 1, "Budžets", 0.99, quote="Kulberga citāts, kas jau pretrunas kartē",
                        url="https://x.com/a/1")
    seed_claim(db, 2, "Budžets", 0.8, quote="Ozola citāts — brīvs, drīkst karuselī" + "!" * 30,
               url="https://x.com/b/1")
    hero = [con(1, 1, claim_old_id=999, claim_new_id=dup_id,
                old_quote="vecs", new_quote="Kulberga citāts, kas jau pretrunas kartē")]
    s = _Shown()
    for c in hero:
        s.add_contradiction(c)
    feed = hero_feed(db, hero, [], {"hot": None, "slot_b": None, "slot_c_items": []},
                     shown=s)
    pos = [i["item"] for i in feed if i["kind"] == "position"]
    assert [p["source_url"] for p in pos] == ["https://x.com/b/1"]


def test_hero_feed_positions_skip_slot_b_contradiction_too():
    """B slota pretrunas citāts arī ir «jau redzams» — pozīciju atlase to
    respektē pat bez padota shown reģistra (u.c. vecā izsaukšanas forma)."""
    from src.render.focus import hero_feed
    db = make_db()
    seed_pol(db, 1, "Anna Bērza", "Partija A")
    seed_claim(db, 1, "Budžets", 0.99, quote="Pretrunas jaunā nostāja verbatim teksts šeit",
               url="https://x.com/a/1")
    focus = {"hot": None,
             "slot_b": {"kind": "contradiction",
                        "item": con(1, 1, new_quote="Pretrunas jaunā nostāja verbatim teksts šeit")},
             "slot_c_items": []}
    feed = hero_feed(db, [], [], focus)
    assert [i for i in feed if i["kind"] == "position"] == []


# ── mazās datu dienas: DB ar tieši 1 pretrunu ────────────────────────


def _seed_one_contradiction_db():
    """1 politiķis, 2 claims (vecs/jauks), 1 svaiga pretruna + 1 brīva pozīcija."""
    db = make_db()
    seed_pol(db, 1, "Anna Bērza", "Partija A")
    old_id = seed_claim(db, 1, "Budžets", 0.7, quote="Vecā nostāja pirms maiņas, garums ok te ir",
                        days_ago=40, url="https://a.lv/old")
    new_id = seed_claim(db, 1, "Budžets", 0.9, quote="Jaunā nostāja pēc maiņas, pilnīgi cita",
                        days_ago=1, url="https://a.lv/new")
    db.execute(
        "INSERT INTO contradictions (opponent_id, claim_old_id, claim_new_id, topic,"
        " summary, severity, detected_at, confirmed)"
        " VALUES (?,?,?,?,?,?, DATETIME('now'), 1)",
        (1, old_id, new_id, "Budžets", "Kopsavilkums par maiņu", "reversal"),
    )
    # brīva pozīcija karuseļa pozīciju un hot/qod atlasei
    seed_claim(db, 1, "Veselība", 0.6, quote="Neatkarīgs citāts citā tēmā, garumā ok šeit",
               days_ago=0, url="https://a.lv/other")
    db.commit()
    return db


def test_one_contradiction_data_level():
    """1 pretruna DB: karuselis to patur; slot_b ir None (nevis dublē);
    focus/hero_feed nesalūst."""
    from src.render.contradictions import _fetch_contradictions
    from src.render.focus import _hero_contradictions, _slot_b_contradiction, assemble_focus, hero_feed
    db = _seed_one_contradiction_db()
    contradictions = _fetch_contradictions(db)
    assert len(contradictions) == 1

    hero_cons = _hero_contradictions([dict(c) for c in contradictions])
    assert [c["id"] for c in hero_cons] == [contradictions[0]["id"]]
    assert _slot_b_contradiction(contradictions, {hero_cons[0]["id"]}) is None

    focus = assemble_focus(None, contradictions, [], None, exclude_con_ids={hero_cons[0]["id"]})
    assert focus["slot_b"] is None          # veidne slots izlaiž — nav tukšas kastes
    feed = hero_feed(db, [dict(c) for c in contradictions], [], focus)
    kinds = [i["kind"] for i in feed]
    assert kinds.count("contradiction") == 1  # tieši vienu reizi — karuselī


def _make_env():
    """Jinja env kā _orchestrator (filtri + globals), atlases versijai 'test'."""
    from jinja2 import Environment, FileSystemLoader
    from src.image_variants import variant_filename as _brief_image_variant
    from src.render._common import (
        TEMPLATES_DIR,
        _autolink_bills_filter,
        _lv_plural,
        _party_page_slug,
        _party_short_name,
        _safe_json_filter,
        _safe_url_filter,
        _salience_label,
    )
    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR), autoescape=True)
    env.filters["lv_date"] = (
        lambda s: f"{s[8:10]}.{s[5:7]}.{s[:4]}" if s and len(s) >= 10 and "-" in s else s or "")
    env.filters["safe_json"] = _safe_json_filter
    env.filters["safe_url"] = _safe_url_filter
    env.filters["autolink_bills"] = _autolink_bills_filter
    env.filters["image_variant"] = _brief_image_variant
    env.filters["lv_plural"] = _lv_plural
    env.filters["salience_label"] = _salience_label
    env.filters["party_page_slug"] = _party_page_slug
    env.globals["_party_short_name"] = _party_short_name
    env.globals["assets_version"] = "test"
    env.globals["bill_slugs"] = set()
    return env


def test_one_contradiction_full_page_renders_without_empty_box(tmp_path):
    """End-to-end: render_dashboard uz 1-pretrunas DB uzraksta index.html,
    kur pretruna parādās tieši vienā vietā un «≈ Svaiga pretruna» kastes NAV."""
    from src.render.contradictions import _fetch_contradictions
    from src.render.dashboard import render_dashboard

    db = _seed_one_contradiction_db()
    contradictions = _fetch_contradictions(db)
    out = tmp_path / "atmina"
    out.mkdir(parents=True)
    render_dashboard(
        _make_env(), db, out,
        stats={"politicians": 1, "parties": 0, "politicians_active": 1,
               "claims": 3, "contradictions": 1, "votes": 0,
               "claims_7d": 2, "votes_7d": 0, "tensions": 0, "documents": 0},
        contradictions=contradictions,
        votes=[], blog_posts=[], syntheses=[], analyses=[],
        trends_data={}, context_notes=[], days_until=365,
        rankings=None, tensions=[],
    )
    html = (out / "index.html").read_text(encoding="utf-8")
    cid = contradictions[0]["id"]
    # pretrunas kartīte ir karuselī (vienīgā vieta); B slota kastes nav
    assert "≈ Svaiga pretruna" not in html
    assert html.count(f"pretrunas/{cid}.html") == 1
    # pretrunas saturs (jaunā nostāja) — vienu reizi, nevis divās kartēs
    assert html.count("Jaunā nostāja pēc maiņas, pilnīgi cita") == 1
