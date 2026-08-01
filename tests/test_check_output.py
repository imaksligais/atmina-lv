"""`scripts/check_output.py` pati ir vārti, tāpēc tai jābūt pierādāmi krītošai.

Šī rīka visa jēga ir noķert atsauces uz failiem, kuru nav. Rīks, kas klusi
iziet cauri visam, ir tieši tā „klusās veiksmes" klase, kuras dēļ tas tika
uzrakstīts (2026-08-01 audits: `wiki/index.md` rādīja „0 broken links", kamēr
`wiki_sync` pats rakstīja 338 salauztus; `/audit-integrity` 7. pārbaude skenēja
nepareizo virzienu un mūžīgi ziņoja tīru). Tāpēc katrs tests šeit apgalvo, ka
konkrēta lauzta forma TIEK noķerta, nevis tikai to, ka tīrs koks iet cauri.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "check_output", REPO / "scripts" / "check_output.py"
)
check_output = importlib.util.module_from_spec(_spec)
sys.modules["check_output"] = check_output
_spec.loader.exec_module(check_output)


@pytest.fixture
def tree(tmp_path, monkeypatch):
    """Minimāls uzbūvēta koka modelis ar vienu lapu un vienu īstu assetu."""
    root = tmp_path / "atmina"
    (root / "assets").mkdir(parents=True)
    (root / "assets" / "style.css").write_text("body{}", encoding="utf-8")
    (root / "politiki").mkdir()
    (root / "politiki" / "kads.html").write_text("<html></html>", encoding="utf-8")
    monkeypatch.setattr(check_output, "ROOT", root)
    return root


def _write(root: Path, name: str, body: str) -> None:
    (root / name).write_text(f"<html><body>{body}</body></html>", encoding="utf-8")


def test_missing_local_asset_is_caught(tree):
    _write(tree, "index.html", '<img src="assets/nav-taada.png">')
    problems = check_output.check_refs([])
    assert any("nav-taada.png" in p for p in problems), problems


def test_existing_local_asset_passes(tree):
    _write(tree, "index.html", '<link href="assets/style.css">')
    assert check_output.check_refs([]) == []


def test_relative_parent_path_resolves(tree):
    """`../politiki/kads.html` no apakšmapes — biežākā forma blog ierakstos."""
    (tree / "blog").mkdir()
    (tree / "blog" / "p.html").write_text(
        '<a href="../politiki/kads.html">x</a><a href="../politiki/nav.html">y</a>',
        encoding="utf-8",
    )
    problems = check_output.check_refs([])
    assert len(problems) == 1
    assert "nav.html" in problems[0]


def test_absolute_site_url_maps_back_into_tree(tree):
    """og:image ir absolūts https://atmina.lv/... — tieši šī forma slēpa 404 hero."""
    _write(
        tree,
        "index.html",
        '<meta property="og:image" content="https://atmina.lv/images/nav.jpg">',
    )
    problems = check_output.check_refs([])
    assert any("og:image" in p and "nav.jpg" in p for p in problems), problems


def test_external_and_non_http_refs_are_skipped(tree):
    _write(
        tree,
        "index.html",
        '<a href="https://lsm.lv/raksts">a</a>'
        '<a href="mailto:info@atmina.lv">b</a>'
        '<a href="#sadala">c</a>'
        '<a href="tel:+37100000000">d</a>'
        '<img src="data:image/gif;base64,R0lGOD">',
    )
    assert check_output.check_refs([]) == []


def test_query_string_is_stripped_before_resolving(tree):
    """Assetiem ir `?v=<hash>` cache-busting — tas nedrīkst skaitīties par robu."""
    _write(tree, "index.html", '<link href="assets/style.css?v=abc123">')
    assert check_output.check_refs([]) == []


def test_allowlist_suppresses_a_known_gap(tree):
    _write(tree, "index.html", '<img src="assets/zudis-original.png">')
    assert check_output.check_refs([]) != []
    assert check_output.check_refs(["zudis-original"]) == []


def test_sitemap_catches_both_directions(tree):
    """Emitēta lapa bez <loc> UN <loc> uz neesošu lapu — abi ir robi."""
    _write(tree, "index.html", "x")
    (tree / "sitemap.xml").write_text(
        "<urlset><url><loc>https://atmina.lv/index.html</loc></url>"
        "<url><loc>https://atmina.lv/nav-taadas.html</loc></url></urlset>",
        encoding="utf-8",
    )
    problems = check_output.check_sitemap([])
    # politiki/kads.html eksistē, bet nav sitemap; nav-taadas.html ir otrādi.
    assert any("nav-taadas.html" in p and "neesošu" in p for p in problems), problems
    assert any("politiki/kads.html" in p for p in problems), problems


