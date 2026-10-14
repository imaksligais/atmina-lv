"""Pārskata virsraksts nāk no PAŠREIZĒJĀ satura, ne no denormalizētā JSON.

`context_notes.visual_brief_json` aizpildās TIKAI rakstīšanas brīdī
(`src/tools.py` → `src.briefs.parse_visual_brief`). Vēlāks `content` labojums
tā `## Vizuālais brief` blokā līdz šim nesasniedza `og:title`, `twitter:title`,
H1 un abus `alt` tekstus — uzvarēja noglabātais (novecojušais) virsraksts.
Atsauces incidents: pārskats #505, 2026-08-26.

Precedence render-laikā:
  parse_visual_brief(content)['headline']
  → json.loads(visual_brief_json)['headline']
  → no virsraksta atvasinātais fallback (datuma nogriešanas regex).
Tukšs/None jebkurā līmenī krīt uz nākamo.
"""

from __future__ import annotations

import os
import sqlite3
import tempfile

from jinja2 import Environment, FileSystemLoader

from src.image_variants import variant_filename as _brief_image_variant
from src.render._common import _lv_plural

_SCHEMA = """
CREATE TABLE documents (id INTEGER PRIMARY KEY, scraped_at TEXT, platform TEXT, source_domain TEXT);
CREATE TABLE tracked_politicians (id INTEGER PRIMARY KEY, name TEXT, party TEXT, relationship_type TEXT);
CREATE TABLE claims (id INTEGER PRIMARY KEY, opponent_id INTEGER, document_id INTEGER, topic TEXT,
                     stance TEXT, source_url TEXT, stated_at TEXT,
                     claim_type TEXT NOT NULL DEFAULT 'position');
CREATE TABLE contradictions (id INTEGER PRIMARY KEY, opponent_id INTEGER, detected_at TEXT, confirmed INTEGER);
CREATE TABLE saeima_votes (id INTEGER PRIMARY KEY, motif TEXT, vote_date TEXT);
CREATE TABLE brief_images (id INTEGER PRIMARY KEY, note_id INTEGER, image_path TEXT, approved INTEGER);
CREATE TABLE context_notes (id INTEGER PRIMARY KEY, opponent_id INTEGER, topic TEXT, note_type TEXT,
                            content TEXT, source TEXT, created_at TEXT, expires_at TEXT,
                            visual_brief_json TEXT);
"""

_BODY = (
    "# Dienas analīze — 2026-08-26\n"
    "\n"
    "## Galvenais\n"
    "\n"
    "Koalīcija vienojās par budžeta grozījumiem.\n"
)

_VB_BLOCK = (
    "\n"
    "## Vizuālais brief\n"
    "\n"
    "- **Tēma:** budžets\n"
    "- **Galvenā tēze:** {headline}\n"
    "- **Skaitlis:** nav\n"
    "- **Metaforas hint:** tukšs krēsls\n"
)

_BROKEN_VB_BLOCK = (
    "\n"
    "## Vizuālais brief\n"
    "\n"
    "Tēma: budžets; galvenā tēze: bez bullet formas\n"
)


def _post(content: str, visual_brief_json: str | None, *, with_image: bool = True) -> dict:
    """Izveido pagaidu DB ar vienu dienas pārskatu un atgriež tā post dict."""
    from src.render.blog import _fetch_blog_posts

    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        db = sqlite3.connect(path)
        db.executescript(_SCHEMA)
        db.execute(
            "INSERT INTO context_notes (id, topic, note_type, content, created_at, "
            "visual_brief_json) VALUES (?, ?, ?, ?, ?, ?)",
            (
                505,
                "dienas analīze 2026-08-26",
                "daily_brief",
                content,
                "2026-08-26 22:10:00",
                visual_brief_json,
            ),
        )
        if with_image:
            db.execute(
                "INSERT INTO brief_images (note_id, image_path, approved) VALUES (?, ?, 1)",
                (505, "images/briefs/brief_2026-08-26.png"),
            )
        db.commit()
        db.close()

        db = sqlite3.connect(path)
        db.row_factory = sqlite3.Row
        posts = _fetch_blog_posts(db)
        db.close()
    finally:
        os.unlink(path)

    assert len(posts) == 1
    return posts[0]


