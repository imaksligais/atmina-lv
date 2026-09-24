"""Tests for src.graphics.visual_map — topic-to-metaphor library."""
from src.graphics import visual_map
from src.topic_map import get_all_group_names


def test_visual_map_covers_all_canonical_topics():
    """Verify VISUAL_MAP includes all canonical topics (currently 31)."""
    canonical = set(get_all_group_names())
    mapped = set(visual_map.VISUAL_MAP.keys())
    missing = canonical - mapped
    assert not missing, f"visual_map missing topics: {missing}"


def test_get_visual_returns_metaphor_mood_accent_for_known_topic():
    """Verify get_visual() returns a dict with required keys for a known topic."""
    result = visual_map.get_visual("Budžets un finanses")
    assert "metaphor" in result and result["metaphor"]
    assert "mood" in result and result["mood"]
    assert "accent" in result and result["accent"]


def test_get_visual_returns_default_for_unknown_topic():
    """Verify get_visual() returns _DEFAULT for unknown topics."""
    result = visual_map.get_visual("nonexistent-topic-xyz")
    assert result == visual_map._DEFAULT


def test_every_entry_has_required_keys():
    """Verify all VISUAL_MAP entries have metaphor, mood, and accent."""
    for topic, entry in visual_map.VISUAL_MAP.items():
        assert set(entry.keys()) >= {"metaphor", "mood", "accent"}, \
            f"Entry '{topic}' missing keys: {entry}"


def test_default_has_required_keys():
    """Verify _DEFAULT has all required keys."""
    assert set(visual_map._DEFAULT.keys()) >= {"metaphor", "mood", "accent"}
