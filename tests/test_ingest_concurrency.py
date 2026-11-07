"""Which sources may be scraped at the same time during `ingest_all`.

Failure this names: a slow site holds up every other site (tier 2 used to run
one source after another), or the speed-up breaks one of the three limits below.
"""
from __future__ import annotations

import asyncio

import src.ingest as ingest


def _source(url: str, tier: int = 2, mode: str = "web_scraper") -> dict:
    return {"url": url, "name": url, "tier": tier, "fetcher_mode": mode,
            "rate_limit_seconds": 0}


def test_ingest_all_scrapes_concurrently_within_the_limits(monkeypatch):
    feed = "https://feed.lv/rss"
    site_a = "https://a.lv/"
    site_a_section = "https://a.lv/viedokli/"
    site_b = "https://b.lv/"
    browser_c = "https://c.lv/"
    browser_d = "https://d.lv/"
    sources = [
        _source(feed, tier=1, mode="fetcher"),
        _source(site_a), _source(site_a_section), _source(site_b),
        _source(browser_c, mode="fetcher"), _source(browser_d, mode="fetcher"),
    ]
    events: list[tuple[str, str]] = []

    async def fake_scrape(url, _tier, _mode):
        events.append(("start", url))
        await asyncio.sleep(0.05)
        events.append(("end", url))
        return []

    monkeypatch.setattr(ingest, "init_db", lambda: None)  # a dry run writes nothing
    monkeypatch.setattr(ingest, "_load_sources", lambda: sources)
    monkeypatch.setattr(ingest, "scrape_source", fake_scrape)

    results = ingest.ingest_all(dry_run=True)

    def overlap(one: str, other: str) -> bool:
        return (events.index(("start", one)) < events.index(("end", other))
                and events.index(("start", other)) < events.index(("end", one)))

    assert overlap(site_a, site_b), "different sites must not wait for each other"
    assert not overlap(site_a, site_a_section), "one site gets one source at a time"
    # insert_document keeps the first copy of identical text: tier 1 keeps priority.
    tier2_starts = [events.index(("start", s["url"])) for s in sources[1:]]
    assert events.index(("end", feed)) < min(tier2_starts)
    # Each browser source starts its own Chromium.
    assert not overlap(browser_c, browser_d)
    assert not any(overlap(browser_c, s) for s in (site_a, site_a_section, site_b))
    # The batch summary lists sources in configured order.
    assert [r["url"] for r in results] == [s["url"] for s in sources]