def _render(post: dict) -> str:
    env = Environment(loader=FileSystemLoader("templates"), autoescape=True)
    env.filters["image_variant"] = _brief_image_variant
    env.filters["lv_plural"] = _lv_plural
    env.globals["assets_version"] = "test"
    return env.get_template("blog-post.html.j2").render(
        post=post,
        content_html="<p>Saturs.</p>",
        toc=None,
        prev_post=None,
        next_post=None,
        latest_analysis=None,
        BASE_URL="https://atmina.lv",
    )


def test_corrected_content_headline_beats_stored_visual_brief_json():
    """Satura bloka virsraksts uzvar noglabāto JSON — visās četrās virsmās."""
    post = _post(
        _BODY + _VB_BLOCK.format(headline="Koalīcija atkāpjas no budžeta griezuma"),
        '{"headline": "Koalīcija griež budžetu", "topic": "budžets"}',
    )

    assert post["headline"] == "Koalīcija atkāpjas no budžeta griezuma"
    assert post["display_title"] == "Koalīcija atkāpjas no budžeta griezuma"

    html = _render(post)
    assert html.count("Koalīcija atkāpjas no budžeta griezuma") >= 4  # og, twitter, H1, alt
    assert "Koalīcija griež budžetu" not in html
    assert (
        '<meta property="og:title" content="Koalīcija atkāpjas no budžeta griezuma">'
        in html
    )
    assert (
        '<meta name="twitter:title" content="Koalīcija atkāpjas no budžeta griezuma">'
        in html
    )
    assert (
        '<h1 class="brief-pagehead-title">Koalīcija atkāpjas no budžeta griezuma</h1>'
        in html
    )
    assert 'alt="Koalīcija atkāpjas no budžeta griezuma"' in html


def test_missing_content_block_falls_back_to_stored_headline():
    """Bez `## Vizuālais brief` bloka paliek noglabātais JSON virsraksts."""
    post = _post(_BODY, '{"headline": "Noglabātais virsraksts"}')

    assert post["headline"] == "Noglabātais virsraksts"
    assert post["display_title"] == "Noglabātais virsraksts"
    assert 'alt="Noglabātais virsraksts"' in _render(post)


def test_unparseable_content_block_falls_back_to_stored_headline():
    """Nesaparsējams bloks (13 no 161 pārskatiem) renderējas tieši kā līdz šim."""
    post = _post(_BODY + _BROKEN_VB_BLOCK, '{"headline": "Noglabātais virsraksts"}')

    assert post["headline"] == "Noglabātais virsraksts"
    assert post["display_title"] == "Noglabātais virsraksts"


def test_no_content_block_and_no_stored_json_uses_title_fallback():
    """Bez abiem avotiem paliek no virsraksta atvasinātais fallback."""
    post = _post(_BODY, None)

    assert post["headline"] is None
    assert post["display_title"] == "Dienas analīze"


def test_empty_stored_headline_falls_through_to_title_fallback():
    """Tukšs/None noglabātais virsraksts nav derīgs — krīt uz nākamo līmeni."""
    for stored in ('{"headline": null}', '{"headline": "   "}', "{}", "nav JSON"):
        post = _post(_BODY, stored)
        assert post["headline"] is None, stored
        assert post["display_title"] == "Dienas analīze", stored


def test_placeholder_template_block_does_not_override_stored_headline():
    """`<tēma>` stila paraugbloks nav īsts brief — noglabātais paliek spēkā."""
    placeholder = (
        "\n"
        "## Vizuālais brief\n"
        "\n"
        "- **Tēma:** <tēma>\n"
        "- **Galvenā tēze:** <galvenā tēze>\n"
        "- **Skaitlis:** <skaitlis>\n"
        "- **Metaforas hint:** <hint>\n"
    )
    post = _post(_BODY + placeholder, '{"headline": "Noglabātais virsraksts"}')

    assert post["headline"] == "Noglabātais virsraksts"
