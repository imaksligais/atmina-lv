"""Task 1.4 — slot health panel."""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _reset_slot_cache():
    """Ensure cache state doesn't leak between tests."""
    from src.dashboard.views import slots

    slots._SLOT_CACHE.clear()
    slots._SLOT_CACHE.update({"probed_at": None, "result": None})
    yield
    slots._SLOT_CACHE.clear()
    slots._SLOT_CACHE.update({"probed_at": None, "result": None})


def _stub_probe_result(slot: int, healthy_endpoints: set[str] | None = None) -> dict:
    """Helper: build a probe result dict with a controlled health profile."""
    endpoints = ("get_user", "user_tweets", "user_replies", "search_tweet")
    healthy_endpoints = healthy_endpoints if healthy_endpoints is not None else set(endpoints)
    return {
        "slot": slot,
        "file": f"{slot}.json",
        **{e: ("ok" if e in healthy_endpoints else "FAIL: TestStub") for e in endpoints},
        "error": None,
    }


def test_slot_snapshot_returns_per_slot_per_endpoint_results(monkeypatch):
    from src.dashboard.views import slots

    fake = [_stub_probe_result(i) for i in range(1, 7)]
    monkeypatch.setattr(slots, "probe_all_slots", lambda: fake)

    snap = slots.get_slot_snapshot()
    assert len(snap["slots"]) == 6
    for s in snap["slots"]:
        assert "slot" in s
        for endpoint in ("get_user", "user_tweets", "user_replies", "search_tweet"):
            assert endpoint in s
    # probed_at + age available for "probed Ns ago" UI rendering
    assert snap["age_seconds"] == 0
    assert snap["probed_at"] is not None


def test_slot_snapshot_uses_60s_cache_unless_force_true(monkeypatch):
    from src.dashboard.views import slots

    call_count = {"n": 0}

    def counting_probe():
        call_count["n"] += 1
        return [_stub_probe_result(i) for i in range(1, 3)]

    monkeypatch.setattr(slots, "probe_all_slots", counting_probe)

    slots.get_slot_snapshot()
    slots.get_slot_snapshot()
    slots.get_slot_snapshot()
    assert call_count["n"] == 1, "cache must absorb repeated reads within TTL"

    slots.get_slot_snapshot(force=True)
    assert call_count["n"] == 2, "force=True must bypass cache"


def test_slot_snapshot_handles_zero_slot_files_gracefully(monkeypatch):
    from src.dashboard.views import slots

    monkeypatch.setattr(slots, "probe_all_slots", lambda: [])
    snap = slots.get_slot_snapshot()
    assert snap["slots"] == []
    assert snap["healthy_search_count"] == 0


def test_snapshot_counts_healthy_search_endpoints(monkeypatch):
    from src.dashboard.views import slots

    # 3 of 6 slots have search_tweet healthy → matches the live 2026-05-16 state
    profile = [
        _stub_probe_result(1, {"get_user", "user_tweets", "user_replies", "search_tweet"}),
        _stub_probe_result(2, {"get_user", "user_tweets", "user_replies", "search_tweet"}),
        _stub_probe_result(3, {"get_user", "user_tweets", "user_replies", "search_tweet"}),
        _stub_probe_result(4, {"get_user", "user_tweets"}),
        _stub_probe_result(5, {"get_user", "user_tweets"}),
        _stub_probe_result(6, {"get_user", "user_tweets"}),
    ]
    monkeypatch.setattr(slots, "probe_all_slots", lambda: profile)

    snap = slots.get_slot_snapshot()
    assert snap["healthy_search_count"] == 3
    assert snap["total_slots"] == 6


