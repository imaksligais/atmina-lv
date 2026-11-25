"""Saites v2, 2. posms — «Kur ceļi krustojas» (kopīgās vietas) no gala līdz galam.

Nosauktās kļūmes, ko šis fails ķer:
- vieta parādās, lai gan neviens pāris tajā nav bijis VIENLAIKUS (komisijā
  pārklāšanās < 30 d, organizācijā nav kopīga deklarācijas gada) — neitrāls
  fakts izskatītos pēc mājiena;
- partija (ORG_EXCLUDED) vai nepārbaudīta organizācija publicējas kā
  «organizācija» (sarakstam jābūt slēgtam: tikai ORG_ALLOWLIST);
- profils vai pāra kartīte saitē uz vietu, kuras lapa nav uzbūvēta;
- neaizvērts 14. Saeimas amats rādās kā joprojām spēkā esošs.
"""
from datetime import date

from src.db import get_db, init_db
from src.render.links import render_links
from src.render.politicians import render_politicians
from src.render.vietas import (
    ORG_ALLOWLIST, ORG_EXCLUDED, build_places, lv_sort_key, merge_intervals,
    overlap_days, render_places, year_ranges,
)
from src.saeima.schema import init_saeima_tables
from src.vad.schema import init_vad_tables
from tests.test_render_saeima_activity import _env, _politician

LOK = "50008022421"
assert LOK in ORG_ALLOWLIST
PARTY = sorted(ORG_EXCLUDED)[0]
UNREVIEWED = "40000000001"
assert UNREVIEWED not in ORG_ALLOWLIST and UNREVIEWED not in ORG_EXCLUDED


def _seed(path):
    init_db(path)
    init_saeima_tables(path)
    init_vad_tables(path)
    db = get_db(path)
    db.execute(
        "INSERT INTO tracked_politicians (id, name, party, relationship_type) VALUES "
        "(1, 'Anna Ozola', 'X', 'tracked'), (2, 'Juris Kalns', 'Y', 'tracked'), "
        "(3, 'Pēteris Bērziņš', 'X', 'tracked'), (4, 'Ilze Neaktīvā', 'X', 'inactive')"
    )

    def pos(pid, body, position, d_from, d_to, level="3"):
        db.execute(
            "INSERT INTO saeima_deputy_positions (convocation, politician_id, deputy_unid,"
            " deputy_name, level, body, position, date_from, date_to, source_url, created_at)"
            " VALUES (14, ?, ?, 'x', ?, ?, ?, ?, ?, ?, '2026-10-05 10:00:00')",
            (pid, f"U{pid}", level, body, position, d_from, d_to, f"https://titania/u{pid}"),
        )
    # Budžeta komisija: Anna + Juris 60+ dienas vienlaikus → vieta.
    # Annas amata maiņa = vienas dienas rinda + vadošais amats (titania artefakts).
    pos(1, "Budžeta komisija", "Deputāte", "2022-11-23", "2022-11-23")
    pos(1, "Budžeta komisija", "Priekšsēdētāja", "2022-11-23", None)
    pos(2, "Budžeta komisija", "Deputāts", "2023-01-01", "2023-06-30")
    # Pēteris Budžeta komisijā tikai 10 dienas pēc Jura → bez «kopā» ar Juri.
    pos(3, "Budžeta komisija", "Deputāts", "2026-10-25", None)
    # Juridiskā komisija: pārklāšanās 5 dienas → NAV vietas.
    pos(1, "Juridiskā komisija", "Deputāte", "2023-01-01", "2023-01-10")
    pos(2, "Juridiskā komisija", "Deputāts", "2023-01-06", "2023-03-01")
    # Neaktīvais nekad neveido vietu.
    pos(4, "Ārlietu komisija", "Deputāte", "2023-01-01", None)
    pos(1, "Ārlietu komisija", "Deputāte", "2023-01-01", None)

    decl_id = [0]

    def decl(pid, year, reg, name, title):
        decl_id[0] += 1
        db.execute(
            "INSERT INTO vad_declarations (id, opponent_id, vad_uuid, declaration_type,"
            " declaration_kind, declaration_year, submitted_at, source_url)"
            " VALUES (?, ?, ?, 'Kārtējā gada deklarācija', 'annual', ?, ?, ?)",
            (decl_id[0], pid, f"u{decl_id[0]}", year, f"{year + 1}-03-01",
             f"https://vid/d{decl_id[0]}"),
        )
        db.execute(
            "INSERT INTO vad_positions (declaration_id, position_title, entity_name,"
            " entity_reg_number, is_individual) VALUES (?, ?, ?, ?, 0)",
            (decl_id[0], title, name, reg),
        )
    decl(1, 2024, LOK, "Biedrība «Latvijas Olimpiskā komiteja»", "Valdes locekle")
    decl(2, 2024, LOK, "Biedrība «Latvijas Olimpiskā komiteja»", "Viceprezidents")
    # Jaunākajā deklarācijā divi amati vienā organizācijā → abi redzami.
    db.execute(
        "INSERT INTO vad_positions (declaration_id, position_title, entity_name,"
        " entity_reg_number, is_individual) VALUES (?, 'Izpildkomitejas loceklis', 'x', ?, 0)",
        (decl_id[0], LOK),
    )
    decl(1, 2024, PARTY, "Partija «Tests»", "Valdes locekle")
    decl(2, 2024, PARTY, "Partija «Tests»", "Valdes loceklis")
    decl(1, 2024, UNREVIEWED, "Biedrība «Jauna»", "Biedre")
    decl(2, 2024, UNREVIEWED, "Biedrība «Jauna»", "Biedrs")
    db.execute(
        "INSERT INTO political_tensions (source_pid, target_pid, topic, description,"
        " tension_type, source_url, created_at) VALUES (1, 2, 'Budžets',"
        " 'Ozola kritizē Kalna budžeta plānu.', 'spriedze', 'https://ex.lv/a',"
        " '2026-03-01 10:00:00')"
    )
    db.commit()
    return db


