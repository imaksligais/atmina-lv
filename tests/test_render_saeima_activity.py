"""Saeimā cilnes aktivitātes bloki (amati, debates, jautājumi) — end-to-end.

Nosauktās kļūmes, ko šis tests ķer (plāns 2026-10-06-saeimas-aktivitate.md, 4. uzd.):
- beigušies amati sajaucas ar pašreizējiem (date_to IS NULL dalījums);
- titania dod «Deputāte» + vadošo amatu tai pašai institūcijai — rādām tikai
  vadošo, BET atgriešanās par ierindas locekli pēc vadības beigām paliek;
- pēdējo uzstāšanos / jautājumu saraksts nav ierobežots ar 10;
- debašu punkts linko uz neeksistējošu likumprojekta lapu;
- adresāta loma tiek ieskaitīta iesniegtajos jautājumos;
- politiķim bez datiem parādās tukši bloki.
"""
from jinja2 import Environment, FileSystemLoader

from src.db import get_db, init_db
from src.render._common import _lv_plural, _safe_json_filter, _safe_url_filter
from src.render.politicians import render_politicians
from src.saeima.schema import init_saeima_bills, init_saeima_tables


def _env():
    env = Environment(loader=FileSystemLoader("templates"), autoescape=True)
    env.filters["safe_url"] = _safe_url_filter
    env.filters["safe_json"] = _safe_json_filter
    env.filters["lv_date"] = (
        lambda s: f"{s[8:10]}.{s[5:7]}.{s[:4]}"
        if s and len(s) >= 10 and "-" in s else s or ""
    )
    env.filters["autolink_bills"] = lambda s, *a, **k: s
    env.filters["lv_plural"] = _lv_plural
    env.globals["assets_version"] = "test"
    return env


def _seed(db_path):
    init_db(db_path)
    init_saeima_tables(db_path)
    init_saeima_bills(db_path)
    db = get_db(db_path)
    db.execute("INSERT INTO tracked_politicians (id,name,party,relationship_type) "
               "VALUES (1,'Anna Ozola','X','tracked'), (2,'Juris Kalns','X','tracked')")

    def pos(level, body, position, d_from, d_to):
        db.execute(
            "INSERT INTO saeima_deputy_positions (convocation, politician_id, deputy_unid,"
            " deputy_name, level, body, position, date_from, date_to, source_url)"
            " VALUES (14, 1, 'U1', 'Ozola Anna', ?, ?, ?, ?, ?, 'https://titania/u1')",
            (level, body, position, d_from, d_to),
        )
    pos("10", "Deputāte Ozola Anna", "Deputāte", "2022-11-01", None)       # mandāts — nerāda
    pos("2", "Frakcija ZILĀ", "Deputāte", "2022-11-01", None)
    pos("3", "Budžeta komisija", "Deputāte", "2025-03-06", "2025-03-06")   # ietverts → izmet
    pos("3", "Budžeta komisija", "Priekšsēdētāja", "2025-03-06", "2026-06-09")
    pos("3", "Budžeta komisija", "Deputāte", "2026-06-09", None)           # atgriešanās → paliek
    pos("5", "Sporta apakškomisija", "Deputāte", "2026-06-18", None)       # ietverts → izmet
    pos("5", "Sporta apakškomisija", "Priekšsēdētāja ", "2026-06-18", None)
    pos("6", "Baltijas Asamblejas delegācija", "Deputāte", "2023-01-12", "2023-09-20")

    db.execute("INSERT INTO saeima_bills (document_nr, bill_type, title) "
               "VALUES ('1105/Lm14', 'Lm14', 'Grozījumi Likumā')")
    for i in range(1, 13):
        doc = {12: "1105/Lm14", 11: "999/Lm14"}.get(i)
        db.execute(
            "INSERT INTO saeima_debate_speeches (convocation, session_date, dkp_id,"
            " document_nr, item_title, speaker_order, politician_id, speaker_name,"
            " duration_sec, opinion, source_url)"
            " VALUES (14, ?, ?, ?, ?, 1, 1, 'Anna Ozola', ?, 'Pret', 'https://titania/d')",
            (f"2026-01-{i:02d}", f"DKP{i:02d}", doc, f"Punkts {i:02d}",
             420 if i == 1 else 300),
        )

    def question(qid, doc_nr, kind, title, role, date):
        db.execute(
            "INSERT INTO saeima_questions (id, convocation, doc_nr, kind, title, status,"
            " submitted_date, source_url) VALUES (?, 14, ?, ?, ?, 'Atbildēts', ?, ?)",
            (qid, doc_nr, kind, title, date, f"https://titania.saeima.lv/q/{qid}"),
        )
        db.execute("INSERT INTO saeima_question_politicians (question_id, politician_id, role)"
                   " VALUES (?, 1, ?)", (qid, role))
    question(1, "257/J14", "jautajums", "Par skolu tīklu (iesniegts 01.02.2026.)", "submitter", "2026-02-01")
    question(2, "258/J14", "jautajums", "Par ceļiem", "submitter", "2026-02-03")
    question(3, "40/P14", "pieprasijums", "Par ministra darbu", "submitter", "2026-02-02")
    db.execute("UPDATE saeima_questions SET result = 'Nodots Pieprasījumu komisijai; Noraidīts' WHERE id = 3")
    question(4, "300/J14", "jautajums", "Adresēts viņai", "addressee", "2026-02-04")

    # Juris: viens balsojums → Saeimā cilne ir, aktivitātes datu nav.
    db.execute("INSERT INTO saeima_votes (id, motif, vote_date, vote_time) "
               "VALUES (1, 'Par likumprojektu', '2026-01-05', '10:00')")
    db.execute("INSERT INTO saeima_individual_votes (vote_id, deputy_name, vote, politician_id)"
               " VALUES (1, 'Kalns Juris', 'Par', 2)")
    db.commit()
    return db


