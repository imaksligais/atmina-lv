"""Profila bio: CVK kandidātu ziņas + amati pēc VID deklarācijām.

Plāns: docs/plans/2026-09-25-personu-bio.md. Katrs tests nosauc kļūmi, ko ķer:

- parseris lasa īsto CVK lapas struktūru (abas Valaiņa lapas — fikstūras ir
  apgrieztas, dzīvesvieta/tautība/ģimene aizstātas ar SENTINEL vērtībām);
- vārdabrālis (79670, LPV, dz. 1943) NEKAD netiek piesaistīts ZZS ministram;
- privātie lauki nenonāk izvadē;
- rakstības varianti neizplūst dublētās karjeras rindās; NULL gads nepazūd;
- review rinda netiek renderēta; profilam bez datiem nav bloka.
"""

from pathlib import Path

import yaml

from scripts.fetch_cvk_candidates import (
    BIO_FIELDS,
    apply_verdict,
    choose_candidate,
    parse_candidate_page,
)
from src.db import get_db, init_db
from src.render.bio import build_bio, fetch_career, merge_career
from src.vad.schema import init_vad_tables

FIX = Path(__file__).parent / "fixtures"


def _page(cvk_id):
    parsed = parse_candidate_page((FIX / f"cvk_candidate_{cvk_id}.html").read_text(encoding="utf-8"))
    return {"cvk_id": cvk_id, **parsed}


# ── Parseris ─────────────────────────────────────────────────────────


def test_parser_reads_minister_page():
    p = _page(83870)
    # CVK tekstā ir ligatūras (U+FB01 "ﬁ", Siliņas grāds) → NFKC dod parastu "fi".
    html = (FIX / "cvk_candidate_83870.html").read_text(encoding="utf-8")
    lig = parse_candidate_page(html.replace("Rīgas Tehniskā", "Rīgas Tehniskā kvaliﬁkācija"))
    assert lig["education"][0]["institution"].startswith("Rīgas Tehniskā kvalifikācija")
    assert p["list_name"] == "Zaļo un Zemnieku savienība"
    assert p["birth_year"] == 1986
    assert p["education"] == [{
        "institution": "Rīgas Tehniskā universitāte", "year": 2011,
        "degree": "Profesionālais maģistra grāds būvuzņēmējdarbībā un nekustamā īpašuma vadība",
    }]
    assert {"employer": "Ekonomikas ministrija", "position": "Ministrs"} in p["workplaces"]
    assert len(p["workplaces"]) == 4


def test_parser_reads_homonym_page():
    p = _page(79670)
    assert p["list_name"] == "LATVIJA PIRMAJĀ VIETĀ"
    assert p["birth_year"] == 1943
    assert [e["year"] for e in p["education"]] == [2018, 1970]
    assert [e["institution"] for e in p["education"]] == ["Izglītības iestāde A", "Izglītības iestāde B"]
    assert p["workplaces"] == [{"employer": "Darbavieta A", "position": "Amats A"}]


# ── Vārdabrāļi (T13) ─────────────────────────────────────────────────


def test_homonym_resolved_by_party():
    """ZZS profils starp diviem Viktoriem Valaiņiem → tikai 83870."""
    both = [_page(79670), _page(83870)]
    chosen, reason = choose_candidate("ZZS", both)
    assert reason is None and chosen["cvk_id"] == 83870
    chosen, reason = choose_candidate("LPV", both)
    assert chosen["cvk_id"] == 79670  # simetrija: saraksts, ne secība


def test_unique_name_with_party_mismatch_goes_to_review():
    """Vienīgais kandidāts, bet cita partija → review, nevis klusa piesaiste."""
    chosen, reason = choose_candidate("ZZS", [_page(79670)])
    assert chosen is None
    assert reason.startswith("party_mismatch")


def test_same_list_homonyms_are_ambiguous():
    """Divi vārdabrāļi vienā sarakstā (Urbanoviču gadījums) → review."""
    a, b = _page(83870), {**_page(83870), "cvk_id": 1}
    chosen, reason = choose_candidate("ZZS", [a, b])
    assert chosen is None and reason.startswith("homonym_ambiguous")


def test_verdict_resolves_homonym_only_for_its_cvk_id():
    """Operatora lēmums (Urbanovičs → 79910) nedrīkst «pieņemt» citu kandidātu:
    ja CVK pārnumurē un lēmuma cvk_id vairs nav, rinda paliek review."""
    a, b = _page(83870), {**_page(83870), "cvk_id": 1}
    chosen, reason = choose_candidate("ZZS", [a, b])
    picked, reason_ok = apply_verdict({"cvk_id": 1, "status": "ok"}, [a, b], chosen, reason)
    assert picked["cvk_id"] == 1 and reason_ok is None
    stale, reason_stale = apply_verdict({"cvk_id": 999, "status": "ok"}, [a, b], chosen, reason)
    assert stale is None and reason_stale.startswith("homonym_ambiguous")


