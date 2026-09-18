"""verify_host.py — katra pārbaude ziņo, cik ko apskatīja (denominators)."""
import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("verify_host", _ROOT / "scripts" / "verify_host.py")
vh = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vh)

CSP = "default-src 'self'; script-src 'self' https://cloud.umami.is"


def _security_txt(expires: datetime) -> bytes:
    return (
        "Contact: mailto:info@atmina.lv\n"
        f"Expires: {expires.strftime('%Y-%m-%dT%H:%M:%SZ')}\n"
        "Preferred-Languages: lv, en\n"
        "Canonical: https://atmina.lv/.well-known/security.txt\n"
        "Policy: https://atmina.lv/kontakti.html\n"
    ).encode()


def _fake_site(redirect_html: bool = False, security_txt: bytes | None = -1, server="cloudflare"):
    """`security_txt=None` → 404; baiti → tāds saturs; noklusējums → derīgs fails."""
    if security_txt == -1:
        security_txt = _security_txt(datetime.now(timezone.utc) + timedelta(days=180))

    def fetch(url: str) -> vh.Response:
        path = url.split("//", 1)[1].split("/", 1)[1] if "/" in url.split("//", 1)[1] else ""
        h = {
            "server": server,
            "content-security-policy": CSP,
            "strict-transport-security": "max-age=31536000",
            "x-content-type-options": "nosniff",
            "x-frame-options": "SAMEORIGIN",
            "referrer-policy": "strict-origin-when-cross-origin",
        }
        if path in ("404.html", "nav-tada-lapa-xyz"):
            status = 200 if path == "404.html" else 404
            return vh.Response(status, h, b"<html>Lapa nav atrasta</html>")
        if path.endswith(".html"):
            if redirect_html:
                return vh.Response(308, {"location": "/" + path[:-5]}, b"")
            return vh.Response(200, h, b"<html>ok</html>")
        if path.endswith(".json"):
            return vh.Response(200, {**h, "content-encoding": "br"}, b"{}")
        if path in ("robots.txt", "sitemap.xml"):
            return vh.Response(200, h, b"x")
        if path == ".well-known/security.txt":
            if security_txt is None:
                return vh.Response(404, h, b"")
            return vh.Response(200, h, security_txt)
        if path.startswith("images/briefs/"):
            return vh.Response(200, h, b"png")
        return vh.Response(404, h, b"")
    return fetch


SITEMAP = [f"https://atmina.lv/politiki/p{i}.html" for i in range(30)]


def test_all_checks_pass_on_good_host():
    checks = vh.run_checks("https://x.example", SITEMAP, _fake_site(), sample=20,
                           hero_paths=["images/briefs/a.png", "images/briefs/b.png"])
    assert all(c.passed for c in checks), [c for c in checks if not c.passed]
    by = {c.name: c for c in checks}
    assert by["sitemap_html_200_no_redirect"].examined == 20
    assert by["hero_images"].examined == 2
    assert by["security_txt"].examined == 1
    assert len(checks) == 9
    assert by["served_by_cloudflare"].examined == 1


def test_missing_security_txt_is_a_failure():
    checks = vh.run_checks("https://x.example", SITEMAP, _fake_site(security_txt=None),
                           sample=5, hero_paths=["images/briefs/a.png"])
    by = {c.name: c for c in checks}
    assert not by["security_txt"].passed
    assert "404" in by["security_txt"].detail
    assert by["security_txt"].examined == 1


def test_expired_security_txt_is_a_failure():
    stale = _security_txt(datetime.now(timezone.utc) - timedelta(days=1))
    checks = vh.run_checks("https://x.example", SITEMAP, _fake_site(security_txt=stale),
                           sample=5, hero_paths=["images/briefs/a.png"])
    by = {c.name: c for c in checks}
    assert not by["security_txt"].passed
    assert "Expires" in by["security_txt"].detail


def test_security_txt_without_contact_is_a_failure():
    no_contact = b"Expires: 2099-01-01T00:00:00Z\n"
    checks = vh.run_checks("https://x.example", SITEMAP, _fake_site(security_txt=no_contact),
                           sample=5, hero_paths=["images/briefs/a.png"])
    by = {c.name: c for c in checks}
    assert not by["security_txt"].passed
    assert "Contact" in by["security_txt"].detail


def test_html_redirect_is_a_failure():
    checks = vh.run_checks("https://x.example", SITEMAP, _fake_site(redirect_html=True), sample=5,
                           hero_paths=[])
    by = {c.name: c for c in checks}
    assert not by["sitemap_html_200_no_redirect"].passed
    assert "308" in by["sitemap_html_200_no_redirect"].detail


def test_zero_denominator_is_a_failure():
    checks = vh.run_checks("https://x.example", [], _fake_site(), sample=20, hero_paths=[])
    by = {c.name: c for c in checks}
    assert not by["sitemap_html_200_no_redirect"].passed
    assert by["sitemap_html_200_no_redirect"].examined == 0
    assert not by["hero_images"].passed
    assert by["hero_images"].examined == 0


def test_old_host_answering_is_a_failure():
    """Novecojis lokālais DNS 2026-09-16 sūtīja `atmina.lv` uz veco Namecheap hostu
    (`server: LiteSpeed`); visas citas pārbaudes tur var būt zaļas."""
    checks = vh.run_checks("https://x.example", SITEMAP, _fake_site(server="LiteSpeed"), sample=20,
                           hero_paths=["images/briefs/a.png"])
    by = {c.name: c for c in checks}
    assert not by["served_by_cloudflare"].passed
    assert "LiteSpeed" in by["served_by_cloudflare"].detail
    assert all(c.passed for c in checks if c.name != "served_by_cloudflare")
