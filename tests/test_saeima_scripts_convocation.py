"""15. Saeimas gatavība — skripti: katra sēde iet uz SAVA sasaukuma bāzi.

Kļūme, ko ķer: pēc pārslēgšanas uz 15. Saeimu 14. sasaukuma sēžu audits klusi
iet uz LIVS15 (vai manifesta pārģenerēšana izmet 14. sasaukuma sēdes) un
ziņo „trūkst 0” par sēdēm, ko nekad nav redzējis."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from src.saeima.convocation import base_url

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, REPO / "scripts" / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


p3u = _load("p3u_conv", "p3_backfill_year_urllib.py")
parity = _load("parity_conv", "audit_saeima_agenda_parity.py")
p3x = _load("p3x_conv", "_p3_extract_sessions_2026-05-26.py")
missing = _load("missing_conv", "ingest_saeima_missing_votes.py")

HEX = "A" * 32


def test_vote_urls_use_passed_base():
    html = f'<a href="./0/{HEX}?OpenDocument">x</a>'
    assert p3u._extract_vote_urls_from_agenda(html, base=base_url(15)) == [
        f"{base_url(15)}/0/{HEX}?OpenDocument"
    ]
    assert p3u._extract_vote_urls_from_agenda(html) == [
        f"{base_url()}/0/{HEX}?OpenDocument"   # noklusējums = kārtējais sasaukums
    ]


def test_audit_session_uses_row_convocation(monkeypatch):
    seen: list[str] = []
    monkeypatch.setattr(parity, "_fetch", lambda url: seen.append(url) or "")
    parity.audit_session({"year": 2026, "month": 12, "day": 3, "uuid": "u1",
                          "session_type": "regular", "convocation": 15}, set(), set(), 0)
    parity.audit_session({"year": 2026, "month": 9, "day": 24, "uuid": "u2",
                          "session_type": "regular"}, set(), set(), 0)
    assert seen == [
        f"{base_url(15)}/DK?ReadForm&nr=u1",
        f"{base_url(14)}/DK?ReadForm&nr=u2",
    ]


def test_doc_nr_regexes_accept_lp15():
    assert p3u._DOC_NR_RE.search("Likumprojekts (1/Lp15)").group(1) == "1/Lp15"
    assert p3u._BILL_LIKE_RE.search("(1/Lp15)")
    assert missing._DOC_NR_RE.search("Likumprojekts (1/Lp15)").group(1) == "1/Lp15"


def test_manifest_merge_keeps_other_convocations():
    old = [{"year": 2026, "month": 9, "day": 24, "uuid": "a"},                  # bez atslēgas = 14
           {"year": 2026, "month": 12, "day": 3, "uuid": "b", "convocation": 15}]
    new = [{"year": 2026, "month": 12, "day": 3, "uuid": "c", "convocation": 15}]
    merged = p3x._merge_convocation_rows(old, new, convocation=15)
    assert {r["uuid"] for r in merged} == {"a", "c"}


def test_backfill_process_session_uses_row_convocation(monkeypatch, tmp_path):
    """Backfill iet uz SĒDES sasaukuma darba kārtību, ne uz kārtējā sasaukuma.

    Tukša darba kārtība atgriežas pirms jebkura DB koda (`empty_session`)."""
    seen: list[str] = []
    monkeypatch.setattr(p3u, "_fetch", lambda url: seen.append(url) or "")
    log_file = tmp_path / "backfill.log"
    r15 = p3u.process_session({"year": 2026, "month": 12, "day": 3, "uuid": "u1",
                               "session_type": "regular", "convocation": 15}, 2026, log_file)
    r14 = p3u.process_session({"year": 2026, "month": 9, "day": 24, "uuid": "u2",
                               "session_type": "regular"}, 2026, log_file)
    assert seen == [
        f"{base_url(15)}/DK?ReadForm&nr=u1",
        f"{base_url(14)}/DK?ReadForm&nr=u2",
    ]
    assert r15 == r14 == {"empty_session": True, "votes": 0}


_SNAPSHOT_15 = """
- generic [ref=e1]: 2026. gads.
  - row [ref=e3]:
    - cell "Novembris" [ref=e4]
    - cell [ref=e5]:
      - link "5" [ref=e6] [cursor=pointer]:
        - /url: ./DK?ReadForm&nr=55555555-5555-5555-5555-555555555555
