"""`parentID=` balsojumu saites: labojuma skripts un paritātes vārti.

Kļūme, ko ķer pirmais tests: labojuma SQL nomaina saiti rindai, kuras lapa nav tas
pats balsojums (citas kopsummas), vai rindai, kuras jaunā saite jau ir aizņemta; vai
skripts pats aiztiek DB. Otrais: nedēļu veca tukša saite paritātes auditā paliek zaļa.

Tīkla nav, dzīvā DB netiek aiztikta. Pie `test_blog_dead_vote_links.py` (kartējuma
lietošana renderā) šie neatkārtojas: tas nerada kartējumu un neskatās DB.
"""

from __future__ import annotations

import importlib.util
import json
import sqlite3
import sys
from datetime import date
from pathlib import Path

from src.db import init_db
from src.saeima.schema import init_saeima_bills, init_saeima_tables

REPO = Path(__file__).resolve().parent.parent
BASE = "https://titania.saeima.lv/LIVS14/SaeimaLIVS2_DK.nsf"
DAY = "2020-03-05"
UUID = "a" * 8 + "-1111-2222-3333-" + "b" * 12


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, REPO / "scripts" / filename)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _old(n: int) -> str:
    return f"{BASE}/Voting?ReadForm&parentID={n:08d}-0000-0000-0000-000000000000"


def _new(n: int) -> str:
    return f"{BASE}/0/{n:032X}?OpenDocument"


def _page(motif: str, vtime: str, totals: tuple[int, int, int], deputies: int) -> str:
    """Lapa tādā formā, kādu lasa `_parse_vote_page()`."""
    entries = ",".join(f'"{i}.�Dep{i}�ZZS�Par"' for i in range(deputies))
    return (
        f"<span>Balsošanas motīvs: </span><b>{motif}</b>"
        f"<span>Datums: </span><b>05.03.2020 {vtime} </b>"
        f"par {totals[0]}, pret {totals[1]}, atturas {totals[2]}"
        f"<script>var voteFullListByNames=[{entries}];</script>"
    )


def _make_db(path: Path) -> sqlite3.Connection:
    init_db(str(path))
    init_saeima_tables(str(path))
    init_saeima_bills(str(path))
    return sqlite3.connect(path)


def _add_vote(db, url: str, vday: str, vtime: str, motif: str = "Par likumu",
              totals: tuple[int, int, int] = (50, 40, 1), deputies: int = 3) -> int:
    vote_id = db.execute(
        "INSERT INTO saeima_votes (motif, vote_date, vote_time, total_par, total_pret, total_atturas, url)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (motif, vday, vtime, *totals, url),
    ).lastrowid
    for i in range(deputies):
        db.execute("INSERT INTO saeima_individual_votes (vote_id, deputy_name, vote) VALUES (?, ?, 'Par')",
                   (vote_id, f"Dep{i}"))
    return vote_id


def _add_claim(db, url: str) -> None:
    db.execute("INSERT INTO claims (topic, stance, source_url, claim_type) VALUES ('Budžets un finanses', 'x', ?, 'saeima_vote')",
               (url,))


def _urls(db) -> dict[int, str]:
    return dict(db.execute("SELECT id, url FROM saeima_votes"))