def test_shared_places_render_end_to_end(tmp_path):
    db = _seed(str(tmp_path / "t.db"))
    out = tmp_path / "site" / "atmina"
    out.mkdir(parents=True)
    env = _env()
    places = build_places(db)
    render_places(env, places, out)
    render_links(env, db, out, [], places=places)
    render_politicians(env, db, out, [
        _politician(1, "Anna Ozola", "anna-ozola"),
        _politician(3, "Pēteris Bērziņš", "peteris-berzins"),
    ], pid_to_syntheses={}, places=places)

    pages = sorted(p.name for p in (out / "vietas").glob("*.html"))
    assert len(pages) == 2, pages          # Budžeta komisija + LOK, nekas cits
    assert [r for r, _ in places["unreviewed_orgs"]] == [UNREVIEWED]

    budget = next(p for p in pages if p.startswith("budzeta-komisija-"))
    lok = next(p for p in pages if p.startswith("latvijas-olimpiska-komiteja-"))
    page = (out / "vietas" / budget).read_text(encoding="utf-8")
    assert "Anna Ozola" in page and "Juris Kalns" in page and "Pēteris Bērziņš" in page
    # Amata maiņas artefakts nerada «locekli»; neaizvērtais amats beidzas ar sasaukumu.
    assert "Priekšsēdētāja</td>" in page
    assert "23.11.2022–03.11.2026" in page
    assert 'href="https://titania/u1"' in page
    lok_page = (out / "vietas" / lok).read_text(encoding="utf-8")
    assert "Valdes locekle" in lok_page
    assert "Viceprezidents, Izpildkomitejas loceklis" in lok_page

    saites = (out / "saites.html").read_text(encoding="utf-8")
    assert f'href="vietas/{budget}"' in saites and f'href="vietas/{lok}"' in saites
    assert "Partija «Tests»" not in saites and "Jauna" not in saites
    assert "Juridiskā komisija" not in saites and "Ārlietu komisija" not in saites

    anna = (out / "politiki" / "anna-ozola.html").read_text(encoding="utf-8")
    section = anna[anna.index('id="kur-celi-krustojas"'):]
    section = section[:section.index("</ul>")]
    assert f'href="../vietas/{budget}"' in section and "Tajā pašā laikā arī: Juris Kalns" in section
    assert "Pēteris" not in section       # 2026-10-25 → 03.11.2026 = 10 dienas ar Annu
    # Pāra kartīte: kopīgā vieta ar otru dalībnieku, uz uzbūvētu lapu.
    card = anna[anna.index('class="saites-card-shared"'):]
    assert card.index(f'href="../vietas/{budget}"') < card.index("</p>")

    # Pēterim nav neviena vienlaicīga pāra → nav sadaļas un nav Saites cilnes.
    peteris = (out / "politiki" / "peteris-berzins.html").read_text(encoding="utf-8")
    assert 'id="kur-celi-krustojas"' not in peteris


def test_interval_and_year_logic():
    d = date
    # Amata maiņa (saskaras vai pārklājas) = viens periods; sprauga paliek.
    assert merge_intervals([(d(2023, 1, 1), d(2023, 1, 1)), (d(2023, 1, 1), d(2023, 6, 1)),
                            (d(2023, 6, 2), d(2023, 9, 1)), (d(2024, 1, 1), d(2024, 2, 1))]) == [
        (d(2023, 1, 1), d(2023, 9, 1)), (d(2024, 1, 1), d(2024, 2, 1))]
    # Kopīgās dienas ieskaitot robežas; bez pārklāšanās 0.
    assert overlap_days([(d(2023, 1, 1), d(2023, 1, 10))], [(d(2023, 1, 10), d(2023, 2, 1))]) == 1
    assert overlap_days([(d(2023, 1, 1), d(2023, 1, 9))], [(d(2023, 1, 10), d(2023, 2, 1))]) == 0
    assert year_ranges({2019, 2021, 2022, 2023, 2025}) == "2019, 2021–2023, 2025"
    # Latviešu alfabēts: «ā» pēc «a», «č» pēc «c», «ž» beigās.
    assert sorted(["Žagars", "Baltijas", "Baltā", "Čaks", "CATA"], key=lv_sort_key) == [
        "Baltā", "Baltijas", "CATA", "Čaks", "Žagars"]
