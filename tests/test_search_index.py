"""Homepage typeahead sidecar (data/sg-index.json) — fetch + emit contracts.

`render_search_index` emits a small suggestion index consumed positionally by
``assets/sgv1.js``. These tests lock the load-bearing pieces: the tuple
arities (a Python-side reorder must not silently break the JS index
constants), the inactive/commentator exclusion, the public-pretrunas
``COALESCE(confirmed, 1) = 1`` counting contract, and the position-only topic
counts. Emit mirrors `links.py::_emit_saites_json` (.json + .br + .gz).
"""

from __future__ import annotations

import json
import sqlite3

import pytest


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE tracked_politicians (
            id INTEGER PRIMARY KEY, name TEXT, party TEXT, role TEXT,
            relationship_type TEXT
        );
        CREATE TABLE claims (
            id INTEGER PRIMARY KEY, opponent_id INTEGER, claim_type TEXT, topic TEXT
        );
        CREATE TABLE contradictions (
            id INTEGER PRIMARY KEY, opponent_id INTEGER, confirmed INTEGER,
            summary TEXT, severity TEXT, topic TEXT
        );
        CREATE TABLE parties (
            id INTEGER PRIMARY KEY, name TEXT, short_name TEXT
        );
        CREATE TABLE social_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            opponent_id INTEGER,
            platform TEXT,
            handle TEXT,
            feed_type TEXT
        );
    """)
    conn.executemany(
        "INSERT INTO tracked_politicians (id, name, party, role, relationship_type) VALUES (?,?,?,?,?)",
        [
            (1, "Jānis Vītols", "Jaunā Vienotība", "Ministrs", "tracked"),
            (2, "Slēptais Politiķis", "Jaunā Vienotība", None, "inactive"),
            (3, "Vecais Komentētājs", None, None, "commentator"),
            (4, "Brīvā Žurnāliste", None, None, "journalist"),
            (5, "Ziņu Aģentūra", None, None, "organization"),
        ],
    )
    conn.executemany(
        "INSERT INTO claims (opponent_id, claim_type, topic) VALUES (?,?,?)",
        [
            (1, "position", "Budžets un finanses"),
            (1, "position", "Budžets un finanses"),
            (1, "saeima_vote", "Budžets un finanses"),  # never counted
            (2, "position", "Vēlēšanas"),               # inactive → topic excluded
            (4, "position", "Mediji un vārda brīvība"),
        ],
    )
    conn.executemany(
        "INSERT INTO contradictions (id, opponent_id, confirmed, summary, severity, topic) VALUES (?,?,?,?,?,?)",
        [
            (1, 1, 1, "Vītols mainīja nostāju par budžeta deficītu no atbalsta uz stingru iebildumu jau nākamajā nedēļā",
             "reversal", "Budžets un finanses"),        # confirmed → counted + in c
            (2, 1, 0, "Neapstiprināta pretruna", "minor_shift", "Vēlēšanas"),  # unpublished → NOT counted, NOT in c
            (3, 1, None, "Vītols balsoja pretēji agrākajiem izteikumiem",
             "direct_contradiction", "Nodokļi"),        # legacy NULL → counted + in c
            (4, 2, 1, "Slēptā politiķa pretruna", "reversal", "Vēlēšanas"),  # active-only gate → NOT in c
        ],
    )
    conn.execute("INSERT INTO parties (id, name, short_name) VALUES (1, 'Jaunā Vienotība', 'JV')")
    yield conn
    conn.close()


def test_sg_index_tuple_shape(db):
    """Arity lock — sgv1.js reads positional indexes (p:8, t:3, g:4)."""
    from src.render.search_index import _fetch_search_index

    d = _fetch_search_index(db)
    assert d["v"] == 3
    assert all(len(row) == 8 for row in d["p"])
    assert all(len(row) == 3 for row in d["t"])
    assert all(len(row) == 4 for row in d["g"])
    assert all(len(row) == 5 for row in d["c"])


def test_sg_index_cat_buckets(db):
    """cat lauks (P_CAT=7): 0=politiķis, 1=komentētājs, 2=iestāde/medijs."""
    from src.render.search_index import _fetch_search_index

    cats = {row[0]: row[7] for row in _fetch_search_index(db)["p"]}
    assert cats["Jānis Vītols"] == 0       # party → Amatpersonas → politiķis
    assert cats["Brīvā Žurnāliste"] == 1   # journalist → komentētājs
    assert cats["Ziņu Aģentūra"] == 2      # organization → iestāde/medijs


def test_fetch_excludes_inactive_and_commentator(db):
    from src.render.search_index import _fetch_search_index

    names = [row[0] for row in _fetch_search_index(db)["p"]]
    assert "Jānis Vītols" in names
    assert "Brīvā Žurnāliste" in names
    assert "Slēptais Politiķis" not in names
    assert "Vecais Komentētājs" not in names


def test_fetch_counts_confirmed_contradictions_only(db):
    """confirmed=0 excluded; confirmed=NULL counted — the COALESCE contract."""
    from src.render.search_index import _fetch_search_index

    vitols = next(r for r in _fetch_search_index(db)["p"] if r[0] == "Jānis Vītols")
    assert vitols[6] == 2  # 1 confirmed + 1 NULL; the 0-row excluded
    assert vitols[5] == 2  # position claims only (saeima_vote excluded)


def test_fetch_topic_counts_position_only_and_active_only(db):
    from src.render.search_index import _fetch_search_index

    topics = {row[0]: row[2] for row in _fetch_search_index(db)["t"]}
    assert topics["Budžets un finanses"] == 2  # saeima_vote row not counted
    assert "Vēlēšanas" not in topics            # only claim came from inactive pol


def test_fetch_contradictions_confirmed_and_active_only(db):
    """`c` list: confirmed + active-politician gate, id DESC, arity-5 tuples."""
    from src.render.search_index import _fetch_search_index

    c = _fetch_search_index(db)["c"]
    ids = [row[1] for row in c]
    assert ids == [3, 1]                     # id DESC; #2 (confirmed=0) + #4 (inactive) excluded
    first = c[0]
    assert first[2] == "Jānis Vītols"        # politician_name via JOIN
    assert first[3] == "direct_contradiction"  # severity
    assert first[4] == "Nodokļi"             # topic


def test_fetch_contradiction_label_truncated_on_word_boundary(db):
    """Long summaries clip to ~80 chars on a word boundary with an ellipsis."""
    from src.render.search_index import _fetch_search_index

    label = next(row[0] for row in _fetch_search_index(db)["c"] if row[1] == 1)
    assert label.endswith("…")
    assert len(label) <= 81                  # 80 + ellipsis
    assert " " not in label[-1]              # no dangling partial word/space


def test_emit_sg_index_writes_payload_and_compressed_variants(tmp_path, db):
    from src.render.search_index import render_search_index

    atmina = tmp_path / "atmina"
    atmina.mkdir()
    render_search_index(db, atmina)

    dest = atmina / "data" / "sg-index.json"
    assert dest.exists()
    loaded = json.loads(dest.read_text(encoding="utf-8"))
    assert loaded["v"] == 3
    # Diacritics survive (ensure_ascii=False).
    assert "Jānis Vītols" in dest.read_text(encoding="utf-8")
    br = atmina / "data" / "sg-index.json.br"
    gz = atmina / "data" / "sg-index.json.gz"
    assert br.exists() and br.stat().st_size > 0
    assert gz.exists() and gz.stat().st_size > 0
