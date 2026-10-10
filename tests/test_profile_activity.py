"""Profila vienotā aktivitāte, mēnešu grafiks un «Vēl nav datu» — end-to-end.

Plāns docs/plans/2026-10-07-profilu-dizains.md, B uzd. Nosauktās kļūmes:
- Laika līnija rāda katru balsojumu kā savu rindu ar «Par» — procedurāls
  balsojums izskatās pēc pozīcijas (T14), un simtiem rindu aizēd pozīcijas.
  Balsojumi jāsakļauj VIENĀ rindā par sēdes dienu, un cilnes skaitlis jāskaita
  ar tiem pašiem predikātiem (dienas, ne balsis).
- Profils bez neviena skaitļa izskatās salauzts (tukša josla) — vajag skaidru
  «Vēl nav datu» stāvokli, bet profilu NEslēpt.
- Mēnešu grafikā ieplūst balsojumi (simtiem mēnesī — sabojā mērogu) vai UTC
  kolonna; grafiks skaita tikai pozīcijas, uzstāšanās un jautājumus.

Renderēšanas fikstūra — tests/test_render_saeima_activity.py::_env.
"""
import re

from src.db import get_db, init_db, now_lv_dt
from src.render.politicians import render_politicians
from src.saeima.schema import init_saeima_bills, init_saeima_tables
from tests.test_render_saeima_activity import _env


def _db(tmp_path):
    db_path = str(tmp_path / "t.db")
    init_db(db_path)
    init_saeima_tables(db_path)
    init_saeima_bills(db_path)
    db = get_db(db_path)
    db.execute("INSERT INTO tracked_politicians (id,name,party,relationship_type) VALUES "
               "(1,'Anna Ozola','X','tracked'), (2,'Juris Kalns','X','tracked')")
    return db


def _vote(db, vid, day, ballot, pid=1, motif="Par likumprojektu"):
    db.execute("INSERT INTO saeima_votes (id, motif, vote_date, vote_time) VALUES (?,?,?,?)",
               (vid, motif, day, f"10:{vid % 60:02d}"))
    db.execute("INSERT INTO saeima_individual_votes (vote_id, deputy_name, vote, politician_id)"
               " VALUES (?, 'Ozola Anna', ?, ?)", (vid, ballot, pid))


def _render(db, tmp_path, pid=1, name="Anna Ozola", slug="anna-ozola"):
    out = tmp_path / "site" / "atmina"
    out.mkdir(parents=True, exist_ok=True)
    render_politicians(_env(), db, out, [{
        "id": pid, "name": name, "slug": slug, "profile_kind": "deputy",
        "role_label": "Saeimas deputāte", "party": "X", "x_handle": None,
    }], pid_to_syntheses={})
    return (out / "politiki" / f"{slug}.html").read_text(encoding="utf-8")


def _section(html, start_marker, end_marker):
    start = html.index(start_marker)
    return html[start:html.index(end_marker, start)]


def test_votes_collapse_to_one_timeline_row_per_session_day(tmp_path):
    db = _db(tmp_path)
    for vid, ballot in enumerate(["Par", "Par", "Pret", "Atturas", "Nebalsoja"], start=1):
        _vote(db, vid, "2026-09-03", ballot)
    _vote(db, 6, "2026-09-10", "Par")
    _vote(db, 7, "2026-09-10", "Pret")
    # Klātbūtne nav balsojums (Data Contract 4b) — dienas skaitā neieiet.
    _vote(db, 8, "2026-09-10", "Reģistrējies", motif="Deputātu klātbūtnes reģistrācija")
    # Diena, kurā ir TIKAI klātbūtne, nav sēdes balsojumu rinda.
    _vote(db, 9, "2026-09-17", "Reģistrējies", motif="Deputātu klātbūtnes reģistrācija")
    db.commit()

    html = _render(db, tmp_path)
    tl = _section(html, 'id="tab-timeline"', "<!-- Pozīcijas tab")

    rows = re.findall(r'<li class="pp-tl-item[^"]*" data-type="vote_day"', tl)
    assert len(rows) == 2, f"divas sēdes dienas → divas rindas, ne {len(rows)}"
    assert "5 balsojumi" in tl and "2 balsojumi" in tl
    # Neviena atsevišķa balsojuma rinda ar biļetena vērtību.
    assert ">Par<" not in tl and ">Pret<" not in tl
    assert "Par likumprojektu" not in tl
    # Rinda ved uz Saeimā cilni, kur atsevišķie balsojumi paliek.
    assert 'data-tab-link="saeima"' in tl
    # Cilnes skaitlis = sēdes dienas (tie paši predikāti), ne 7 balsis.
    assert re.search(r'id="tab-btn-timeline"[^>]*>.*?<span class="pp-tab-count">2</span>',
                     html, re.S)