def test_clean_line_states_what_was_read_not_allowlist_size(tree, monkeypatch, capsys):
    """Zaļā rinda ir publicēšanas pierādījums — tāpēc tai jānes saucēji.

    Līdz 2026-08-09 tā bija `check_output: tīrs (N allowlist paterni)`, t.i.
    vienīgais skaitlis bija tas, ko rīks IGNORĒJA. Saucēji stāvēja aiz
    `--verbose`, ko ne `check.sh`, ne `deploy.sh` nepadeva.
    """
    _write(tree, "index.html", '<link href="assets/style.css">')
    (tree / "politiki" / "kads.html").unlink()
    monkeypatch.setattr(sys, "argv", ["check_output.py", "--refs-only"])
    assert check_output.main() == 0
    out = capsys.readouterr().out
    assert "pārbaudītas 1 lapas" in out
    assert "iekšējās atsauces" in out
    assert "tīrs —" in out


def test_dead_allowlist_pattern_is_named(tree, monkeypatch, capsys):
    """Paterns, kas neapslāpē neko, ir jānosauc — citādi tas dzīvo ilgāk par
    savu cēloni un klusi apklusina to pašu klasi, kad tā atgriežas."""
    _write(tree, "index.html", '<link href="assets/style.css">')
    monkeypatch.setattr(check_output, "load_allowlist", lambda: ["nekad-netrapa"])
    monkeypatch.setattr(sys, "argv", ["check_output.py", "--refs-only"])
    assert check_output.main() == 0
    assert "BEZ TRĀPĪJUMA: nekad-netrapa" in capsys.readouterr().out


def test_empty_tree_is_a_failure_not_clean(tree, monkeypatch):
    """Saucējs 0 nav tīrs rezultāts — tie ir salauzti vārti."""
    for p in tree.rglob("*.html"):
        p.unlink()
    monkeypatch.setattr(sys, "argv", ["check_output.py", "--refs-only"])
    assert check_output.main() == 1


def test_404_page_is_not_required_in_sitemap(tree):
    _write(tree, "index.html", "x")
    _write(tree, "404.html", "x")
    (tree / "politiki" / "kads.html").unlink()
    (tree / "sitemap.xml").write_text(
        "<urlset><url><loc>https://atmina.lv/index.html</loc></url></urlset>",
        encoding="utf-8",
    )
    assert check_output.check_sitemap([]) == []


# --- publish-gate (T15, 2026-08-09) ---
#
# Gatei jābūt pierādāmi KRĪTOŠAI: melnraksta brief lapa kokā = bloķēts deploy;
# orfāna lapa bez DB brief = bloķēts; DB nepieejama = bloķēts (neklusā izlaišana).

import os
import sqlite3
import tempfile

from src.db import init_db


@pytest.fixture
def publish_setup(tree, monkeypatch, tmp_path):
    """Koks ar blog/ + temp DB ar vienu daily_brief (subjekta datums 2026-08-09)."""
    (tree / "blog").mkdir(exist_ok=True)
    fd, db_file = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(db_file)
    db = sqlite3.connect(db_file)
    db.execute(
        "INSERT INTO context_notes (id, topic, note_type, content, created_at)"
        " VALUES (1, 'dienas analīze 2026-08-09', 'daily_brief', '# T', '2026-08-09 22:00')"
    )
    db.commit()
    db.close()
    monkeypatch.setattr(check_output, "DB_PATH", Path(db_file))
    yield db_file
    try:
        os.unlink(db_file)
    except PermissionError:
        pass


def _page(tree, name="2026-08-09.html"):
    (tree / "blog" / name).write_text("<html></html>", encoding="utf-8")


def test_publish_gate_blocks_unapproved_brief(tree, publish_setup, capsys):
    """T15 incidents: melnraksts bez approved=1 attēla nedrīkst aizbraukt deploy."""
    _page(tree)
    problems = check_output.check_publish_gate([])
    assert any("2026-08-09.html" in p for p in problems), problems
    out = capsys.readouterr().out
    assert "1 blog lapas" in out, "saucējs obligāts — cik lapas pārbaudītas"


def _approve_image(db_file, note_id=1):
    db = sqlite3.connect(db_file)
    db.execute(
        "INSERT INTO brief_images (note_id, image_path, prompt, model, width, height, generated_at, approved)"
        f" VALUES ({note_id}, 'images/briefs/x.png', 'p', 'm', 1, 1, '2026-08-09 10:00', 1)"
    )
    db.commit()
    db.close()


def _approve_publish(db_file, key="2026-08-09"):
    db = sqlite3.connect(db_file)
    db.execute(
        "INSERT OR REPLACE INTO publish_approvals (subject_key, approved_at)"
        " VALUES (?, '2026-08-09 21:00:00')", (key,)
    )
    db.commit()
    db.close()


def test_publish_gate_passes_approved_brief(tree, publish_setup):
    _page(tree)
    _approve_image(publish_setup)
    _approve_publish(publish_setup)
    assert check_output.check_publish_gate([]) == []


