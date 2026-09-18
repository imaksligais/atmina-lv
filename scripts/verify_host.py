"""Dzīvā hosta pārbaude pēc deploy — katra rinda ar denominatoru.

  .venv/Scripts/python.exe scripts/verify_host.py --base https://atmina.<konts>.workers.dev
  .venv/Scripts/python.exe scripts/verify_host.py --base https://atmina.lv

Pārbaudes (spec 3. fāze): drošības galvenes uz 3 lapām; sitemap paraugs → 200
bez redirect (html_handling none vārts); nezināms URL → 404 ar 404.html saturu;
robots/sitemap; sidecar JSON saspiests; kurētais saturs; hero attēlu paraugs;
`/.well-known/security.txt` (RFC 9116) ar derīgu `Expires`.
Exit 1, ja kāda krīt VAI kādas denominators ir 0.
"""
from __future__ import annotations

import argparse
import random
import re
import sys
from collections import namedtuple
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

import httpx

Response = namedtuple("Response", "status headers body")
Check = namedtuple("Check", "name passed examined detail")

_REQUIRED_HEADERS = (
    "content-security-policy",
    "strict-transport-security",
    "x-content-type-options",
    "x-frame-options",
    "referrer-policy",
)
_JSON_SIDECARS = ("pozicijas-data.json", "data/balsojumi-matrica.json")


def http_fetch(url: str) -> Response:
    r = httpx.get(url, follow_redirects=False, timeout=20,
                  headers={"accept-encoding": "br, gzip"})
    return Response(r.status_code, {k.lower(): v for k, v in r.headers.items()}, r.content)


def sitemap_urls(path: Path) -> list[str]:
    return re.findall(r"<loc>([^<]+)</loc>", path.read_text(encoding="utf-8"))


def _path_of(url: str) -> str:
    rest = url.split("//", 1)[1]
    return rest.split("/", 1)[1] if "/" in rest else ""


def _parse_expires(body: str) -> datetime | None:
    """`Expires:` lauks no security.txt kā UTC datetime; None, ja nav/nederīgs."""
    m = re.search(r"^Expires:\s*(\S+)\s*$", body, re.MULTILINE)
    if not m:
        return None
    raw = m.group(1)
    try:
        # `Z` → `+00:00` skaidrības pēc: fromisoformat to prot tikai no 3.11.
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None  # RFC 9116 prasa nobīdi; bez tās vērtība nav nepārprotama.
    return parsed.astimezone(timezone.utc)


