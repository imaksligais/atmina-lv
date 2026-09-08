"""Manifesta VECUMA vārti parity auditā — nolasīts manifests nav svaigs manifests.

Robs, kas to prasīja (2026-09-02): `data/saeima_backfill_sessions.json` pēdējo
reizi pārģenerēts 2026-08-01. 2026-08-20 sēdei bija DIVI sēžu UUID, un neviens
no tiem manifestā nebija. `--dates 2026-08-20` tāpēc nofiltrēja sarakstu līdz
TUKŠAM, audits neapmeklēja nevienu darba kārtību un izdrukāja „trūkst 0" — kamēr
DB tiešām trūka 25 balsojumu.

Esošais T8 STOP šo neķer: tas nostrādā tikai tad, kad manifestā nav VESELA gada
(`if not in_year:`). 2026. gads manifestā bija; tajā nebija tikai augusta beigu
sēžu. Vārti, kas nostrādā tikai pie visa gada trūkuma, ir vārti, kas nevar
nostrādāt tajā gadījumā, kura dēļ tie vispār pastāv.

Divi neatkarīgi vārti, abi ar izejas kodu 2:
  1. manifesta VECUMS — `generated_at` trūkst / vecāks par jaunāko pieprasīto
     datumu / (bez `--dates`) vecāks par 14 dienām;
  2. pieprasīts datums BEZ NEVIENAS manifesta rindas — datums, ko manifests
     neredz, ir manifesta robs, ne tīra diena.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent

TODAY = date.today()


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, REPO / "scripts" / filename)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _session(day_iso: str, uuid_seed: str = "1") -> dict:
    y, m, d = (int(x) for x in day_iso.split("-"))
    return {
        "year": y,
        "month": m,
        "day": d,
        "session_type": "regular",
        "uuid": uuid_seed * 36,
        "url": "https://example.invalid",
    }


def _write_manifest(path: Path, sessions: list[dict], generated_at: str | None,
                    legacy_bare_list: bool = False) -> None:
    if legacy_bare_list:
        payload: object = sessions
    else:
        payload = {"generated_at": generated_at, "sessions": sessions}
        if generated_at is None:
            payload = {"sessions": sessions}
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


@pytest.fixture()
def parity(request, tmp_path, monkeypatch):
    """Ielādēts audita modulis ar atslēgtu DB un tīklu; atgriež (mod, fetch_calls)."""
    mod = _load(f"audit_parity_gate_{request.node.name}", "audit_saeima_agenda_parity.py")
    calls: list[str] = []

    def _fetch(url, *_a, **_kw):
        calls.append(url)
        raise OSError("tīkls testā ir aizvērts")

    monkeypatch.setattr(mod, "_fetch", _fetch)
    monkeypatch.setattr(mod, "_db_index", lambda: (set(), set()))
    mod._test_fetch_calls = calls  # type: ignore[attr-defined]
    return mod


def _run(mod, monkeypatch, manifest: Path, argv: list[str]) -> int:
    monkeypatch.setattr(mod, "MANIFEST_PATH", manifest)
    monkeypatch.setattr(sys, "argv", ["audit", *argv])
    return mod.main()


# --------------------------------------------------------------------------
# 1. vārti — manifesta vecums
# --------------------------------------------------------------------------

def test_manifest_older_than_the_requested_date_stops(parity, tmp_path, monkeypatch, capsys):
    """Tieši 2026-09-02 gadījums: manifests no 08-01, prasīta 08-20 sēde."""
    manifest = tmp_path / "sessions.json"
    _write_manifest(manifest, [_session("2026-08-20")], generated_at="2026-08-01")

    rc = _run(parity, monkeypatch, manifest, ["--year", "2026", "--dates", "2026-08-20"])
    err = capsys.readouterr().err

    assert rc == 2, "novecojis manifests nedrīkst iziet ar 0"
    assert "STOP" in err
    assert "2026-08-01" in err, "kļūdai jānosauc manifesta datums"
    assert "2026-08-20" in err, "kļūdai jānosauc pieprasītais datums"
    assert "_p3_extract_sessions" in err, "jāpasaka, kā pārģenerēt"
    assert "Playwright" in err
    assert parity._test_fetch_calls == [], "STOP nāk PIRMS pirmās lapas ielādes"


def test_manifest_without_generated_at_stops(parity, tmp_path, monkeypatch, capsys):
    """Vecais formāts (kails saraksts) nenes ģenerēšanas datumu — vecums nav zināms."""
    manifest = tmp_path / "sessions.json"
    _write_manifest(manifest, [_session("2026-08-20")], generated_at=None,
                    legacy_bare_list=True)

    rc = _run(parity, monkeypatch, manifest, ["--year", "2026", "--dates", "2026-08-20"])
    err = capsys.readouterr().err

    assert rc == 2, "nezināms manifesta vecums nedrīkst iziet ar 0"
    assert "STOP" in err
    assert "generated_at" in err
    assert parity._test_fetch_calls == []


def test_manifest_key_present_but_null_stops(parity, tmp_path, monkeypatch, capsys):
    """Objekta formāts ar tukšu lauku ir tas pats nezināmais vecums."""
    manifest = tmp_path / "sessions.json"
    manifest.write_text(
        json.dumps({"generated_at": None, "sessions": [_session("2026-08-20")]}),
        encoding="utf-8",
    )
    rc = _run(parity, monkeypatch, manifest, ["--year", "2026", "--dates", "2026-08-20"])
    assert rc == 2
    assert "generated_at" in capsys.readouterr().err


def test_manifest_older_than_14_days_stops_when_no_dates_given(
    parity, tmp_path, monkeypatch, capsys
):
    """Bez `--dates` nav ko salīdzināt ar konkrētu dienu — der 14 dienu slieksnis."""
    manifest = tmp_path / "sessions.json"
    stale = (TODAY - timedelta(days=32)).isoformat()
    _write_manifest(manifest, [_session("2026-01-16")], generated_at=stale)

    rc = _run(parity, monkeypatch, manifest, ["--year", "2026"])
    err = capsys.readouterr().err

    assert rc == 2
    assert stale in err
    assert "14" in err, "slieksnim jābūt nosauktam skaitliski"
    assert parity._test_fetch_calls == []


def test_recent_manifest_passes_the_gate_without_dates(parity, tmp_path, monkeypatch, capsys):
    manifest = tmp_path / "sessions.json"
    fresh = (TODAY - timedelta(days=3)).isoformat()
    _write_manifest(manifest, [_session("2026-01-16")], generated_at=fresh)

    _run(parity, monkeypatch, manifest, ["--year", "2026", "--delay", "0"])
    out = capsys.readouterr().out

    assert parity._test_fetch_calls, "svaigam manifestam vārtiem jālaiž cauri līdz tīklam"
    assert "Auditējamas sēdes: 1" in out, "saucēja rinda paliek nemainīta"


# --------------------------------------------------------------------------
# 2. vārti — pieprasīts datums bez nevienas manifesta rindas
# --------------------------------------------------------------------------

def test_requested_date_absent_from_manifest_stops(parity, tmp_path, monkeypatch, capsys):
    """Svaigs manifests, kurā pieprasītās dienas vienkārši nav."""
    manifest = tmp_path / "sessions.json"
    _write_manifest(manifest, [_session("2026-08-19")], generated_at=TODAY.isoformat())

    rc = _run(parity, monkeypatch, manifest, ["--year", "2026", "--dates", "2026-08-20"])
    err = capsys.readouterr().err

    assert rc == 2, "datums, ko manifests neredz, nav tīra diena"
    assert "2026-08-20" in err
    assert "2026-08-19" not in err, "jānosauc tikai TRŪKSTOŠIE datumi"
    assert parity._test_fetch_calls == []


def test_every_absent_date_is_listed_not_just_the_first(parity, tmp_path, monkeypatch, capsys):
    manifest = tmp_path / "sessions.json"
    _write_manifest(manifest, [_session("2026-08-19")], generated_at=TODAY.isoformat())

    rc = _run(parity, monkeypatch, manifest,
              ["--year", "2026", "--dates", "2026-08-20,2026-08-21,2026-08-19"])
    err = capsys.readouterr().err

    assert rc == 2
    assert "2026-08-20" in err and "2026-08-21" in err


def test_requested_date_from_another_year_stops(parity, tmp_path, monkeypatch, capsys):
    """`--year 2025 --dates 2026-08-20` auditētu tukšumu — tas nav tīra diena."""
    manifest = tmp_path / "sessions.json"
    _write_manifest(manifest, [_session("2025-01-16"), _session("2026-08-20", "2")],
                    generated_at=TODAY.isoformat())

    rc = _run(parity, monkeypatch, manifest, ["--year", "2025", "--dates", "2026-08-20"])
    assert rc == 2
    assert "2026-08-20" in capsys.readouterr().err


def test_fresh_manifest_with_the_date_present_passes_the_gate(
    parity, tmp_path, monkeypatch, capsys
):
    """Pozitīvā kontrole: vārti nedrīkst apturēt derīgu skrējienu."""
    manifest = tmp_path / "sessions.json"
    _write_manifest(manifest, [_session("2026-08-20")], generated_at=TODAY.isoformat())

    rc = _run(parity, monkeypatch, manifest,
              ["--year", "2026", "--dates", "2026-08-20", "--delay", "0"])
    captured = capsys.readouterr()

    assert parity._test_fetch_calls, "vārtiem jālaiž cauri līdz darba kārtības ielādei"
    assert "Auditējamas sēdes: 1" in captured.out
    assert "MANIFEST" not in captured.err.upper().replace("MANIFESTA ROBS", "")
    # Tīkls testā ir aizvērts, tāpēc palaidiens beidzas ar fetch-kļūdas STOP (2),
    # NEVIS ar manifesta vārtiem — tas ir vecais, jau nolīgtais uzvedības ceļš.
    assert rc == 2
    assert "SEGUMS: nolasītas 0/1" in captured.out


# --------------------------------------------------------------------------
# Manifesta ielasītājs — abas formas, viena atbilde
# --------------------------------------------------------------------------

def test_loader_reads_both_manifest_shapes(tmp_path):
    from src.saeima.manifest import load_manifest

    sessions = [_session("2026-08-20")]
    wrapped = tmp_path / "wrapped.json"
    wrapped.write_text(json.dumps({"generated_at": "2026-09-02", "sessions": sessions}),
                       encoding="utf-8")
    bare = tmp_path / "bare.json"
    bare.write_text(json.dumps(sessions), encoding="utf-8")

    assert load_manifest(wrapped) == (sessions, "2026-09-02")
    assert load_manifest(bare) == (sessions, None)


def test_committed_manifest_carries_a_generated_at():
    """Repo manifestam JĀBŪT jaunajā formā — citādi katrs audits apstājas."""
    from src.saeima.manifest import MANIFEST_PATH, load_manifest

    sessions, generated_at = load_manifest(MANIFEST_PATH)
    assert generated_at, f"{MANIFEST_PATH.name} bez `generated_at` aptur katru auditu"
    assert date.fromisoformat(generated_at) <= TODAY
    assert len(sessions) > 100, f"aizdomīgi maz sēžu: {len(sessions)}"