def test_profile_without_any_data_shows_explicit_empty_state(tmp_path):
    db = _db(tmp_path)
    _vote(db, 1, "2026-09-03", "Par", pid=2)
    db.commit()

    empty = _render(db, tmp_path)
    # Profils NAV paslēpts: vārds, cilnes un paskaidrojums ir lapā.
    assert "<h1" in empty and "Anna Ozola" in empty
    assert 'role="tablist"' in empty
    assert "Vēl nav datu" in empty
    assert 'class="pp-stat"' not in empty

    full = _render(db, tmp_path, pid=2, name="Juris Kalns", slug="juris-kalns")
    assert "Vēl nav datu" not in full
    # Nulles flīzes nerāda: ir tikai balsojumu flīze.
    tiles = re.findall(r'<a class="pp-stat"[^>]*>', full) + re.findall(
        r'<div class="pp-stat"[^>]*>', full)
    assert len(tiles) == 1, tiles


def test_monthly_chart_counts_positions_speeches_questions_never_votes(tmp_path):
    db = _db(tmp_path)
    today = now_lv_dt().date()
    this_month = today.strftime("%Y-%m")
    day = f"{this_month}-01"
    for i in (1, 2):
        db.execute(
            "INSERT INTO documents (id,content,content_hash,platform,source_domain,"
            "source_url,scraped_at,published_at) VALUES (?,?,?,'web','delfi.lv',?,?,?)",
            (i, f"T{i}", f"h{i}", f"https://delfi.lv/{i}", day, day),
        )
        db.execute(
            "INSERT INTO claims (id,opponent_id,document_id,topic,stance,confidence,"
            "source_url,stated_at,claim_type) VALUES (?,1,?,'Ekonomika',?,0.9,?,?,'position')",
            (i, i, f"Pozīcija {i}", f"https://delfi.lv/{i}", day),
        )
    db.execute(
        "INSERT INTO saeima_debate_speeches (convocation, session_date, dkp_id, item_title,"
        " speaker_order, politician_id, speaker_name, duration_sec, source_url)"
        " VALUES (14, ?, 'D1', 'Punkts', 1, 1, 'Anna Ozola', 60, 'https://x/d.xml')", (day,))
    db.execute(
        "INSERT INTO saeima_questions (id, convocation, doc_nr, kind, title, status,"
        " submitted_date, source_url) VALUES (1, 14, '1/J14', 'jautajums', 'Par ceļiem',"
        " 'Atbildēts', ?, 'https://titania.saeima.lv/q/1')", (day,))
    db.execute("INSERT INTO saeima_question_politicians (question_id, politician_id, role)"
               " VALUES (1, 1, 'submitter')")
    for vid in range(1, 41):  # 40 balsojumi šomēnes — grafikā tiem NAV vietas
        _vote(db, vid, day, "Par")
    db.commit()

    html = _render(db, tmp_path)
    chart = _section(html, 'class="pp-chart"', "</figure>")

    months = re.findall(r'data-month="(\d{4}-\d{2})" data-counts="(\d+),(\d+),(\d+)"', chart)
    assert len(months) == 12, "pēdējie 12 mēneši"
    assert months[-1] == (this_month, "2", "1", "1")
    assert all(c == ["0", "0", "0"] for _, *c in months[:-1])
    # Leģenda — tieši trīs sērijas, balsojumu nav.
    legend = re.findall(r'<li class="pp-chart-key[^"]*"', chart)
    assert len(legend) == 3
    assert "alsojum" not in chart


def test_publications_tab_count_is_real_total_not_list_cap(tmp_path):
    # Nosauktā kļūme (2026-10-07): žurnālistam skaitļu josla «X ieraksti 498»,
    # bet cilne «Publikācijas 51» — cilne skaitīja LIMIT 50 sarakstu garumu.
    db = _db(tmp_path)
    db.execute("UPDATE tracked_politicians SET relationship_type='journalist' WHERE id=1")
    for i in range(60):
        cur = db.execute(
            "INSERT INTO documents (source_url, source_domain, platform, content, content_hash, scraped_at) "
            "VALUES (?, 'x.com', 'twitter', 'ieraksts', ?, ?)",
            (f"https://x.com/a/status/{i}", f"h{i}", f"2026-09-{1 + i % 28:02d} 10:00:00"))
        db.execute("INSERT INTO document_politicians (document_id, politician_id, role) "
                   "VALUES (?, 1, 'subject')", (cur.lastrowid,))
    db.commit()

    out = tmp_path / "site" / "atmina"
    out.mkdir(parents=True, exist_ok=True)
    render_politicians(_env(), db, out, [{
        "id": 1, "name": "Anna Ozola", "slug": "anna-ozola", "profile_kind": "journalist",
        "role_label": "Žurnāliste", "party": None, "x_handle": None,
    }], pid_to_syntheses={})
    html = (out / "politiki" / "anna-ozola.html").read_text(encoding="utf-8")

    assert re.search(r'id="tab-btn-publikacijas"[^>]*>.*?<span class="pp-tab-count">60</span>',
                     html, re.S)
    assert "X ieraksti (50 jaunākie no 60)" in html