def test_index_renders_slot_panel_with_guardrail_warning(tmp_path, monkeypatch):
    """When `healthy_search_count < SEARCH_MIN_HEALTHY_SLOTS`, the panel must
    surface the guardrail warning chip — that's the entire reason this panel
    exists (degradation visibility from commit 52775ac)."""
    from src.db import init_db
    from src.dashboard.server import create_app
    from src.dashboard.views import slots

    profile = [
        _stub_probe_result(i, {"get_user", "user_tweets"} | ({"search_tweet"} if i <= 2 else set()))
        for i in range(1, 7)
    ]
    monkeypatch.setattr(slots, "probe_all_slots", lambda: profile)

    db_path = tmp_path / "test.db"
    init_db(str(db_path))
    app = create_app(db_path=str(db_path))
    html = app.test_client().get("/").get_data(as_text=True)

    assert 'id="slot-panel"' in html
    # Warning copy must appear when healthy < 4
    assert "fallback" in html.lower() or "timeline" in html.lower() or "2/6" in html
    # Each slot rendered as a card
    for i in range(1, 7):
        assert f"slot {i}" in html.lower() or f"slot-{i}" in html


# -------------------------------------------------- Task 2.3: force-refresh


def test_force_refresh_bypasses_cache(tmp_path, monkeypatch):
    """`POST /api/slots/refresh` must call probe_all_slots even when the
    cache is warm — that's the entire point of operator-triggered refresh.
    """
    from src.db import init_db
    from src.dashboard.server import create_app
    from src.dashboard.views import slots

    call_count = {"n": 0}
    profile = [_stub_probe_result(i) for i in range(1, 4)]

    def counting_probe():
        call_count["n"] += 1
        return profile

    monkeypatch.setattr(slots, "probe_all_slots", counting_probe)

    db_path = tmp_path / "test.db"
    init_db(str(db_path))
    app = create_app(db_path=str(db_path))

    # Prime the cache via a normal page load
    app.test_client().get("/")
    assert call_count["n"] == 1

    # Force-refresh — counter must tick again
    resp = app.test_client().post("/api/slots/refresh")
    assert resp.status_code == 200
    assert call_count["n"] == 2, "force-refresh must bypass the 60 s cache"


def test_refresh_returns_updated_slot_panel(tmp_path, monkeypatch):
    """Refresh response is the slot panel partial (HTMX outerHTML swap)."""
    import json as _json

    from src.db import init_db
    from src.dashboard.server import create_app
    from src.dashboard.views import slots

    profile = [_stub_probe_result(i) for i in range(1, 7)]
    monkeypatch.setattr(slots, "probe_all_slots", lambda: profile)

    db_path = tmp_path / "test.db"
    init_db(str(db_path))
    app = create_app(db_path=str(db_path))

    resp = app.test_client().post("/api/slots/refresh")
    html = resp.get_data(as_text=True)
    assert 'id="slot-panel"' in html
    for i in range(1, 7):
        assert f"slot-{i}" in html

    trigger = _json.loads(resp.headers["HX-Trigger"])
    assert "6/6" in trigger["showToast"]["message"] or "healthy" in trigger["showToast"]["message"].lower()


def test_refresh_toast_warns_when_below_threshold(tmp_path, monkeypatch):
    """When refresh shows guardrail tripped, toast level escalates to warning."""
    import json as _json

    from src.db import init_db
    from src.dashboard.server import create_app
    from src.dashboard.views import slots

    profile = [
        _stub_probe_result(i, {"get_user", "user_tweets"} | ({"search_tweet"} if i <= 2 else set()))
        for i in range(1, 7)
    ]
    monkeypatch.setattr(slots, "probe_all_slots", lambda: profile)

    db_path = tmp_path / "test.db"
    init_db(str(db_path))
    app = create_app(db_path=str(db_path))

    resp = app.test_client().post("/api/slots/refresh")
    trigger = _json.loads(resp.headers["HX-Trigger"])
    assert trigger["showToast"]["level"] == "warning"


def test_slot_panel_renders_refresh_button(tmp_path, monkeypatch):
    """The panel template must wire the HTMX POST + shortcut hook."""
    from src.db import init_db
    from src.dashboard.server import create_app
    from src.dashboard.views import slots

    monkeypatch.setattr(slots, "probe_all_slots",
                        lambda: [_stub_probe_result(i) for i in range(1, 7)])
    db_path = tmp_path / "test.db"
    init_db(str(db_path))
    app = create_app(db_path=str(db_path))
    html = app.test_client().get("/").get_data(as_text=True)

    assert "/api/slots/refresh" in html
    assert 'hx-post="/api/slots/refresh"' in html
    assert 'data-shortcut="R"' in html
