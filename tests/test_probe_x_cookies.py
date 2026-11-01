"""Tests for scripts.probe_x_cookies — [OK] only when all 4 endpoints actually ran."""

from scripts.probe_x_cookies import _slot_status


def _res(**overrides):
    base = {
        "slot": 1,
        "file": "1.json",
        "get_user": None,
        "user_tweets": None,
        "user_replies": None,
        "search_tweet": None,
        "error": None,
        "key_rebuilds": 0,
    }
    base.update(overrides)
    return base


def test_ok_requires_all_four_probed_and_zero_fail():
    marker, probed, failed = _slot_status(
        _res(
            get_user="ok (AtminaLV)",
            user_tweets="ok (2)",
            user_replies="ok (2)",
            search_tweet="ok (1)",
        )
    )
    assert marker == "OK"
    assert probed == 4
    assert failed == 0


def test_broken_when_all_probed_but_some_fail():
    marker, probed, failed = _slot_status(
        _res(
            get_user="ok (AtminaLV)",
            user_tweets="ok (2)",
            user_replies="FAIL: X: 404",
            search_tweet="FAIL: X: 404",
        )
    )
    assert marker == "BROKEN (2/4)"
    assert probed == 4
    assert failed == 2


def test_not_probed_when_bootstrap_raises():
    """Client('en-US')/load_cookies() exception leaves every endpoint None."""
    marker, probed, failed = _slot_status(_res(error="SomeException: boom"))
    assert marker == "NOT_PROBED (0/4)"
    assert probed == 0
    assert failed == 0


def test_not_probed_when_get_user_fails_early():
    """get_user failure returns early — three endpoints stay unprobed."""
    marker, probed, failed = _slot_status(_res(get_user="FAIL: SomeException: x"))
    assert marker == "NOT_PROBED (1/4)"
    assert probed == 1
    assert failed == 1
