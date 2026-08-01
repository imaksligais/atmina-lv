"""Ārējo saišu jaunā-taba uzvedība (2026-07-24, operatora lēmums).

Ārējie linki (cits hosts, http/https) atveras jaunā tabā, lai lasītājs
nepamet atmina.lv. Implementācija: VIENS delegēts click-handlers
``assets/chrome-v1.js`` (chrome-sync to iznes arī uz kurētajām lapām; klikšķa
brīža delegācija sedz arī JS-renderēto saturu — bmv1 kartītes, feed vienumus —
bez per-template ``target=`` atribūtiem).

Šie testi sargā handlera trīs kontraktus:
  1. host-salīdzinājums (``a.host === location.host``) — nevis URL-prefiksa
     regex, lai absolūtas pašu-domēna saites paliek tajā pašā tabā;
  2. ``rel=noopener`` pievienošana — jaunā taba nedrīkst dabūt window.opener;
  3. eksplicīts ``target`` netiek pārrakstīts un ne-http(s) sheēmas
     (mailto:, enkuri, relatīvie ceļi) paliek neskartas.
"""

from pathlib import Path


def _chrome_js() -> str:
    return Path("assets/chrome-v1.js").read_text(encoding="utf-8")


def test_external_link_handler_present_with_host_guard():
    js = _chrome_js()
    assert "a.host === location.host" in js, (
        "ārējo saišu handleram jāsalīdzina hosts, ne URL prefikss"
    )
    assert "a.target = '_blank'" in js


def test_external_link_handler_adds_noopener():
    js = _chrome_js()
    assert "noopener" in js


def test_external_link_handler_respects_existing_target_and_schemes():
    js = _chrome_js()
    # Eksplicīts target (piem., apzināts _self) netiek pārrakstīts.
    assert "if (!a || a.target) return;" in js
    # Tikai http(s): mailto:, tel:, enkuri un relatīvie ceļi izkrīt uz regex.
    assert "/^https?:/i.test(href)" in js
