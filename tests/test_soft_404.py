"""Tests for src/soft_404.py — the soft-404 fetch guard.

Why (backlog/avoti.md): the truncated-document backfill campaign re-fetches
stored web articles and updates them in place. A source that answers a dead
article URL with HTTP 200 + an unrelated page lets trafilatura extract that
page and OVERWRITE the real stored text — the guard flags such pages so
callers treat them like fetch errors.

Live probe, 2026-09-23 (httpx, project HEADERS, ~1s pacing):
  - www.lsm.lv  — SOFT-404: a nonexistent article id (`.a9999999`) 301s to
    https://www.lsm.lv/ i.e. the HOMEPAGE. Status 200, <title> is the portal
    tagline, no og:title, trafilatura extracts ~13k chars of headline
    listings. (Existent ids 301 to the article's canonical URL instead —
    the `.aNNNNNN` id is the key, slug/date are ignored.)
  - www.diena.lv — real 404 status (body "Lapa nav atrasta"); real article
    also showed a benign www.diena.lv → diena.lv apex redirect (path kept).
  - tvnet.lv    — real 404 status.
  - nra.lv      — real 404 status (<title>"Lapa nav atrasta (404) - nra.lv").
  - www.delfi.lv — real 404 status (107-char "nepareizu lapas adresi" body).

So ONLY lsm.lv serves a soft-404; the other four are caught upstream by
raise_for_status() and the guard deliberately carries no signal for them —
their *_fake fixtures below must return None.

Fixtures in tests/fixtures/soft404/ are trimmed copies (head + title/meta
verbatim, body reduced to the trafilatura output head as a comment).
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.db import get_db, init_db  # noqa: E402
from src.soft_404 import looks_like_soft_404  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "soft404"


def _fx(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


# (requested_url, final_url) pairs as observed on the wire 2026-09-23.
LSM_DEAD = ("https://www.lsm.lv/raksts/zinas/latvija/"
            "01.01.2020-neeksistejoss-raksts-soft404-tests.a9999999/")
LSM_ROOT = "https://www.lsm.lv/"
LSM_REAL = ("https://www.lsm.lv/raksts/zinas/latvija/"
            "22.03.2024-zurnalistu-asociaciju-turpmak-vadis-delfi-galvenais-redaktors-lastovskis"
            ".a547778/")
DIENA_DEAD = ("https://www.diena.lv/raksts/latvija/politika/"
              "neeksistejoss-raksts-soft404-tests-12345678")
DIENA_DEAD_FINAL = ("https://diena.lv/raksts/latvija/politika/"
                    "neeksistejoss-raksts-soft404-tests-12345678")
DIENA_REAL = ("https://www.diena.lv/raksts/latvija/politika/"
              "ari-kozlovskis-iztur-uzticibas-balsojumu-saeima")
DIENA_REAL_FINAL = ("https://diena.lv/raksts/latvija/politika/"
                    "ari-kozlovskis-iztur-uzticibas-balsojumu-saeima")
TVNET_DEAD = "https://www.tvnet.lv/99999999/neeksistejoss-raksts-soft404-tests"
TVNET_REAL = ("https://www.tvnet.lv/8146843/"
              "darbu-sak-tvnet-galvena-redaktore-erika-staskevica")
NRA_DEAD = "https://nra.lv/latvija/999999-neeksistejoss-raksts-soft404-tests.htm"
NRA_REAL = ("https://nra.lv/latvija/400845-par-mediju-nama-ipasnieci-klust-"
            "uznemeja-anastasija-udalova.htm")
DELFI_DEAD = ("https://www.delfi.lv/193/politics/999999999/"
              "neeksistejoss-raksts-soft404-tests")
DELFI_REAL = ("https://www.delfi.lv/193/politics/120111362/amatpersonas-jau-pec-"
              "gada-drikstes-stradat-uznemumos-par-kuru-ieprieks-lemusas")


class TestLooksLikeSoft404:
    def test_lsm_dead_article_redirected_to_root_is_flagged(self):
        """The observed soft-404: nonexistent .a id 301s to the homepage."""
        reason = looks_like_soft_404(_fx("lsm_fake.html"), None, LSM_DEAD, LSM_ROOT)
        assert reason is not None
        assert "root" in reason

    def test_lsm_homepage_shell_flagged_without_final_url(self):
        """If redirect info isn't threaded through, the portal tagline <title>
        on a /raksts/ URL still catches it (same observed page)."""
        reason = looks_like_soft_404(_fx("lsm_fake.html"), None, LSM_DEAD)
        assert reason is not None
        assert "lsm.lv" in reason

    @pytest.mark.parametrize("fixture,url,final", [
        ("lsm_real.html", LSM_REAL, LSM_REAL),
        ("diena_real.html", DIENA_REAL, DIENA_REAL_FINAL),
        ("tvnet_real.html", TVNET_REAL, TVNET_REAL),
        ("nra_real.html", NRA_REAL, NRA_REAL),
        ("delfi_real.html", DELFI_REAL, DELFI_REAL),
    ])
    def test_real_articles_are_not_flagged(self, fixture, url, final):
        assert looks_like_soft_404(_fx(fixture), None, url, final) is None

    @pytest.mark.parametrize("fixture,url,final", [
        # All four returned real 404 status on 2026-09-23 — raise_for_status()
        # drops them before any extraction, so the guard invents no signal.
        ("diena_fake.html", DIENA_DEAD, DIENA_DEAD_FINAL),
        ("tvnet_fake.html", TVNET_DEAD, TVNET_DEAD),
        ("nra_fake.html", NRA_DEAD, NRA_DEAD),
        ("delfi_fake.html", DELFI_DEAD, DELFI_DEAD),
    ])
    def test_hard_404_bodies_are_not_flagged(self, fixture, url, final):
        assert looks_like_soft_404(_fx(fixture), None, url, final) is None

    def test_slug_canonicalization_redirect_is_not_flagged(self):
        """LSM keys articles on the .aNNNNNN id: a mangled slug on an EXISTING
        id 301s to the real article's canonical URL (deep path kept)."""
        canonical = ("https://www.lsm.lv/raksts/zinas/ekonomika/"
                     "27.05.2024-latvija-sanem-otro-es-atveselosanas-fonda-maksajumu"
                     "-336-miljonu-eiro-apmera.a555555/")
        mangled = "https://www.lsm.lv/raksts/zinas/latvija/01.01.2020-cits.a555555/"
        assert looks_like_soft_404(_fx("lsm_real.html"), None, mangled, canonical) is None

    def test_homepage_fetched_as_homepage_is_not_flagged(self):
        """A root URL staying at root is a homepage fetch, not a soft-404."""
        assert looks_like_soft_404(_fx("lsm_fake.html"), None, LSM_ROOT, LSM_ROOT) is None

    def test_no_redirect_info_no_signal(self):
        assert looks_like_soft_404("<html><title>x</title></html>", None, LSM_REAL) is None


