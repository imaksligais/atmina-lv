"""RSS plūsma (feed.xml): lasītājs ar RSS lasītāju redz jaunākos pārskatus un analīzes.

Kļūme, ko tests ķer: plūsma netiek uzrakstīta, nav derīgs XML, rāda uz lapu,
kuras kokā nav (piem. nepublicēts pārskats), vai nav atrodama no lapas galvenes.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

from src.render._common.constants import BASE_URL
from src.render.feed import FEED_LIMIT


def test_feed_lists_published_pages_newest_first(rendered_site):
    feed = rendered_site / "feed.xml"
    assert feed.exists(), "feed.xml nav uzrakstīts"

    channel = ET.fromstring(feed.read_bytes()).find("channel")
    assert channel is not None
    self_link = channel.find("{http://www.w3.org/2005/Atom}link")
    assert self_link is not None and self_link.get("href") == f"{BASE_URL}/feed.xml", "nav atom:link rel=self"
    items = channel.findall("item")
    assert 2 <= len(items) <= FEED_LIMIT, f"ierakstu skaits: {len(items)}"

    stamps = []
    for item in items:
        link = item.findtext("link")
        assert link.startswith(BASE_URL + "/"), link
        page = rendered_site / link[len(BASE_URL) + 1:]
        assert page.exists(), f"plūsma rāda uz neesošu lapu: {link}"
        assert item.findtext("guid") == link
        assert item.findtext("title").strip()
        stamps.append(parsedate_to_datetime(item.findtext("pubDate")))
    assert stamps == sorted(stamps, reverse=True), "ieraksti nav no jaunākā uz vecāko"

    kinds = {item.findtext("link").split("/")[3] for item in items}
    assert {"blog", "analizes"} <= kinds, f"plūsmā trūkst veida: {kinds}"

    head = (rendered_site / "blog.html").read_text(encoding="utf-8").split("</head>")[0]
    assert f'type="application/rss+xml" title="atmina.lv" href="{BASE_URL}/feed.xml"' in head