def _render_kind(db, tmp_path, kind, pid=1, name="Anna Ozola", slug="anna-ozola"):
    out = tmp_path / "site" / "atmina"
    out.mkdir(parents=True, exist_ok=True)
    render_politicians(_env(), db, out, [{
        "id": pid, "name": name, "slug": slug, "profile_kind": kind,
        "role_label": "Politiķe", "party": "X", "x_handle": None,
    }], pid_to_syntheses={})
    return (out / "politiki" / f"{slug}.html").read_text(encoding="utf-8")


def test_saites_tab_count_is_real_total_not_list_cap(tmp_path):
    # Nosauktā kļūme (2026-10-07): spriedžu saraksts griests pie 20, un cilnes
    # skaitlis skaitīja saraksta garumu — 25 saitēm cilne rādīja «20».
    db = _db(tmp_path)
    for i in range(25):
        db.execute("INSERT INTO political_tensions (source_pid, target_pid, topic, description,"
                   " tension_type, created_at) VALUES (1, 2, 'Ekonomika', ?, 'spriedze', ?)",
                   (f"Spriedze {i}", f"2026-09-{1 + i:02d} 10:00:00"))
    db.commit()

    html = _render(db, tmp_path)
    assert re.search(r'id="tab-btn-saites"[^>]*>.*?<span class="pp-tab-count">25</span>',
                     html, re.S)
    saites = _section(html, 'id="tab-saites"', "Skatīt pilnajā kartē")
    assert "Rādīti jaunākie 20 no 25 uzbrukumu, spriedžu un atbalsta ierakstiem" in saites


def test_profile_with_only_news_opens_on_news_and_hides_zero_tabs(tmp_path):
    # Nosauktā kļūme (2026-10-07): 33 politiķiem nav ne pozīciju, ne balsojumu,
    # bet ir ziņas — profils atvērās tukšā Laika līnijā ar cilnēm «0», ziņas
    # bija paslēptas zem «Pozīcijas 0».
    db = _db(tmp_path)
    for i in range(3):
        cur = db.execute(
            "INSERT INTO documents (source_url, source_domain, platform, content, content_hash,"
            " scraped_at) VALUES (?, 'lsm.lv', 'web', ?, ?, '2026-09-20 10:00:00')",
            (f"https://lsm.lv/{i}", f"Ziņas teksts numur {i}", f"n{i}"))
        db.execute("INSERT INTO document_politicians (document_id, politician_id, role) "
                   "VALUES (?, 1, 'mentioned')", (cur.lastrowid,))
    db.commit()

    html = _render_kind(db, tmp_path, "politician")
    assert re.search(r'id="tab-btn-publikacijas"[^>]*aria-selected="true"', html)
    assert '<span class="pp-tab-count">0</span>' not in html
    assert 'id="tab-btn-timeline"' not in html and 'id="tab-btn-pozicijas"' not in html
    pubs = _section(html, 'id="tab-publikacijas"', "<!-- Saites tab")
    assert "Ziņas teksts numur 0" in pubs


def test_latest_activity_vote_renders_as_session_day_not_one_motif(tmp_path):
    # Nosauktā kļūme (2026-10-07, T14): ja jaunākais notikums ir balsojums,
    # «Pēdējā aktivitāte» rādīja viena balsojuma motīvu kā nostāju.
    db = _db(tmp_path)
    db.execute(
        "INSERT INTO documents (id,content,content_hash,platform,source_domain,source_url,"
        "scraped_at) VALUES (1,'T','h1','web','delfi.lv','https://delfi.lv/1','2026-09-01')")
    db.execute(
        "INSERT INTO claims (id,opponent_id,document_id,topic,stance,confidence,source_url,"
        "stated_at,claim_type) VALUES (1,1,1,'Ekonomika','Agrāka pozīcija',0.9,"
        "'https://delfi.lv/1','2026-09-01','position')")
    for vid, ballot in enumerate(["Par", "Pret", "Atturas"], start=1):
        _vote(db, vid, "2026-09-10", ballot, motif="Par procedūras priekšlikumu")
    _vote(db, 4, "2026-09-10", "Reģistrējies", motif="Deputātu klātbūtnes reģistrācija")
    db.commit()

    html = _render(db, tmp_path)
    # Citu signālu bloku šeit nav (nav pretrunu, viena pozīcija), tāpēc
    # griezums līdz Laika līnijas cilnei ir tikai šis bloks.
    block = _section(html, 'class="parskats-block parskats-block-activity"', "<!-- Timeline tab")
    assert "Saeimas sēde" in block and "3 balsojumi" in block
    assert "Par procedūras priekšlikumu" not in block
    assert ">Par<" not in block
    assert 'data-tab-link="saeima"' in block
