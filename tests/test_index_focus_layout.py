"""«Uzmanības centrā» apakšējās rindas izkārtojuma šablona līgums (2026-09-23).

Svaigā pretruna (.focus-slot-full) aizņem visu .focus-grid platumu; citāts un
spriedzes zem tās veido divkolonnu rindu, un vieninieks rindā dabū
.focus-slot-full. Pārbauda visus assemble_focus atļautos zarus:
slot_b ∈ {contradiction, tension, quote, None} × {citāts, spriedzes} ×
{konteksts ir/nav}.

Renderē ``index.html.j2`` tieši ar sintētisku ``focus`` (tāpat kā
tests/test_index_entry_points.py) — bez DB.
"""

from __future__ import annotations

import re

from jinja2 import Environment, FileSystemLoader

from src.render._common import _safe_json_filter, _safe_url_filter


def _env() -> Environment:
    env = Environment(loader=FileSystemLoader("templates"), autoescape=True)
    env.filters["safe_json"] = _safe_json_filter
    env.filters["safe_url"] = _safe_url_filter
    env.filters["lv_date"] = lambda s: s or ""
    env.filters["lv_plural"] = lambda n, *a, **k: ""
    env.filters["autolink_bills"] = lambda s, *a, **k: s
    env.filters["image_variant"] = lambda s, *a, **k: s
    env.globals["assets_version"] = "test"
    return env


CONTRA = {
    "id": 1, "severity": "reversal", "severity_lv": "Pozīcijas maiņa",
    "severity_glyph": "≈", "category_label": None,
    "politician_name": "Andris Bērziņš", "slug": "andris-berzins",
    "initials": "AB", "party_short": "AS", "party_color": "#112233",
    "has_photo": False, "topic": "Budžets", "delta_days": 0,
    "summary": "Kopsavilkuma teksts.",
    "context_note": "Konteksta teksts.",
    "old_label": None, "old_date": "2026-09-01",
    "old_source": "https://x.com/a/1", "old_source_domain": "x.com",
    "old_stance": "Vecā nostāja.", "old_quote": "Vecais citāts.",
    "new_label": None, "new_date": "2026-09-22",
    "new_source": "https://x.com/a/2", "new_source_domain": "x.com",
    "new_stance": "Jaunā nostāja.", "new_quote": "Jaunais citāts.",
    "vote_summary": None,
}

TENSION = {
    "type_lv": "Uzbrukums", "source_name": "Anna A", "source_slug": "anna-a",
    "target_name": "Jānis B", "target_slug": "janis-b",
    "description": "Apraksts.", "date": "2026-09-22", "topic": "Budžets",
    "source_url": "https://x.com/t/1", "target_url": "https://x.com/t/2",
    "created_at": "2026-09-22 10:00:00",
}

QUOTE = {
    "quote": "Dienas citāta teksts.", "mid_sentence": False,
    "name": "Anna A", "slug": "anna-a", "initials": "AA",
    "party_short": "AS", "party_color": "#112233", "has_photo": False,
    "topic": "Budžets", "topic_slug": "budzets",
    "date": "2026-09-22", "source_url": "https://x.com/q/1",
    "source_domain": "x.com",
}


def _render(focus: dict) -> str:
    return _env().get_template("index.html.j2").render(
        stats={},
        days_until_election=10,
        focus=focus,
        hero_items=[],
        rankings={},
        week_summary={},
        recent_votes=[],
        recent_briefs=[],
        trends_data={},
        BASE_URL="https://atmina.lv",
    )


def _grid(html: str) -> str:
    """Režģis līdz fokusa sekcijas beigām. Kartītē ir iekšējie
    <section class="prv2-*> (atkāpti), tāpēc griežam pie </section> kolonnā 0."""
    start = html.index('<div class="focus-grid">')
    end = html.index("\n</section>", start)
    return html[start:end]


def _slot_classes(grid_html: str) -> list[str]:
    """Visu .focus-slot bērnu class atribūti režģa secībā."""
    return re.findall(r'<div class="(focus-slot[^"]*)">', grid_html)


def _focus(slot_b=None, c_items=()):
    return {"hot": None, "slot_b": slot_b, "slot_c_items": list(c_items)}


# ── pretruna ──────────────────────────────────────────────────────────

def test_contra_full_width_then_quote_tensions_row():
    f = _focus({"kind": "contradiction", "item": CONTRA},
               [{"kind": "tension", "item": TENSION}, {"kind": "quote", "item": QUOTE}])
    grid = _grid(_render(f))
    classes = _slot_classes(grid)
    assert classes[0] == "focus-slot focus-slot-full"
    assert "focus-slot-lead" in classes[1] and "focus-slot-full" not in classes[1]
    assert classes[2] == "focus-slot"
    # pretrunas karte ir tikai pilnplatuma slotā; citāts ir atsevišķs slots
    assert grid.count("prv2-card") == 1
    assert "prv2-card" not in grid.split(classes[1])[1]


def test_contra_no_context_still_renders():
    c = {**CONTRA, "context_note": None, "summary": None, "old_quote": None}
    grid = _grid(_render(_focus({"kind": "contradiction", "item": c})))
    assert "prv2-card" in grid and "prv2-context" not in grid
    assert "prv2-summary" not in grid and "prv2-quote-fallback" in grid


def test_contra_no_quote_tensions_full_width():
    f = _focus({"kind": "contradiction", "item": CONTRA},
               [{"kind": "tension", "item": TENSION}])
    classes = _slot_classes(_grid(_render(f)))
    assert classes == ["focus-slot focus-slot-full", "focus-slot focus-slot-full"]


def test_contra_quote_no_tensions_lead_full_width():
    f = _focus({"kind": "contradiction", "item": CONTRA},
               [{"kind": "quote", "item": QUOTE}])
    classes = _slot_classes(_grid(_render(f)))
    assert classes[0] == "focus-slot focus-slot-full"
    assert "focus-slot-full" in classes[1]


# ── citi slot_b veidi ─────────────────────────────────────────────────

def test_tension_slot_b_stays_in_lead_citas_spriedzes():
    f = _focus({"kind": "tension", "item": TENSION},
               [{"kind": "tension", "item": TENSION}, {"kind": "quote", "item": QUOTE}])
    grid = _grid(_render(f))
    classes = _slot_classes(grid)
    assert "focus-slot-lead" in classes[0] and "focus-slot-full" not in classes[0]
    assert classes[1] == "focus-slot"
    assert "Citas spriedzes" in grid
    assert "focus-kicker-stacked" in grid  # citāts zem spriedzes — ar atdallīni


def test_quote_slot_b_in_lead():
    f = _focus({"kind": "quote", "item": QUOTE})
    grid = _grid(_render(f))
    classes = _slot_classes(grid)
    assert len(classes) == 1 and "focus-slot-lead" in classes[0]
    assert "focus-slot-full" in classes[0]  # vieninieks → viss platums
    assert "Dienas citāts" in grid and "prv2-card" not in grid


def test_no_slot_b_only_quote_and_tensions():
    f = _focus(None, [{"kind": "tension", "item": TENSION},
                      {"kind": "quote", "item": QUOTE}])
    classes = _slot_classes(_grid(_render(f)))
    assert len(classes) == 2
    assert "focus-slot-full" not in classes[0] + classes[1]


def test_only_tensions_full_width():
    f = _focus(None, [{"kind": "tension", "item": TENSION}])
    classes = _slot_classes(_grid(_render(f)))
    assert classes == ["focus-slot focus-slot-full"]
