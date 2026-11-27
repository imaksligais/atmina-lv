"""saeima.html (15. Saeimas pusloks) — viens e2e tests caur īsto ieejas punktu.

Renderē `generate_public_site(only={"saeima"})` no komitētās fixture DB un
fixture sastāva/rezultātu YAML. Kļūmes, ko tas noķer:
  (a) puslokā nav tieši 100 sēdvietu;
  (b) izsekotais deputāts nav sasaistīts ar profilu VAI neizsekotais saņem
      saiti uz neesošu profilu (404);
  (c) neizsekotais pozīciju lēcā izskatās kā «0» (zemākā krāsa), nevis «nav datu»;
  (d) nepilns sastāva fails (99) vai amatu fails ar nesēdošu vārdu, izkritušu
      komisiju, diviem priekšsēdētājiem, deputātu bez komisijas vai nesakrītošiem
      mandātiem klusi renderē nepilnu lapu, nevis krīt;
  (e) amati (data/saeima15_amati.yaml) nenonāk lapā: Prezidija bloks ar 5
      saitēm uz #dep-*, frakcijas vadība savā grupā, amata čips rindā un
      sēdvietas aria-label, gredzens tieši 11 amatpersonu sēdvietām;
  (f) koalīcijas lēca neņem statusu no `parties.coalition_status` (vai liek
      kādu pusi sarakstam, kura partijas DB nav);
  (g) uzticības balsojuma lēcā deputāts bez balsojuma rindas izskatās kā «pret»;
  (h) bloks «Valdība» nerāda ministru vai ved uz neesošu valdiba.html rindu
      (enkurs ≠ ``fetch_cabinet`` enkurs);
  (i) sēdvietas rāda CVK sarakstu, ne sēdošos: ministrs, kas nolicis mandātu, vēl
      sēž, aizstājēja nav; komisiju blokā nav 16 komisiju vai sastāva rinda ved uz
      neesošu #dep- rindu.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

FIXTURES = Path(__file__).parent / "fixtures"
ELECTED = FIXTURES / "cvk_sv2026_ievēlētie.yaml"
RESULTS = FIXTURES / "cvk_sv2026_rezultati.yaml"
AMATI = FIXTURES / "saeima15_amati.yaml"


@pytest.fixture
def fixture_db(tmp_path):
    from src.db import get_db, init_db
    from src.saeima.schema import init_saeima_bills, init_saeima_tables
    from tests.fixture_sql import load_render_fixture_sql

    db_path = str(tmp_path / "fixture.db")
    init_db(db_path)
    init_saeima_tables(db_path)
    init_saeima_bills(db_path)
    conn = get_db(db_path)
    for ddl in (
        "ALTER TABLE tracked_politicians ADD COLUMN x_handle TEXT",
        "ALTER TABLE documents ADD COLUMN is_paywall BOOLEAN DEFAULT FALSE",
        "ALTER TABLE documents ADD COLUMN summary TEXT",
    ):
        try:
            conn.execute(ddl)
        except Exception:  # noqa: BLE001 — kolonna jau ir
            pass
    conn.executescript(load_render_fixture_sql())
    conn.commit()
    conn.close()
    return db_path


def _render(tmp_path, monkeypatch, db_path, elected_path, amati_path=AMATI):
    import src.render._orchestrator as orch
    import src.render.saeima as saeima_mod
    from src.render import generate_public_site

    def _stub(dest, *a, **k):
        Path(dest).write_text("/* stub */", encoding="utf-8")

    for name in ("_download_chart_js", "_download_annotation_plugin", "_download_d3"):
        if hasattr(orch, name):
            monkeypatch.setattr(orch, name, _stub)
    monkeypatch.setattr(saeima_mod, "ELECTED_PATH", elected_path)
    monkeypatch.setattr(saeima_mod, "RESULTS_PATH", RESULTS)
    monkeypatch.setattr(saeima_mod, "AMATI_PATH", amati_path, raising=False)
    out = tmp_path / "site"
    generate_public_site(db_path=db_path, output_dir=str(out), only={"saeima"})
    return (out / "atmina" / "saeima.html").read_text(encoding="utf-8")


def _sitting() -> list[dict]:
    """Sēdošie = ievēlētie − mandātu nolikušie + aizstājēji (kā amatu fixture)."""
    elected = yaml.safe_load(ELECTED.read_text(encoding="utf-8"))["elected"]
    mand = yaml.safe_load(AMATI.read_text(encoding="utf-8"))["mandates"]
    out = set(mand["suspended"])
    return [e for e in elected if e["name"] not in out] + list(mand["substitutes"])


def _tracked_names(db_path: str) -> set[str]:
    import sqlite3

    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT name FROM tracked_politicians "
        "WHERE relationship_type NOT IN ('inactive', 'commentator')"
    ).fetchall()
    conn.close()
    return {r[0] for r in rows}


def _seat(html: str, name: str) -> str:
    m = re.search(r'<a [^>]*class="seat[ "][^>]*aria-label="' + re.escape(name) + r',[^"]*"[^>]*>', html)
    assert m, f"sēdvieta {name!r} nav atrasta"
    return m.group(0)


def _row(html: str, slug: str) -> str:
    m = re.search(r'<details class="slv-dep[^"]*" id="dep-' + re.escape(slug) + r'".*?</details>', html, re.S)
    assert m, f"rinda dep-{slug} nav atrasta"
    return m.group(0)


def _seed_confidence_vote(db_path: str, ballots: dict[str, str]) -> None:
    """Šī sasaukuma uzticības balsojums + coalition_periods rinda, kas uz to rāda."""
    from src.db import get_db
    from src.saeima.convocation import SAEIMA_CONVOCATION, base_url

    db = get_db(db_path)
    vote_id = db.execute(
        "INSERT INTO saeima_votes (motif, vote_date, vote_time, url, result) "
        "VALUES ('Uzticības izteikšana Ministru kabinetam', '2026-11-17', '22:27:39', ?, 'Pieņemts')",
        (base_url(SAEIMA_CONVOCATION) + "/Voting?ReadForm&parentID=test",),
    ).lastrowid
    db.execute(
        "INSERT INTO coalition_periods (valid_from_date, valid_from_time, factions, source_vote_id) "
        "VALUES ('2026-11-17', '22:27:39', 'AS,NA', ?)",
        (vote_id,),
    )
    for name, vote in ballots.items():
        pid = db.execute("SELECT id FROM tracked_politicians WHERE name = ?", (name,)).fetchone()[0]
        db.execute(
            "INSERT INTO saeima_individual_votes (vote_id, politician_id, deputy_name, vote) VALUES (?, ?, ?, ?)",
            (vote_id, pid, name, vote),
        )
    db.commit()
    db.close()


def test_saeima_page_end_to_end(tmp_path, monkeypatch, fixture_db):
    from src.render._common import _slugify

    elected_rows = _sitting()
    import sqlite3
    # Fixture DB no AS un NA izseko tikai ministrus (tie nolikuši mandātu) — pa vienam
    # aizstājējam kā izsekotu deputātu, lai abu sarakstu sēdvietām būtu profils un balss.
    with sqlite3.connect(fixture_db) as c:
        for nr, party in ((7, "Apvienotais saraksts"), (5, "Nacionālā apvienība")):
            sub = next(s["name"] for s in elected_rows if s["list_nr"] == nr and "region" not in s)
            c.execute(
                "INSERT INTO tracked_politicians (name, name_forms, relationship_type, party, role) "
                "VALUES (?, '[]', 'tracked', ?, 'Saeimas deputāts')",
                (sub, party),
            )
    tracked_all = _tracked_names(fixture_db)
    # Uzticības balsojums: AS deputātam «Par», PRO deputātam «Pret»; izsekotam NA
    # deputātam rindas nav (jābūt «nav ieraksta», ne «pret»).
    def _tracked_from(list_nr: int) -> str:
        return next(e["name"] for e in elected_rows if e["list_nr"] == list_nr and e["name"] in tracked_all)

    voter_par, voter_pret, no_row = _tracked_from(7), _tracked_from(14), _tracked_from(5)
    sv_any = next(e["name"] for e in elected_rows if e["list_nr"] == 1)
    _seed_confidence_vote(fixture_db, {voter_par: "Par", voter_pret: "Pret"})
    import sqlite3
    with sqlite3.connect(fixture_db) as c:  # (h) viens zināms ministrs
        c.execute("UPDATE tracked_politicians SET role = 'Labklājības ministrs' WHERE name = ?", (voter_par,))

    html = _render(tmp_path, monkeypatch, fixture_db, ELECTED)

    # (a) 100 sēdvietas
    assert len(re.findall(r'<a [^>]*class="seat[ "]', html)) == 100

    elected = [e["name"] for e in elected_rows]
    tracked = _tracked_names(fixture_db) & set(elected)
    untracked = [n for n in elected if n not in tracked]
    assert tracked and untracked, "fixture jāsatur abas klases"

    # (b) izsekotajam profila saite, neizsekotajam nav
    t = sorted(tracked)[0]
    assert f'href="politiki/{_slugify(t)}.html"' in _row(html, _slugify(t))
    u = untracked[0]
    u_row = _row(html, _slugify(u))
    assert "politiki/" not in u_row
    assert "Profils vēl nav izveidots." in u_row

    # (c) neizsekotajam pozīciju lēcā «nav datu», ne 0
    assert 'data-pos="nav"' in _seat(html, u)
    assert re.search(r'data-lens-val="pos"[^>]*>\s*nav datu\s*<', u_row)
    assert 'data-pos="nav"' not in _seat(html, t)

    # (e) amati
    amati = yaml.safe_load(AMATI.read_text(encoding="utf-8"))
    prez = amati["presidium"]["members"]
    chairs = [ld for f in amati["factions"]["items"] for ld in f["leaders"] if ld["role"] == "chair"]
    block = re.search(r'<section class="slv-prez".*?</section>', html, re.S)
    assert block, "Prezidija bloka nav"
    prez_links = re.findall(r'href="#dep-([^"]+)"', block.group(0))
    assert prez_links == [_slugify(m["name"]) for m in prez], "Prezidija saites ≠ 5 locekļi YAML secībā"

    smiltens = prez[0]
    assert smiltens["office"] in _row(html, _slugify(smiltens["name"])), "amata čips nav rindā"
    assert smiltens["office"] in _seat(html, smiltens["name"]), "amats nav sēdvietas aria-label"

    as_group = next(g for g in html.split('<details class="slv-group"') if 'data-list="7"' in g.split(">", 1)[0])
    lead = re.search(r'<p class="slv-group-lead">.*?</p>', as_group, re.S)
    assert lead and 'href="#dep-maris-kucinskis"' in lead.group(0), "AS frakcijas vadība nav grupā"
    as_sum = re.search(r'<summary class="slv-group-sum">.*?</summary>', as_group, re.S).group(0)
    assert "Priekšsēdētājs Māris Kučinskis" in as_sum and "<a " not in as_sum, "priekšsēdētājs nav grupas galvenē kā teksts"

    ringed = set(re.findall(r'<a [^>]*class="seat has-office"[^>]*data-slug="([^"]+)"', html))
    expected = {_slugify(x["name"]) for x in prez + chairs}
    assert len(expected) == 11 and ringed == expected, f"gredzens {len(ringed)} sēdvietām, gaidīts 11"

    # (f) koalīcija no fixture `parties.coalition_status`: AS (id 6) = coalition,
    # PRO (id 2) = opposition; SV-AJ (party_id 19 fixture DB nav) = «nav datu».
    assert 'data-lens="koalicija"' in html and 'data-lens="uzticiba"' in html, "valdības lēcu pogu nav"
    assert 'data-gov="koalicija"' in _seat(html, voter_par)
    assert 'data-gov="opozicija"' in _seat(html, voter_pret)
    assert 'data-gov="nav"' in _seat(html, sv_any)
    assert re.search(r'data-lens-val="gov"[^>]*>\s*opozīcija\s*<', _row(html, _slugify(voter_pret)))

    # (g) uzticības balss: rinda → sava vērtība; nav rindas → «nav ieraksta», nekad «pret».
    assert 'data-uzt="par"' in _seat(html, voter_par)
    assert 'data-uzt="pret"' in _seat(html, voter_pret)
    for name in (no_row, untracked[0]):
        assert 'data-uzt="nav"' in _seat(html, name), f"{name}: bez rindas jābūt data-uzt=nav"
        r = _row(html, _slugify(name))
        assert re.search(r'data-lens-val="uzt"[^>]*>\s*nav ieraksta\s*<', r), f"{name}: rindā nav «nav ieraksta»"
        assert "balsoja pret" not in r, f"{name}: bez rindas rādīts «balsoja pret»"
    assert re.search(r'data-lens-val="uzt"[^>]*>\s*balsoja pret\s*<', _row(html, _slugify(voter_pret)))
    assert "Dati par 2 no 100" in html, "uzticības lēcas saucējs nav 2 no 100"

    # (h) Valdība: ministrs rindā ar saiti uz SAVU rindu valdiba.html (tas pats enkurs).
    from src.db import get_db
    from src.render.valdiba import fetch_cabinet

    gov_block = re.search(r'<section class="slv-gov".*?</section>', html, re.S)
    assert gov_block, "bloka «Valdība» nav"
    cabinet, _ = fetch_cabinet(get_db(fixture_db))
    lab = next(r for r in cabinet if r["post"] == "Labklājības ministrija")
    row = re.search(r'<a class="slv-gov-row" href="valdiba\.html#' + re.escape(lab["anchor"]) + r'">.*?</a>',
                    gov_block.group(0), re.S)
    assert row and voter_par in row.group(0), "ministrs nav rindā ar saiti uz savu valdiba.html rindu"

    # (i) sēdošie un komisijas
    mand = amati["mandates"]
    for name in mand["suspended"]:
        assert f'aria-label="{name},' not in html, f"{name} nolicis mandātu, bet sēdvieta vēl ir"
    for s in mand["substitutes"]:
        assert "ministra vietā" in _row(html, _slugify(s["name"])), f"{s['name']}: rindā nav «ministra vietā»"
        assert f'data-list="{s["list_nr"]}"' in _seat(html, s["name"]), f"{s['name']} nav sava saraksta sēdvietā"
    kom = re.findall(r'<details class="slv-kom-item" id="kom-[^"]+">.*?</details>', html, re.S)
    assert len(kom) == 16, f"komisiju blokā {len(kom)} komisijas, jābūt 16"
    dep_ids = set(re.findall(r'id="dep-([^"]+)"', html))
    for block, c in zip(kom, amati["committees"]["items"], strict=True):
        assert c["name"] in block
        links = re.findall(r'<a class="slv-kom-row" href="#dep-([^"]+)"', block)
        assert links == [_slugify(m["name"]) for m in c["members"]], f"{c['name']}: sastāvs ≠ YAML"
        assert set(links) <= dep_ids, f"{c['name']}: saite uz neesošu deputāta rindu"
    chair = amati["committees"]["items"][0]["members"][0]["name"]
    assert re.search(r'<summary class="slv-kom-sum">.*?' + re.escape(chair), kom[0], re.S), "priekšsēdētājs nav komisijas rindā"


def _break_amati(amati: dict, how: str) -> str:
    """Viena kļūda amatu YAML; atgriež tekstu, kam jābūt kļūdas ziņojumā."""
    items = amati["committees"]["items"]
    if how == "nesēdošs":
        amati["presidium"]["members"][0]["name"] = "Neievēlēts Deputāts"
        return "Neievēlēts Deputāts"
    if how == "nolicis_mandātu_komisijā":
        items[0]["members"][-1]["name"] = amati["mandates"]["suspended"][0]
        return "nav sēdošo"
    if how == "izkritusi_komisija":
        del items[-1]
        return "komisiju ir 15"
    if how == "divi_priekšsēdētāji":
        items[0]["members"][3]["title"] = "Priekšsēdētājs"
        return "'chair' 2"
    if how == "deputāts_bez_komisijas":
        gone = items[0]["members"].pop()["name"]
        for c in items[1:]:
            c["members"] = [m for m in c["members"] if m["name"] != gone]
        return "nav 1–2 komisijās"
    if how == "mandāti_nesakrīt":
        amati["mandates"]["substitutes"][0]["list_nr"] = 5
        return "nesakrīt"
    raise AssertionError(how)


@pytest.mark.parametrize("how", [
    "nesēdošs", "nolicis_mandātu_komisijā", "izkritusi_komisija",
    "divi_priekšsēdētāji", "deputāts_bez_komisijas", "mandāti_nesakrīt",
])
def test_saeima_bad_offices_fail(tmp_path, monkeypatch, fixture_db, how):
    amati = yaml.safe_load(AMATI.read_text(encoding="utf-8"))
    expect = _break_amati(amati, how)
    bad_amati = tmp_path / f"amati_{how}.yaml"
    bad_amati.write_text(yaml.safe_dump(amati, allow_unicode=True), encoding="utf-8")
    with pytest.raises(ValueError, match=re.escape(expect)):
        _render(tmp_path, monkeypatch, fixture_db, ELECTED, bad_amati)


def test_saeima_incomplete_composition_fails(tmp_path, monkeypatch, fixture_db):
    doc = yaml.safe_load(ELECTED.read_text(encoding="utf-8"))
    doc["elected"] = doc["elected"][:99]
    bad = tmp_path / "ievēlētie_99.yaml"
    bad.write_text(yaml.safe_dump(doc, allow_unicode=True), encoding="utf-8")
    with pytest.raises(ValueError, match="100"):
        _render(tmp_path, monkeypatch, fixture_db, bad)


@pytest.mark.parametrize("convocation", [15, 16])
def test_saeima_vote_lens_filters_convocation(tmp_path, monkeypatch, fixture_db, convocation):
    from src.db import get_db
    import src.render.saeima as saeima

    monkeypatch.setattr(saeima, "SAEIMA_CONVOCATION", convocation, raising=False)
    elected = yaml.safe_load(ELECTED.read_text(encoding="utf-8"))["elected"]
    names = [e["name"] for e in elected[:2]]
    db = get_db(fixture_db)
    db.execute("DELETE FROM saeima_individual_votes")
    for n, name in zip((14, 15), names, strict=True):
        db.execute("INSERT OR IGNORE INTO tracked_politicians (name, relationship_type) VALUES (?, 'opponent')", (name,))
        pid = db.execute("SELECT id FROM tracked_politicians WHERE name = ?", (name,)).fetchone()[0]
        db.execute("UPDATE tracked_politicians SET relationship_type = 'opponent' WHERE id = ?", (pid,))
        vote_id = db.execute(
            "INSERT INTO saeima_votes (motif, vote_date, url) VALUES ('Test', '2026-11-03', ?)",
            (f"https://titania.saeima.lv/LIVS{n}/SaeimaLIVS2_DK.nsf/test",),
        ).lastrowid
        db.execute("INSERT INTO saeima_individual_votes (vote_id, politician_id, deputy_name, vote) VALUES (?, ?, ?, 'Par')", (vote_id, pid, name))
    db.commit()
    ctx = saeima._build_context(db, ELECTED, RESULTS, AMATI)
    db.close()
    assert ctx["voted_n"] == 1
    members = {s["name"]: s for s in ctx["seats"]}
    # Lēca rāda IEPRIEKŠĒJO Saeimu: pašreizējā 15 → 14. Saeimas balsotājs.
    assert members[names[0]]["voted14"] is (convocation == 15)
    assert members[names[1]]["voted14"] is (convocation == 16)
    html = _render(tmp_path, monkeypatch, fixture_db, ELECTED)
    prev = convocation - 1
    assert f"Balsoja {prev}. Saeimā" in html
    assert f"1 no 100 balsoja arī {prev}. Saeimā" in html
    assert f"Vai deputāts iepriekšējā, {prev}. Saeimā" in html