"""


def test_parse_calendar_rows_carry_convocation():
    sessions, unparsed = p3x.parse_calendar(_SNAPSHOT_15, convocation=15)
    assert unparsed == []
    assert [(s["convocation"], s["url"]) for s in sessions] == [
        (15, f"{base_url(15)}/DK?ReadForm&nr=55555555-5555-5555-5555-555555555555"),
    ]


def test_generator_keeps_other_convocation_rows(tmp_path):
    """Pārslēgšanas dienas scenārijs: `--convocation 15` pārģenerēšana patur
    esošā manifesta 14. sasaukuma rindas (rinda bez atslēgas = 14)."""
    import json

    snap = tmp_path / "page-test.yml"
    snap.write_text(_SNAPSHOT_15, encoding="utf-8")
    out = tmp_path / "sessions.json"
    old14 = {"year": 2026, "month": 9, "day": 24, "session_type": "regular",
             "uuid": "44444444-4444-4444-4444-444444444444",
             "url": f"{base_url(14)}/DK?ReadForm&nr=44444444-4444-4444-4444-444444444444"}
    out.write_text(json.dumps({"generated_at": "2026-09-27", "sessions": [old14]}),
                   encoding="utf-8")

    rc = p3x.main(["--snapshot", str(snap), "--out", str(out),
                   "--max-year", "2026", "--convocation", "15"])
    assert rc == 0
    rows = json.loads(out.read_text(encoding="utf-8"))["sessions"]
    assert old14 in rows, "14. sasaukuma rinda pārģenerēšanā nedrīkst pazust"
    new = [r for r in rows if r["uuid"] == "55555555-5555-5555-5555-555555555555"]
    assert len(new) == 1 and new[0]["convocation"] == 15
    assert new[0]["url"].startswith(base_url(15))
    assert len(rows) == 2


def test_generator_stops_on_zero_parsed_sessions(tmp_path, capsys):
    """T8 viltus zaļais: 0 parsētu sēžu + esošais manifests → apvienošana
    paturētu citu sasaukumu rindas, atjaunotu `generated_at` un izietu ar 0.
    Jāapstājas PIRMS rakstīšanas, manifests paliek neskarts."""
    import json

    snap = tmp_path / "page-test.yml"
    snap.write_text("- generic [ref=e1]: 2026. gads.\n", encoding="utf-8")
    out = tmp_path / "sessions.json"
    old14 = {"year": 2026, "month": 9, "day": 24, "session_type": "regular",
             "uuid": "44444444-4444-4444-4444-444444444444",
             "url": f"{base_url(14)}/DK?ReadForm&nr=44444444-4444-4444-4444-444444444444"}
    out.write_text(json.dumps({"generated_at": "2026-09-01", "sessions": [old14]}),
                   encoding="utf-8")
    before = out.read_bytes()

    rc = p3x.main(["--snapshot", str(snap), "--out", str(out),
                   "--max-year", "2026", "--convocation", "15"])
    assert rc == 1, "0 parsētu sēžu nedrīkst iziet ar 0"
    assert out.read_bytes() == before, "manifests nedrīkst mainīties"
    assert "STOP" in capsys.readouterr().err


def test_check_new_votes_stops_on_empty_agenda(monkeypatch, capsys):
    """0 balsojumu saišu darba kārtībā nav „NAV JAUNU” (T8/T12): pēc
    pārslēgšanas noklusējuma 14. sasaukuma UUID atveras zem LIVS15 tukšs.
    STOP notiek pirms DB atvēršanas."""
    check = _load("check_new_conv", "check_new_session_votes.py")
    monkeypatch.setattr(check, "_fetch", lambda url: "")

    def _no_db(*_a, **_kw):
        raise AssertionError("DB nedrīkst atvērt, ja darba kārtība ir tukša")

    monkeypatch.setattr(check.sqlite3, "connect", _no_db)
    monkeypatch.setattr(sys, "argv", ["check_new_session_votes.py", "u1"])
    assert check.main() == 2
    out = capsys.readouterr().out
    assert "STOP" in out and "NAV JAUNU" not in out
