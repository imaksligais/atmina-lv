"""`/.well-known/security.txt` (RFC 9116) sargi.

Failu raksta renderis `static` domēnā blakus robots.txt — saturs nav statisks
asets, jo lauks `Expires` ir atkarīgs no renderēšanas brīža. Tests sauc tieši
rakstīšanas palīgu, nevis pilno renderu (ātrums + neatkarība no DB).

Kāpēc katrs apgalvojums:
  * lauki — RFC 9116 prasa `Contact` un `Expires`; `Canonical` un `Policy`
    piesaista failu vienai adresei un publiskajai kontaktu lapai;
  * `Expires` nākotnē un ≤ 365 dienas — RFC 9116 5. sadaļa neļauj bezgalīgu
    termiņu, un pagājis termiņš padara failu nederīgu;
  * LF + beigu rindas pārnesums — Windows `write_text` citādi dod CRLF, un
    Cloudflare faila saturu atdod baitos tādu, kāds tas ir kokā.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.render._orchestrator import _write_security_txt, security_txt

_NOW = datetime(2026, 9, 16, 12, 34, 56, tzinfo=timezone.utc)
_REDIRECTS = Path(__file__).resolve().parents[1] / "assets" / "_redirects"


def _fields(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in text.splitlines():
        if line.strip() and not line.lstrip().startswith("#"):
            key, _, value = line.partition(":")
            out[key.strip()] = value.strip()
    return out


def test_required_rfc9116_fields_present():
    f = _fields(security_txt(_NOW))
    assert f["Contact"] == "mailto:info@atmina.lv"
    assert f["Preferred-Languages"] == "lv, en"
    assert f["Canonical"] == "https://atmina.lv/.well-known/security.txt"
    assert f["Policy"] == "https://atmina.lv/kontakti.html"
    assert "Expires" in f


def test_expires_is_rfc3339_utc_with_zero_seconds():
    raw = _fields(security_txt(_NOW))["Expires"]
    assert raw.endswith("Z"), raw
    parsed = datetime.strptime(raw, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    assert parsed.second == 0, raw


def test_expires_is_in_the_future_and_at_most_a_year_ahead():
    raw = _fields(security_txt(_NOW))["Expires"]
    parsed = datetime.strptime(raw, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    assert parsed > _NOW, raw
    assert parsed - _NOW <= timedelta(days=365), raw


def test_expires_tracks_render_time_not_a_fixed_date():
    later = _NOW + timedelta(days=30)
    assert _fields(security_txt(later))["Expires"] != _fields(security_txt(_NOW))["Expires"]


def test_naive_datetime_is_treated_as_utc():
    naive = _NOW.replace(tzinfo=None)
    assert _fields(security_txt(naive))["Expires"] == _fields(security_txt(_NOW))["Expires"]


def test_writer_puts_the_file_under_dot_well_known_with_lf_only(tmp_path):
    dest = _write_security_txt(tmp_path, now=_NOW)
    assert dest == tmp_path / ".well-known" / "security.txt"
    raw = dest.read_bytes()
    assert b"\r\n" not in raw, "CRLF — Cloudflare atdod baitus tādus, kādi tie ir kokā"
    assert raw.endswith(b"\n")
    assert raw.decode("utf-8") == security_txt(_NOW)


def test_writer_creates_the_directory_when_missing(tmp_path):
    dest = _write_security_txt(tmp_path / "jauns", now=_NOW)
    assert dest.exists()


def test_writer_defaults_to_now_when_no_timestamp_given(tmp_path):
    dest = _write_security_txt(tmp_path)
    raw = _fields(dest.read_text(encoding="utf-8"))["Expires"]
    parsed = datetime.strptime(raw, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    assert parsed > datetime.now(timezone.utc)


def test_short_url_redirects_to_the_well_known_path():
    """`/security.txt` ir iesakņojies paradums; RFC 9116 adrese ir `/.well-known/`."""
    lines = _REDIRECTS.read_text(encoding="utf-8").splitlines()
    rules = [ln.split() for ln in lines if ln.strip() and not ln.lstrip().startswith("#")]
    assert ["/security.txt", "/.well-known/security.txt", "301"] in rules, rules