def test_publish_gate_rejected_image_does_not_satisfy(tree, publish_setup):
    """approved=2 (rejected) NAV apstiprinājums — tipisks slazds (435. briefam
    3 rejected + 1 approved rindas)."""
    _page(tree)
    db = sqlite3.connect(publish_setup)
    db.execute(
        "INSERT INTO brief_images (note_id, image_path, prompt, model, width, height, generated_at, approved)"
        " VALUES (1, 'images/briefs/x.png', 'p', 'm', 1, 1, '2026-08-09 10:00', 2)"
    )
    db.commit()
    db.close()
    assert check_output.check_publish_gate([]) != []


def test_publish_gate_blocks_orphan_page(tree, publish_setup):
    """Lapa bez DB brief ar to datumu = orfāns; additīvais deploy to publicētu
    uz mūžu (T15 mehānisma otra puse)."""
    _page(tree, "2026-01-01.html")
    problems = check_output.check_publish_gate([])
    assert any("orfāns" in p for p in problems), problems


def test_publish_gate_missing_db_hard_fails(tree, monkeypatch):
    (tree / "blog").mkdir(exist_ok=True)
    _page(tree)
    monkeypatch.setattr(check_output, "DB_PATH", Path("E:/nav-sadas-dbs.db"))
    problems = check_output.check_publish_gate([])
    assert any("nevar pārbaudīt" in p for p in problems), problems


# --- eksplicītais publish karogs (2026-08-18, T15 atlikums) ---
#
# Attēla apstiprinājums pierāda TIKAI to, ka attēls ir izvēlēts. Korektūra,
# quality-reviewer un operatora atļauja tur nav — melnraksts ar apstiprinātu
# attēlu izietu v1 vārtus. `publish_approvals` ir tas trūkstošais fakts.


def test_publish_gate_blocks_when_only_image_approved(tree, publish_setup, capsys):
    """Robs, ko šis solis aizver: attēls apstiprināts, atļaujas nav."""
    _page(tree)
    _approve_image(publish_setup)
    problems = check_output.check_publish_gate([])
    assert any("apstiprinājuma" in p for p in problems), problems
    assert any("approve_publish.py" in p for p in problems), problems
    out = capsys.readouterr().out
    assert "1 blog lapas" in out
    assert "bez publicēšanas apstiprinājuma" in out, "saucējs obligāts"


def test_publish_gate_approval_survives_brief_upsert(tree, publish_setup):
    """Atslēga ir SUBJEKTA datums, ne note id: tās pašas dienas brief
    pārģenerēšana (UPSERT vai delete+insert ar jaunu id) nedrīkst atsaukt
    operatora atļauju."""
    _page(tree)
    _approve_image(publish_setup)
    _approve_publish(publish_setup)
    db = sqlite3.connect(publish_setup)
    db.execute("DELETE FROM brief_images WHERE note_id = 1")
    db.execute("DELETE FROM context_notes WHERE id = 1")
    db.execute(
        "INSERT INTO context_notes (id, topic, note_type, content, created_at)"
        " VALUES (77, 'dienas analīze 2026-08-09', 'daily_brief', '# T v2',"
        " '2026-08-10 01:00')"
    )
    db.commit()
    db.close()
    _approve_image(publish_setup, note_id=77)
    assert check_output.check_publish_gate([]) == []


def test_publish_gate_revoked_approval_blocks_again(tree, publish_setup):
    _page(tree)
    _approve_image(publish_setup)
    _approve_publish(publish_setup)
    assert check_output.check_publish_gate([]) == []
    db = sqlite3.connect(publish_setup)
    db.execute("DELETE FROM publish_approvals WHERE subject_key = '2026-08-09'")
    db.commit()
    db.close()
    assert check_output.check_publish_gate([]) != []


def test_publish_gate_weekly_needs_its_own_approval(tree, publish_setup):
    """Nedēļas pārskata lapa ar TO PAŠU subjekta datumu nav segta ar dienas
    pārskata atļauju — atslēga ir lapas slugs (`nedela-` prefikss)."""
    db = sqlite3.connect(publish_setup)
    db.execute(
        "INSERT INTO context_notes (id, topic, note_type, content, created_at)"
        " VALUES (2, 'nedēļas analīze 2026-08-09 līdz 2026-08-15', 'weekly_brief',"
        " '# N', '2026-08-16 20:00')"
    )
    db.commit()
    db.close()
    _page(tree, "nedela-2026-08-09.html")
    _approve_image(publish_setup, note_id=2)
    _approve_publish(publish_setup, key="2026-08-09")  # dienas atļauja
    problems = check_output.check_publish_gate([])
    assert any("nedela-2026-08-09.html" in p for p in problems), problems
    _approve_publish(publish_setup, key="nedela-2026-08-09")
    assert check_output.check_publish_gate([]) == []


def test_publish_gate_missing_approvals_table_hard_fails(tree, publish_setup):
    """Vecs DB bez tabulas nedrīkst nozīmēt „nav ko pārbaudīt"."""
    _page(tree)
    _approve_image(publish_setup)
    db = sqlite3.connect(publish_setup)
    db.execute("DROP TABLE publish_approvals")
    db.commit()
    db.close()
    problems = check_output.check_publish_gate([])
    assert any("nevar pārbaudīt" in p for p in problems), problems