def _politician(pid, name, slug):
    return {"id": pid, "name": name, "slug": slug, "profile_kind": "deputy",
            "role_label": "Saeimas deputāts", "party": "X", "x_handle": None}


def _saeima_tab(html):
    start = html.index('id="tab-saeima"')
    return html[start:html.index("<!-- Komentāri-by tab", start)]


def test_saeima_activity_blocks_render_end_to_end(tmp_path):
    db = _seed(str(tmp_path / "t.db"))
    out = tmp_path / "site" / "atmina"
    out.mkdir(parents=True)
    render_politicians(_env(), db, out, [
        _politician(1, "Anna Ozola", "anna-ozola"),
        _politician(2, "Juris Kalns", "juris-kalns"),
    ], pid_to_syntheses={})

    tab = _saeima_tab((out / "politiki" / "anna-ozola.html").read_text(encoding="utf-8"))
    current, _, past = tab.partition("Iepriekšējie amati")

    # Amati: pašreizējie pret beigušajiem; mandāts nerādās.
    assert "Amati Saeimā" in tab
    assert "Deputāte Ozola Anna" not in tab
    assert "Frakcija ZILĀ" in current and "kopš 01.11.2022" in current
    assert "Baltijas Asamblejas delegācija" in past
    assert "Baltijas Asamblejas delegācija" not in current
    # Vadošā amata dedup: stubs izmests (2 beigušies, ne 3), atgriešanās paliek.
    assert past.startswith(" (2)")
    assert "Budžeta komisija" in current and "kopš 09.06.2026" in current
    assert current.count("Sporta apakškomisija") == 1
    assert '<span class="badge badge-blue">Priekšsēdētāja</span>' in current

    # Debates: kopskaits, laiks, ≤10 jaunākās, saite tikai uz esošu likumprojektu.
    assert "12 uzstāšanās · kopējais runas laiks 1 st. 2 min" in tab
    assert "Punkts 12" in tab and "Punkts 03" in tab
    assert "Punkts 02" not in tab
    assert 'href="../likumprojekti/1105-lm14.html"' in tab
    assert "999-lm14" not in tab
    assert ">Pret<" not in tab  # opinion nav nostāja — nerāda

    # Jautājumi: tikai iesniegtie, skaits pa veidiem, saite uz titania.
    assert "Iesniegti: 2 jautājumi, 1 pieprasījums" in tab
    assert 'href="https://titania.saeima.lv/q/1"' in tab
    assert "Adresēts viņai" not in tab
    # Datums savā kolonnā, nosaukumā neatkārtojas; statuss = pēdējais iznākums.
    assert "Par skolu tīklu" in tab and "(iesniegts 01.02.2026.)" not in tab
    assert ">Noraidīts</span>" in tab

    empty = _saeima_tab((out / "politiki" / "juris-kalns.html").read_text(encoding="utf-8"))
    assert "Par likumprojektu" in empty  # cilne ir
    for heading in ("Amati Saeimā", "Uzstāšanās debatēs", "Jautājumi un pieprasījumi"):
        assert heading not in empty
