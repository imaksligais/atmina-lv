"""Paritātes audits atlasa turpinājuma sēdi pēc JEBKURA tās datuma.

2026-09-03 Saeimai bija otra sēde — 07-23 ārkārtas sesijas sēdes turpinājums
(kalendārā `23 / 3(As)`, UUID `886631a9…`). Manifestā šis UUID stāv tikai ar
datumu 2026-07-23, tāpēc `--dates 2026-09-03` to neatlasīja un audits ziņoja
zaļu, kamēr DB trūka 4 balsojumu. Tagad īpašnieka rindai ir `continued_on`,
un atlase iet caur `_session_dates()`.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

from src.saeima.convocation import base_url

REPO = Path(__file__).resolve().parent.parent


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, REPO / "scripts" / filename)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_dates_filter_selects_continuation_of_older_sitting():
    audit = _load("audit_parity", "audit_saeima_agenda_parity.py")
    in_year = [
        {"year": 2026, "month": 7, "day": 23, "session_type": "arkartas_sesija", "uuid": "a",
         "continued_on": ["2026-09-03"]},
        {"year": 2026, "month": 9, "day": 3, "session_type": "regular", "uuid": "b"},
    ]
    selected, future = audit._select_sessions(in_year, ["2026-09-03"], "2026-09-25")
    assert sorted(s["uuid"] for s in selected) == ["a", "b"]
    assert audit._uncovered_dates(in_year, ["2026-09-03"]) == []


def test_old_manifest_without_continued_on_still_selects_by_base_date():
    """Vecos manifestos atslēgas nav — lasītājs lieto `s.get("continued_on", [])`."""
    audit = _load("audit_parity_old", "audit_saeima_agenda_parity.py")
    in_year = [{"year": 2026, "month": 7, "day": 23, "session_type": "regular", "uuid": "a"}]
    assert audit._session_dates(in_year[0]) == ["2026-07-23"]
    selected, future = audit._select_sessions(in_year, ["2026-07-23"], "2026-09-25")
    assert [s["uuid"] for s in selected] == ["a"]
    assert future == []


def test_future_filter_is_by_base_date_and_listed():
    """Nākotnes sēde tiek izlaista un NOSAUKTA (`future`), ne klusi nomesta."""
    audit = _load("audit_parity_future", "audit_saeima_agenda_parity.py")
    in_year = [
        {"year": 2026, "month": 9, "day": 3, "session_type": "regular", "uuid": "a"},
        {"year": 2026, "month": 10, "day": 1, "session_type": "regular", "uuid": "b"},
    ]
    selected, future = audit._select_sessions(in_year, [], "2026-09-25")
    assert [s["uuid"] for s in selected] == ["a"]
    assert [s["uuid"] for s in future] == ["b"]


def test_main_audits_the_owning_agenda_for_a_continuation_date(tmp_path, monkeypatch, capsys):
    """Viss ceļš caur `main()`: `--dates 2026-09-03` apmeklē 07-23 darba kārtību
    un rindā nosauc turpinājumu. Pirms labojuma 3. vārti te apstājās vai —
    ja 09-03 bija cita sēde — 07-23 darba kārtība netika atvērta nemaz."""
    audit = _load("audit_parity_main", "audit_saeima_agenda_parity.py")
    manifest = tmp_path / "sessions.json"
    manifest.write_text(json.dumps({
        "generated_at": "2026-09-25",
        "sessions": [
            {"year": 2026, "month": 7, "day": 23, "session_type": "arkartas_sesija",
             "uuid": "8" * 36, "url": "https://example.invalid",
             "continued_on": ["2026-09-03"]},
        ],
    }), encoding="utf-8")
    monkeypatch.setattr(audit, "MANIFEST_PATH", manifest)
    seen = []

    def _fetch(url, *_a, **_kw):
        seen.append(url)
        return "<html></html>"

    monkeypatch.setattr(audit, "_fetch", _fetch)
    monkeypatch.setattr(audit, "_db_index", lambda: (set(), set()))
    monkeypatch.setattr(sys, "argv", ["audit", "--year", "2026", "--dates", "2026-09-03",
                                      "--delay", "0"])

    assert audit.main() == 0
    # Rinda bez `convocation` atslēgas = 14. sasaukums (LIVS14).
    assert seen == [f"{base_url(14)}/DK?ReadForm&nr={'8' * 36}"]
    assert "(turpinājums: 2026-09-03)" in capsys.readouterr().out