def test_occupation_only_row_is_kept():
    """Kandidātam bez darbavietas tabula nes vienu kolonnu «Nodarbošanās /
    statuss» (K. Kļaviņš: «Žurnālists») — agrāk to klusi izmeta."""
    html = (FIX / "cvk_candidate_83870.html").read_text(encoding="utf-8")
    start = html.index('id="uxEmploymentTable"')
    body_start, body_end = html.index("<tbody>", start), html.index("</tbody>", start)
    html = html[:body_start] + '<tbody><tr><td>Žurnālists</td></tr>' + html[body_end:]
    assert parse_candidate_page(html)["workplaces"] == [{"employer": None, "position": "Žurnālists"}]


# ── Privātums ────────────────────────────────────────────────────────


def test_private_fields_never_leave_the_parser():
    forbidden_keys = {"residence", "dzivesvieta", "ethnicity", "tautiba", "marital",
                      "gimene", "property", "real_estate", "vehicles", "cash", "loans"}
    for cvk_id in (83870, 79670):
        p = _page(cvk_id)
        assert set(p) <= set(BIO_FIELDS)
        assert not forbidden_keys & set(p)
        dumped = yaml.safe_dump(p, allow_unicode=True)
        assert "SENTINEL" not in dumped
        assert "Vīrietis" not in dumped  # dzimums arī netiek ņemts


# ── Karjeras apvienošana ─────────────────────────────────────────────


def test_career_variants_merge_into_one_range():
    rows = merge_career([
        (2015, "Deputāts", "LATVIJAS REPUBLIKAS SAEIMA"),
        (2018, "Deputāts", "LATVIJAS REPUBLIKAS SAEIMA"),
        (2022, "Deputāts", "Latvijas Republikas Saeima"),
        (2013, "VALDES PRIEKŠSĒDĒTĀJS", '"BRĪVIE DEMOKRĀTI"'),
        (2014, "Valdes priekšsēdētājs", "BRĪVIE  DEMOKRĀTI"),
        (2016, "Parlamentārais sekretārs", "LR EKONOMIKAS MINISTRIJA"),
    ])
    assert [(r["position"], r["entity"], r["years"]) for r in rows] == [
        ("Deputāts", "Latvijas Republikas Saeima", "2015–2022"),
        ("Parlamentārais sekretārs", "LR EKONOMIKAS MINISTRIJA", "2016"),
        ("Valdes priekšsēdētājs", "BRĪVIE DEMOKRĀTI", "2013–2014"),
    ]


def test_null_declaration_year_falls_back_to_submitted_at(tmp_path):
    """Starpposma deklarācijai nav gada — amats nedrīkst pazust; galvene netiek jaukta klāt."""
    db_path = str(tmp_path / "t.db")
    init_db(db_path)
    init_vad_tables(db_path)
    db = get_db(db_path)
    db.execute("INSERT INTO tracked_politicians (id,name,relationship_type) VALUES (1,'A B','tracked')")
    db.execute(
        "INSERT INTO vad_declarations (id,opponent_id,declaration_type,declaration_kind,"
        "declaration_year,submitted_at,source_url,institution,position_title) VALUES "
        "(10,1,'Beidzot darbu','interim',NULL,'2015-01-05','u1','',''),"
        "(11,1,'Kārtējā','annual',2013,'2014-03-31','u2','',''),"
        "(12,1,'Kārtējā','annual',2024,'2025-03-31','u3','Valsts kanceleja','Ministrs')"
    )
    db.execute(
        "INSERT INTO vad_positions (declaration_id,position_title,entity_name) VALUES "
        "(10,'Parlamentārais sekretārs','Satiksmes ministrija'),"
        "(11,'Parlamentārais sekretārs','Satiksmes ministrija')"
    )
    db.commit()
    career = fetch_career(db, [1])[1]
    # Deklarācijas galvene (ministram "Valsts kanceleja") NAV darbavieta — netiek ņemta.
    assert [(r["position"], r["entity"], r["years"]) for r in career] == [
        ("Parlamentārais sekretārs", "Satiksmes ministrija", "2013–2015"),
    ]


# ── Renders ──────────────────────────────────────────────────────────


def test_cvk_workplaces_shown_alongside_vad_history():
    """Bez datiem → nav bloka; CVK darbavietas (pašreizējie amati) rādās arī tad, ja ir VID vēsture."""
    assert build_bio(None, []) is None
    cvk = {"status": "ok", "birth_year": None, "education": [],
           "workplaces": [{"employer": "Y", "position": "docents"}], "source_url": "u"}
    career = merge_career([(2024, "Deputāts", "Saeima")])
    bio = build_bio(cvk, career)
    assert bio["workplaces"] and bio["career"] == career