def test_only_the_clean_row_reaches_sql_and_map_and_script_never_writes_db(tmp_path, monkeypatch, capsys):
    db_path = tmp_path / "t.db"
    db = _make_db(db_path)
    clean = _add_vote(db, _old(1), DAY, "12:00:01")
    _add_claim(db, _old(1))
    # Lapai citas kopsummas: cits balsojums vai sabojāta rinda.
    _add_vote(db, _old(2), DAY, "12:00:02")
    # Tas pats (datums, laiks) jau ir citā rindā ar pastāvīgo saiti: dublikāts.
    _add_vote(db, _old(3), DAY, "12:00:03")
    _add_vote(db, _new(3), DAY, "12:00:03")
    # Pastāvīgā saite jau ir kādam claim: mainot source_url, rastos sadursme (#3).
    _add_vote(db, _old(4), DAY, "12:00:04")
    _add_claim(db, _new(4))
    # Dienai manifestā nav sēdes.
    _add_vote(db, _old(5), "2020-04-01", "09:00:00")
    db.commit()
    before = _urls(db)

    manifest = tmp_path / "sessions.json"
    manifest.write_text(json.dumps({
        "generated_at": "2020-05-01",
        "sessions": [{"year": 2020, "month": 3, "day": 5, "session_type": "regular", "uuid": UUID,
                      "url": "https://example.invalid", "convocation": 14}],
    }), encoding="utf-8")
    map_path = tmp_path / "map.json"
    map_path.write_text('{\n"https://z.invalid/esoss": "https://z.invalid/jauns"\n}\n', encoding="utf-8")
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    agenda = "".join(f'<a href="./0/{n:032X}?OpenDocument">x</a>' for n in (1, 2, 3, 4))
    pages = {
        f"{BASE}/DK?ReadForm&nr={UUID}": agenda,
        _new(1): _page("Par likumu", "12:00:01", (50, 40, 1), 3),
        _new(2): _page("Par likumu", "12:00:02", (51, 39, 1), 3),
        _new(4): _page("Par likumu", "12:00:04", (50, 40, 1), 3),
    }
    fix = _load("fix_parentid", "fix_parentid_vote_urls.py")
    monkeypatch.setattr(fix, "_fetch", pages.__getitem__)
    common = ["fix", "--db", str(db_path), "--manifest", str(manifest), "--map", str(map_path),
              "--out-dir", str(out_dir), "--delay", "0"]

    # Noklusējums tikai lasa: nav failu, kartējums tas pats.
    monkeypatch.setattr(sys, "argv", common)
    map_before = map_path.read_text(encoding="utf-8")
    assert fix.main() == 1, "ja kaut viena rinda palikusi, iznākums nav zaļš"
    printed = capsys.readouterr().out
    for line in ("kopā 5", "kartēti 3", "tīri 1", "ar problēmām 3", "nav atrasti 1", "kļūdas 0"):
        assert line in printed
    assert list(out_dir.iterdir()) == []
    assert map_path.read_text(encoding="utf-8") == map_before

    # Ar karodziņu: pārī SQL tikai tīrajai rindai.
    monkeypatch.setattr(sys, "argv", [*common, "--write"])
    assert fix.main() == 1
    capsys.readouterr()
    fix_sql = next(out_dir.glob("fix_*.sql")).read_text(encoding="utf-8")
    rollback_sql = next(out_dir.glob("rollback_*.sql")).read_text(encoding="utf-8")
    for sql in (fix_sql, rollback_sql):
        assert _new(1) in sql and _old(1) in sql
        for n in (2, 3, 4, 5):
            assert _new(n) not in sql and _old(n) not in sql
    assert "1 saeima_votes.url + 1 claims.source_url" in fix_sql
    assert json.loads(map_path.read_text(encoding="utf-8")) == {
        "https://z.invalid/esoss": "https://z.invalid/jauns",
        _old(1): _new(1),
    }

    assert _urls(db) == before, "skripts pats DB nemaina"

    # Pārī: labojums maina vienu rindu un tās claim; rollback atjauno visu.
    db.executescript(fix_sql)
    after = _urls(db)
    assert {vote_id for vote_id, url in before.items() if after[vote_id] != url} == {clean}
    assert after[clean] == _new(1)
    assert db.execute("SELECT source_url FROM claims WHERE source_url = ?", (_new(1),)).fetchone()
    db.executescript(rollback_sql)
    assert _urls(db) == before
    assert db.execute("SELECT COUNT(*) FROM claims WHERE source_url = ?", (_old(1),)).fetchone()[0] == 1
    db.close()


def test_parity_audit_fails_on_a_week_old_parentid_url(tmp_path, monkeypatch, capsys):
    db_path = tmp_path / "t.db"
    db = _make_db(db_path)
    stale = _add_vote(db, _old(1), DAY, "12:00:01")
    _add_vote(db, _old(2), date.today().isoformat(), "12:00:02")
    _add_vote(db, _new(3), DAY, "12:00:03")
    db.commit()

    audit = _load("audit_parity_parentid", "audit_saeima_agenda_parity.py")
    manifest = tmp_path / "sessions.json"
    manifest.write_text(json.dumps({
        "generated_at": "2020-05-01",
        "sessions": [{"year": 2020, "month": 3, "day": 5, "session_type": "regular", "uuid": UUID,
                      "url": "https://example.invalid", "convocation": 14}],
    }), encoding="utf-8")
    monkeypatch.setattr(audit, "MANIFEST_PATH", manifest)
    monkeypatch.setattr(audit, "DB_PATH", str(db_path))
    monkeypatch.setattr(audit, "_fetch", lambda url: "<html></html>")
    monkeypatch.setattr(sys, "argv", ["audit", "--year", "2020", "--dates", DAY, "--delay", "0"])

    assert audit.main() == 1
    captured = capsys.readouterr()
    assert "parentID= saites: 2 no 3 balsojumiem; vecākas par 7 dienām: 1" in captured.out
    assert "fix_parentid_vote_urls.py" in captured.err

    # Svaiga parentID= saite vēl nav kļūme, bet saucējs paliek redzams.
    db.execute("UPDATE saeima_votes SET url = ? WHERE id = ?", (_new(1), stale))
    db.commit()
    db.close()
    assert audit.main() == 0
    assert "parentID= saites: 1 no 3 balsojumiem; vecākas par 7 dienām: 0" in capsys.readouterr().out