def run_checks(base: str, sitemap: list[str], fetch: Callable[[str], Response],
               sample: int = 20, hero_paths: list[str] | None = None,
               rng: random.Random | None = None) -> list[Check]:
    rng = rng or random.Random(0)
    base = base.rstrip("/")
    out: list[Check] = []

    # 1. drošības galvenes uz 3 lapām
    pages = ["index.html", "personas.html", "blog.html"]
    missing = []
    for p in pages:
        r = fetch(f"{base}/{p}")
        for h in _REQUIRED_HEADERS:
            if h not in r.headers:
                missing.append(f"{p}:{h}")
        csp = r.headers.get("content-security-policy", "")
        script_src = next((d for d in csp.split(";") if d.strip().startswith("script-src")), "")
        if "'unsafe-inline'" in script_src:
            missing.append(f"{p}:script-src unsafe-inline")
    out.append(Check("security_headers", not missing, len(pages), ", ".join(missing) or "ok"))

    # 2. sitemap paraugs: .html → 200, bez 30x
    html = [u for u in sitemap if u.endswith(".html")]
    picked = rng.sample(html, min(sample, len(html))) if html else []
    bad = []
    for u in picked:
        r = fetch(f"{base}/{_path_of(u)}")
        if r.status != 200:
            bad.append(f"{_path_of(u)} → {r.status}")
    out.append(Check("sitemap_html_200_no_redirect", bool(picked) and not bad,
                     len(picked), "; ".join(bad[:5]) or "ok"))

    # 3. 404 ar 404.html saturu
    r404 = fetch(f"{base}/nav-tada-lapa-xyz")
    page404 = fetch(f"{base}/404.html")
    ok404 = r404.status == 404 and page404.status == 200 and r404.body == page404.body
    out.append(Check("custom_404", ok404, 2,
                     f"status {r404.status}, body match {r404.body == page404.body}"))

    # 4. robots + sitemap
    rs = [fetch(f"{base}/robots.txt").status, fetch(f"{base}/sitemap.xml").status]
    out.append(Check("robots_sitemap", rs == [200, 200], 2, str(rs)))

    # 5. sidecar JSON saspiests
    enc = []
    for j in _JSON_SIDECARS:
        r = fetch(f"{base}/{j}")
        enc.append(f"{j}:{r.status}/{r.headers.get('content-encoding', '-')}")
    ok_json = all(":200/" in e and e.split("/")[-1] in ("br", "gzip") for e in enc)
    out.append(Check("json_compressed", ok_json, len(_JSON_SIDECARS), ", ".join(enc)))

    # 6. kurētais saturs
    cur = ["finanses.html", "statistika.html"]
    st = [fetch(f"{base}/{c}").status for c in cur]
    out.append(Check("curated_present", st == [200, 200], len(cur), str(st)))

    # 7. hero attēli
    heroes = hero_paths or []
    hs = [(h, fetch(f"{base}/{h}").status) for h in heroes]
    badh = [f"{h}→{s}" for h, s in hs if s != 200]
    out.append(Check("hero_images", bool(hs) and not badh, len(hs), "; ".join(badh[:5]) or "ok"))

    # 8. /.well-known/security.txt (RFC 9116). Denominators ir 1 apzināti:
    # viens fails, viena adrese — vairāk šeit nav ko apskatīt.
    sec_path = ".well-known/security.txt"
    rsec = fetch(f"{base}/{sec_path}")
    problems: list[str] = []
    if rsec.status != 200:
        problems.append(f"status {rsec.status}")
    else:
        body = rsec.body.decode("utf-8", "replace")
        if "Contact: mailto:" not in body:
            problems.append("trūkst `Contact: mailto:`")
        expires = _parse_expires(body)
        if expires is None:
            problems.append("trūkst derīga `Expires` (RFC 3339)")
        elif expires <= datetime.now(timezone.utc):
            problems.append(f"`Expires` pagājis: {expires:%Y-%m-%d}")
    out.append(Check("security_txt", not problems, 1,
                     ", ".join(problems) or f"{sec_path} 200, Contact + Expires derīgi"))

    # 9. KURŠ hosts atbildēja. Šī mašīna 2026-09-16 vakarā `atmina.lv` joprojām
    # rezolvēja uz veco Namecheap IP (162.213.255.90, `server: LiteSpeed`), kamēr
    # 1.1.1.1 jau deva Cloudflare — tātad visas pārējās 8 pārbaudes var iziet
    # zaļas PRET VECO HOSTU un deploy izskatās „dzīvs", kaut neviena jaunā lapa
    # nav pārbaudīta. Denominators 1 apzināti: viena atbilde, viena galvene.
    rroot = fetch(f"{base}/")
    server = rroot.headers.get("server", "")
    out.append(Check("served_by_cloudflare", server.lower() == "cloudflare", 1,
                     f"server: {server or '(nav galvenes)'}"
                     + ("" if server.lower() == "cloudflare"
                        else " — vecais hosts vai novecojis lokālais DNS; salīdzini "
                             "`nslookup atmina.lv 1.1.1.1` un pārbaudi ar `curl --resolve`")))
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", required=True)
    ap.add_argument("--sample", type=int, default=20)
    ap.add_argument("--sitemap", default="output/atmina/sitemap.xml")
    ap.add_argument("--heroes", type=int, default=10, help="cik pārskatu hero attēlu paraugā")
    a = ap.parse_args(argv)

    # Lapas saitē `-hero.webp` variantus (PNG masteri kokā nav) — pārbaudām tos.
    briefs = sorted(Path("output/atmina/images/briefs").glob("*-hero.webp"))
    hero_paths = [f"images/briefs/{p.name}" for p in briefs[-a.heroes:]]
    checks = run_checks(a.base, sitemap_urls(Path(a.sitemap)), http_fetch,
                        sample=a.sample, hero_paths=hero_paths)
    width = max(len(c.name) for c in checks)
    for c in checks:
        print(f"{'PASS' if c.passed else 'FAIL'}  {c.name:<{width}}  n={c.examined:<3}  {c.detail}")
    failed = [c for c in checks if not c.passed]
    print(f"{len(checks) - len(failed)}/{len(checks)} pārbaudes zaļas")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
