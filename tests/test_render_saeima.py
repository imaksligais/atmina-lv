"""saeima.html (15. Saeimas pusloks) — viens e2e tests caur īsto ieejas punktu.

Renderē `generate_public_site(only={"saeima"})` no komitētās fixture DB un
fixture sastāva/rezultātu YAML. Kļūmes, ko tas noķer:
  (a) puslokā nav tieši 100 sēdvietu;
  (b) izsekotais deputāts nav sasaistīts ar profilu VAI neizsekotais saņem
      saiti uz neesošu profilu (404);
  (c) neizsekotais pozīciju lēcā izskatās kā «0» (zemākā krāsa), nevis «nav datu»;
  (d) nepilns sastāva fails (99) vai amatu fails ar neievēlētu vārdu klusi
      renderē nepilnu lapu, nevis krīt;
  (e) amati (data/saeima15_amati.yaml) nenonāk lapā: Prezidija bloks ar 5
      saitēm uz #dep-*, frakcijas vadība savā grupā, amata čips rindā un
      sēdvietas aria-label, gredzens tieši 11 amatpersonu sēdvietām.
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


def test_saeima_page_end_to_end(tmp_path, monkeypatch, fixture_db):
    from src.render._common import _slugify

    html = _render(tmp_path, monkeypatch, fixture_db, ELECTED)

    # (a) 100 sēdvietas
    assert len(re.findall(r'<a [^>]*class="seat[ "]', html)) == 100

    elected = [e["name"] for e in yaml.safe_load(ELECTED.read_text(encoding="utf-8"))["elected"]]
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
    assert "16 komisiju sastāvs un vadība vēl nav ievēlēti" in html

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


def test_saeima_incomplete_composition_fails(tmp_path, monkeypatch, fixture_db):
    doc = yaml.safe_load(ELECTED.read_text(encoding="utf-8"))
    doc["elected"] = doc["elected"][:99]
    bad = tmp_path / "ievēlētie_99.yaml"
    bad.write_text(yaml.safe_dump(doc, allow_unicode=True), encoding="utf-8")
    with pytest.raises(ValueError, match="100"):
        _render(tmp_path, monkeypatch, fixture_db, bad)

    amati = yaml.safe_load(AMATI.read_text(encoding="utf-8"))
    amati["presidium"]["members"][0]["name"] = "Neievēlēts Deputāts"
    bad_amati = tmp_path / "amati_neievēlēts.yaml"
    bad_amati.write_text(yaml.safe_dump(amati, allow_unicode=True), encoding="utf-8")
    with pytest.raises(ValueError, match="Neievēlēts Deputāts"):
        _render(tmp_path, monkeypatch, fixture_db, ELECTED, bad_amati)


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
