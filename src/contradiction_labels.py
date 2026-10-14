"""The ONE vocabulary for contradiction types (operator decision 2026-09-28).

Before this module the same ``contradictions.severity`` had three names across
the site: ``reversal`` was «Apvērsums» (render, graph, pretrunas chips — and
reads as "coup") and «reversija» (daily/weekly brief — a calque);
``minor_shift`` was «Pozīcijas maiņa», «neliela novirze» and «Nobīde»; and
«Pozīcijas maiņa» ALSO named the ``position_position`` category.

A leaf module (no project imports) so ``src.briefs``, ``src.render`` and
``src.social_agent`` can all import it without a cycle. ``assets/sav1.js``
carries the severity strings as literals; ``tests/test_contradiction_labels.py``
fails if they drift.

Stored, already-published brief text keeps its old wording — this changes what
is rendered from here on, not history.
"""

from __future__ import annotations

# contradictions.severity → sentence-case label (badges, chips, cards).
SEVERITY_LV: dict[str, str] = {
    "direct_contradiction": "Tieša pretruna",
    "reversal": "Nostājas maiņa",
    "minor_shift": "Neliela novirze",
}

# Category from the claim_type pair (sorted types joined by "_"). Drives the
# main badge on OG cards, the pretrunas list, detail pages, politician pages.
CATEGORY_LV: dict[str, str] = {
    "position_position": "Retorikas maiņa",
    "position_saeima_vote": "Vārdi pret darbiem",
    "saeima_vote_saeima_vote": "Balsojuma maiņa",
}


def lower_first(label: str) -> str:
    """Mid-sentence / mid-table form: «Nostājas maiņa» → «nostājas maiņa»."""
    return label[:1].lower() + label[1:]