def test_rendered_profile_has_no_bio_for_review_or_empty(tmp_path, monkeypatch):
    from tests.test_render_own_pubs import _env, _politician
    from src.render.politicians import render_politicians
    from src.saeima.schema import init_saeima_tables

    db_path = str(tmp_path / "t.db")
    init_db(db_path)
    init_saeima_tables(db_path)
    db = get_db(db_path)
    for pid, name in ((1, "Ok Persona"), (2, "Review Persona"), (3, "Tukša Persona")):
        db.execute("INSERT INTO tracked_politicians (id,name,relationship_type) VALUES (?,?,'tracked')",
                   (pid, name))
    db.commit()
    bio_yaml = tmp_path / "cvk.yaml"
    base = {"cvk_id": 9, "source_url": "https://dati.cvk.lv/SV2026/kandidati/9-x/",
            "fetched_at": "2026-09-25", "list_name": "L", "workplaces": [],
            "education": [{"institution": "SENTINEL_SKOLA", "year": 2000, "degree": None}]}
    bio_yaml.write_text(yaml.safe_dump([
        {**base, "politician_id": 1, "name": "Ok Persona", "birth_year": 1986,
         "education": [], "status": "ok", "reason": None},
        {**base, "politician_id": 2, "name": "Review Persona", "birth_year": 1943,
         "status": "review", "reason": "party_mismatch"},
    ], allow_unicode=True), encoding="utf-8")
    monkeypatch.setattr("src.render.bio.CVK_BIO_PATH", bio_yaml)

    out = tmp_path / "site" / "atmina"
    out.mkdir(parents=True)
    render_politicians(_env(), db, out, [
        _politician(1, "Ok Persona", "ok", "politician"),
        _politician(2, "Review Persona", "review", "politician"),
        _politician(3, "Tukša Persona", "tuksa", "politician"),
    ], pid_to_syntheses={})

    ok = (out / "politiki" / "ok.html").read_text(encoding="utf-8")
    assert 'class="profile-bio"' in ok and "dz. 1986" in ok
    for slug in ("review", "tuksa"):
        html = (out / "politiki" / f"{slug}.html").read_text(encoding="utf-8")
        assert 'class="profile-bio"' not in html
        assert "SENTINEL" not in html and "1943" not in html


def test_mep_bio_from_europarl_file_with_source_link(tmp_path, monkeypatch):
    """Nosauktā kļūme (2026-10-07): EP deputāti 2026. g. nekandidēja → CVK datu
    nav, VID deklarāciju nav → bio bez dzimšanas gada un izglītības. Avots —
    oficiālā EP deputāta lapa, ar saiti «Avoti» sarakstā; izglītība bez
    iestādes (EP lapā tikai grāds) nedrīkst sākties ar «: »."""
    from tests.test_render_own_pubs import _env, _politician
    from src.render.politicians import render_politicians
    from src.saeima.schema import init_saeima_tables

    db_path = str(tmp_path / "t.db")
    init_db(db_path)
    init_saeima_tables(db_path)
    db = get_db(db_path)
    db.execute("INSERT INTO tracked_politicians (id,name,relationship_type,role) VALUES "
               "(1,'Eva Deputāte','tracked','EP deputāte')")
    db.commit()
    url = "https://www.europarl.europa.eu/meps/lv/1/EVA_DEPUTATE/cv"
    ep_yaml = tmp_path / "ep.yaml"
    ep_yaml.write_text(yaml.safe_dump([{
        "politician_id": 1, "name": "Eva Deputāte", "source_url": url,
        "fetched_at": "2026-10-08", "birth_year": 1970, "status": "ok",
        "education": [
            {"institution": "Latvijas Universitāte", "year": "1990–1995", "degree": "bakalaura grāds"},
            {"institution": None, "year": None, "degree": "doktora grāds ekonomikā"},
        ],
    }], allow_unicode=True), encoding="utf-8")
    monkeypatch.setattr("src.render.bio.CVK_BIO_PATH", tmp_path / "nav.yaml")
    monkeypatch.setattr("src.render.bio.EP_BIO_PATH", ep_yaml)

    out = tmp_path / "site" / "atmina"
    out.mkdir(parents=True)
    render_politicians(_env(), db, out, [_politician(1, "Eva Deputāte", "eva", "mep")],
                       pid_to_syntheses={})
    html = (out / "politiki" / "eva.html").read_text(encoding="utf-8")
    bio = html[html.index('class="profile-bio"'):html.index("</aside>")]
    assert "dz. 1970" in bio
    assert "Latvijas Universitāte (1990–1995): bakalaura grāds" in bio
    assert "<span>doktora grāds ekonomikā</span>" in bio
    src = bio[bio.index("profile-bio-src"):]
    assert f'href="{url}"' in src and "Eiropas Parlamenta" in src
