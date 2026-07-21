from src.social_agent.drafters import draft_pretrunas


SAMPLE_CONTRADICTION = {
    "contradiction_id": 100,
    "politician_name": "Arturs Kariņš",
    "topic": "budžets",
    "old_quote": "Nekad neatbalstīšu nodokļu celšanu",
    "old_stance": "Iebilst pret nodokļu celšanu",
    "old_stated_at": "2026-03-01",
    "old_claim_type": "position",
    "new_quote": "Šis budžets ir vienīgais iespējamais risinājums",
    "new_stance": "Budžets ir vienīgais iespējamais risinājums",
    "new_stated_at": "2026-04-15",
    "new_claim_type": "position",
    "slug": "arturs-karins",
}


def test_draft_pretrunas_contains_required_elements():
    text = draft_pretrunas(SAMPLE_CONTRADICTION)
    assert "Arturs Kariņš" in text
    assert "budžets" in text
    assert "Nekad neatbalstīšu" in text
    assert "vienīgais iespējamais" in text
    assert "2026-03-01" in text
    assert "2026-04-15" in text
    assert "atmina.lv/pretrunas/100.html" in text


def test_draft_pretrunas_mixed_shows_vardi_vs_darbi():
    mixed = {
        **SAMPLE_CONTRADICTION,
        "new_claim_type": "saeima_vote",
    }
    text = draft_pretrunas(mixed)
    assert "vārdi vs. darbi" in text.lower()


def test_draft_pretrunas_same_type_shows_pozicijas_maina():
    text = draft_pretrunas(SAMPLE_CONTRADICTION)
    assert "pozīcijas maiņa" in text.lower()


def test_draft_pretrunas_max_280_chars():
    long = {
        **SAMPLE_CONTRADICTION,
        "old_quote": "A" * 200,
        "new_quote": "B" * 200,
    }
    text = draft_pretrunas(long)
    assert len(text) <= 280, f"draft too long: {len(text)} chars"
    # Truncated quotes must end with ellipsis
    assert "…" in text


def test_draft_pretrunas_raises_on_missing_fields():
    import pytest
    with pytest.raises(KeyError):
        draft_pretrunas({"contradiction_id": 1})


from src.social_agent.drafters import draft_stats


SAMPLE_STATS = {
    "iso_week": "2026-W16",
    "leaderboard": [
        {"politician_id": 1, "name": "Arturs Kariņš", "party": "JV", "count": 12},
        {"politician_id": 2, "name": "Edgars Rinkēvičs", "party": "JV", "count": 9},
        {"politician_id": 3, "name": "Juris Rancāns", "party": "JV", "count": 7},
    ],
}


def test_draft_stats_lists_top_three_names():
    text = draft_stats(SAMPLE_STATS)
    assert "Arturs Kariņš" in text
    assert "Edgars Rinkēvičs" in text
    assert "Juris Rancāns" in text
    assert "12" in text
    assert "atmina.lv/statistika" in text
    assert len(text) <= 280


def test_draft_stats_handles_short_leaderboard():
    result = draft_stats({
        "iso_week": "2026-W16",
        "leaderboard": [{"politician_id": 1, "name": "Alone", "party": "X", "count": 3}],
    })
    assert "Alone" in result
    assert len(result) <= 280


from src.social_agent.drafters import draft_highlight


def test_draft_highlight_attack():
    row = {
        "kind": "attack",
        "politician_name": "Arturs Kariņš",
        "text": "Kariņš pēdējā gada laikā ir mainījis viedokli par nodokļiem trīs reizes.",
        "slug": "arturs-karins",
    }
    text = draft_highlight(row)
    assert "Kariņš" in text
    assert "atmina.lv/" in text
    assert len(text) <= 280


def test_draft_highlight_tension():
    row = {
        "kind": "tension",
        "source_name": "A",
        "target_name": "B",
        "topic": "drošība",
        "description": "A publiski pārmet B par drošības dienestu reformu.",
        "tension_type": "uzbrukums",
    }
    text = draft_highlight(row)
    assert "A" in text
    assert "B" in text
    assert "drošība" in text
    assert "atmina.lv/" in text
    assert len(text) <= 280


def test_draft_highlight_unknown_kind_raises():
    import pytest
    with pytest.raises(ValueError):
        draft_highlight({"kind": "unknown"})