# --- fake transports ----------------------------------------------------------

# The trimmed fixture's <body> is only a comment, so trafilatura yields
# nothing and a soft-404 would "fail thin" without the guard — proving
# nothing. For call-site tests we keep the real <title>/head but inject a
# body long enough to become stored content if the guard does NOT fire.
# trafilatura's deduplicate=True dedupes ACROSS calls in one process, so each
# call-site test gets a distinct body via `tag`.
def _lsm_soft_html(tag: str) -> str:
    body = " ".join(
        f"Saeimas deputāti {tag} apsprieda jautājumu numur {i}." for i in range(80)
    )
    return _fx("lsm_fake.html").replace("</body>", f"<p>{body}</p></body>")


class _Resp:
    """Minimal httpx.Response stand-in (sync + async paths)."""

    def __init__(self, text: str, url: str, status: int = 200):
        self.text = text
        self.url = url  # httpx exposes resp.url as URL; str(resp.url) == this
        self.status_code = status
        self.headers: dict[str, str] = {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class _FakeAsyncClient:
    """Routes a fixed {url: _Resp} map; unknown URLs get an empty 200."""

    def __init__(self, routes, *args, **kwargs):
        self._routes = routes

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get(self, url, headers=None):
        return self._routes.get(str(url)) or _Resp("", str(url))


class _FakeSyncClient:
    def __init__(self, routes, *args, **kwargs):
        self._routes = routes

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def get(self, url):
        return self._routes.get(str(url)) or _Resp("", str(url))


# --- call-site wiring ----------------------------------------------------------


@pytest.fixture
def tmp_db(tmp_path) -> str:
    db_path = str(tmp_path / "t.db")
    init_db(db_path=db_path)
    return db_path


def test_default_fetch_soft404_returns_none(monkeypatch):
    """ingest_url._default_fetch must treat a soft-404 like a fetch error."""
    import httpx
    import scripts.ingest_url as iu

    monkeypatch.setattr(
        httpx, "Client",
        lambda *a, **k: _FakeSyncClient({LSM_DEAD: _Resp(_lsm_soft_html("fetch"), LSM_ROOT)}),
    )
    assert iu._default_fetch(LSM_DEAD) is None


def test_ingest_one_soft404_never_reaches_insert_document(tmp_db, monkeypatch):
    """End-to-end: soft-404 -> status fetch_error, no documents row."""
    import httpx
    import scripts.ingest_url as iu

    monkeypatch.setattr(
        httpx, "Client",
        lambda *a, **k: _FakeSyncClient({LSM_DEAD: _Resp(_lsm_soft_html("ingest"), LSM_ROOT)}),
    )
    res = iu.ingest_one(LSM_DEAD, db_path=tmp_db)
    assert res["status"] == "fetch_error"
    db = get_db(tmp_db)
    n = db.execute("SELECT COUNT(*) AS c FROM documents").fetchone()["c"]
    db.close()
    assert n == 0


def test_fetch_page_returns_none_on_soft404():
    import src.ingest as ing

    client = _FakeAsyncClient({LSM_DEAD: _Resp(_lsm_soft_html("page"), LSM_ROOT)})
    assert asyncio.run(ing._fetch_page(client, LSM_DEAD, article=True)) is None


def test_fetch_page_entry_page_redirect_to_root_is_not_guarded():
    """Sargs ir TIKAI raksta fetcham. Sadaļas/ieejas lapa, kas pārvirza uz "/",
    joprojām ir derīgs saišu avots — ja to bloķētu, avota ingests klusi
    iztukšotos (2026-09-23 orķestratora recenzija)."""
    import src.ingest as ing

    entry = "https://www.lsm.lv/zinas/latvija/"
    html = _lsm_soft_html("entry")
    client = _FakeAsyncClient({entry: _Resp(html, LSM_ROOT)})
    assert asyncio.run(ing._fetch_page(client, entry)) == html


def test_enrich_rss_soft404_falls_back_to_lede(monkeypatch):
    """A soft-404 must keep the RSS lede with truncated=True — never replace
    it with the error page's text."""
    import httpx
    import src.ingest as ing

    routes = {LSM_DEAD: _Resp(_lsm_soft_html("rss"), LSM_ROOT)}
    monkeypatch.setattr(httpx, "AsyncClient", lambda *a, **k: _FakeAsyncClient(routes))

    async def _no_sleep(*a, **k):
        return None

    monkeypatch.setattr(ing.asyncio, "sleep", _no_sleep)

    lede = "Saeima šodien pieņēma budžetu."
    items = [{"text": lede, "url": LSM_DEAD, "published_at": None}]
    out = asyncio.run(
        ing._enrich_rss_items_fulltext(items, "https://www.lsm.lv/rss/?lang=lv&catid=20")
    )
    assert out[0]["text"] == lede
    assert out[0]["truncated"] is True


def test_scrape_web_articles_soft404_article_skipped(monkeypatch):
    """The httpx scrape path must not emit a soft-404 page as an article."""
    import httpx
    import src.ingest as ing

    entry = (
        '<html><body><a href="/raksts/zinas/latvija/x.a9999999/">x</a></body></html>'
    )
    article_url = "https://www.lsm.lv/raksts/zinas/latvija/x.a9999999"
    routes = {
        LSM_ROOT: _Resp(entry, LSM_ROOT),
        article_url: _Resp(_lsm_soft_html("scrape"), LSM_ROOT),
    }
    monkeypatch.setattr(httpx, "AsyncClient", lambda *a, **k: _FakeAsyncClient(routes))

    async def _no_sleep(*a, **k):
        return None

    monkeypatch.setattr(ing.asyncio, "sleep", _no_sleep)

    out = asyncio.run(ing._scrape_web_articles(LSM_ROOT))
    assert out is None, "soft-404 article must be skipped; no items -> None"
