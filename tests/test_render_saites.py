"""Tests for _fetch_saites_for_profile per-card anchor annotation.

Spec: docs/superpowers/specs/2026-05-02-saites-tab-click-focus-design.md
"""

import sqlite3
import pytest

from src.render.politicians import _fetch_saites_for_profile


@pytest.fixture
def empty_db():
    """In-memory DB with row_factory — _fetch_saites_for_profile uses _vote_alignment_for
    only for profile_kind='deputy', so non-deputy profiles need no schema."""
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    return db


def _make_tension(
    source_pid,
    target_pid,
    tension_type,
    source_name="A",
    target_name="B",
    source_party="JV",
    target_party="NA",
    topic="Drošība",
    description="...",
    created_at="2026-04-30",
):
    return {
        "source_pid": source_pid,
        "target_pid": target_pid,
        "tension_type": tension_type,
        "source_name": source_name,
        "target_name": target_name,
        "source_party": source_party,
        "target_party": target_party,
        "topic": topic,
        "description": description,
        "created_at": created_at,
    }


def test_first_card_for_pair_is_anchor(empty_db):
    """Single tension → its card is the anchor."""
    tensions = [_make_tension(1, 2, "uzbrukums")]
    out = _fetch_saites_for_profile(
        empty_db, pid=1, profile_kind="politician", tensions=tensions, commentary_about=[]
    )
    assert out["uzbrukumi"][0]["is_anchor"] is True
    assert out["uzbrukumi"][0]["other_pid"] == 2
    assert out["uzbrukumi"][0]["other_slug"] == "b"


def test_second_card_same_pair_is_not_anchor(empty_db):
    """Same pair appears in uzbrukumi AND spriedzes — only uzbrukumi gets is_anchor."""
    tensions = [
        _make_tension(1, 2, "uzbrukums"),
        _make_tension(1, 2, "spriedze"),
    ]
    out = _fetch_saites_for_profile(
        empty_db, pid=1, profile_kind="politician", tensions=tensions, commentary_about=[]
    )
    assert out["uzbrukumi"][0]["is_anchor"] is True
    assert out["spriedzes"][0]["is_anchor"] is False
    assert out["spriedzes"][0]["other_pid"] == 2  # still annotated, just not anchor


def test_atbalsts_only_pair_is_anchor(empty_db):
    """Same pair in atbalsts only → atbalsts card is anchor."""
    tensions = [_make_tension(1, 2, "atbalsts")]
    out = _fetch_saites_for_profile(
        empty_db, pid=1, profile_kind="politician", tensions=tensions, commentary_about=[]
    )
    assert out["atbalsts"][0]["is_anchor"] is True


def test_other_pid_when_current_is_target(empty_db):
    """When the current politician is target_pid, other_pid is source_pid."""
    tensions = [_make_tension(2, 1, "uzbrukums", source_name="X", target_name="Y")]
    out = _fetch_saites_for_profile(
        empty_db, pid=1, profile_kind="politician", tensions=tensions, commentary_about=[]
    )
    assert out["uzbrukumi"][0]["other_pid"] == 2
    assert out["uzbrukumi"][0]["other_slug"] == "x"


def test_two_distinct_pairs_both_anchors(empty_db):
    """Different other_pids → both cards anchored."""
    tensions = [
        _make_tension(1, 2, "uzbrukums"),
        _make_tension(1, 3, "uzbrukums", target_name="C"),
    ]
    out = _fetch_saites_for_profile(
        empty_db, pid=1, profile_kind="politician", tensions=tensions, commentary_about=[]
    )
    assert out["uzbrukumi"][0]["is_anchor"] is True
    assert out["uzbrukumi"][1]["is_anchor"] is True
    assert out["uzbrukumi"][0]["other_pid"] == 2
    assert out["uzbrukumi"][1]["other_pid"] == 3


def test_empty_tensions_no_annotation_keys_in_empty_lists(empty_db):
    """No tensions → uzbrukumi/spriedzes/atbalsts are empty lists. No crash."""
    out = _fetch_saites_for_profile(
        empty_db, pid=1, profile_kind="politician", tensions=[], commentary_about=[]
    )
    assert out["uzbrukumi"] == []
    assert out["spriedzes"] == []
    assert out["atbalsts"] == []


def test_diacritic_name_slugified(empty_db):
    """Latvian diacritics in target name → slug stripped."""
    tensions = [_make_tension(1, 2, "uzbrukums", target_name="Āris Šķērslis")]
    out = _fetch_saites_for_profile(
        empty_db, pid=1, profile_kind="politician", tensions=tensions, commentary_about=[]
    )
    assert out["uzbrukumi"][0]["other_slug"] == "aris-skerslis"


def test_anchor_walks_full_three_sections(empty_db):
    """Same pair appears in all three sections — only the Uzbrukumi card
    is the anchor; Spriedzes and Atbalsts are annotated but not anchored."""
    tensions = [
        _make_tension(1, 2, "uzbrukums"),
        _make_tension(1, 2, "spriedze"),
        _make_tension(1, 2, "atbalsts"),
    ]
    out = _fetch_saites_for_profile(
        empty_db, pid=1, profile_kind="politician", tensions=tensions, commentary_about=[]
    )
    assert out["uzbrukumi"][0]["is_anchor"] is True
    assert out["spriedzes"][0]["is_anchor"] is False
    assert out["atbalsts"][0]["is_anchor"] is False
    assert out["uzbrukumi"][0]["other_pid"] == 2
    assert out["spriedzes"][0]["other_pid"] == 2
    assert out["atbalsts"][0]["other_pid"] == 2


def test_pid_neither_source_nor_target_falls_into_else_branch(empty_db):
    """When the current politician is neither source nor target (malformed input
    that the caller should pre-filter), _annotate_card hits the `else` branch
    and assigns other_pid = source_pid. This is documented defensive behavior
    — the annotation block does not raise, but the tension list is bucketed by
    tension_type upstream and is expected to involve pid. This test pins the
    current behavior so future refactors don't silently change it."""
    tensions = [_make_tension(3, 4, "uzbrukums", source_name="X", target_name="Y")]
    out = _fetch_saites_for_profile(
        empty_db, pid=1, profile_kind="politician", tensions=tensions, commentary_about=[]
    )
    # Falls into else branch: other_pid = source_pid = 3
    assert out["uzbrukumi"][0]["other_pid"] == 3
    assert out["uzbrukumi"][0]["other_slug"] == "x"
    assert out["uzbrukumi"][0]["is_anchor"] is True
