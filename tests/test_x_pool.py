"""Tests for X/Twitter client pool with round-robin rotation and rate-limit cooldown."""
import time
import pytest
from unittest.mock import MagicMock
from src.x_pool import XClientPool


class TestPoolRotation:
    """Round-robin rotation across available slots."""

    def test_round_robin_returns_slots_in_order(self):
        pool = XClientPool(slot_count=3)
        for i in range(3):
            pool._clients[i] = MagicMock()
        assert pool.get_next_slot() == 0
        assert pool.get_next_slot() == 1
        assert pool.get_next_slot() == 2
        assert pool.get_next_slot() == 0  # wraps

    def test_skips_rate_limited_slot(self):
        pool = XClientPool(slot_count=3)
        for i in range(3):
            pool._clients[i] = MagicMock()
        pool.report_rate_limit(1, time.time() + 600)
        slots = [pool.get_next_slot() for _ in range(4)]
        assert 1 not in slots
        assert slots == [0, 2, 0, 2]

    def test_rate_limited_slot_recovers_after_reset(self):
        pool = XClientPool(slot_count=2)
        for i in range(2):
            pool._clients[i] = MagicMock()
        pool.report_rate_limit(0, time.time() - 1)
        assert pool.get_next_slot() == 0

    def test_all_slots_rate_limited_raises(self):
        pool = XClientPool(slot_count=2)
        for i in range(2):
            pool._clients[i] = MagicMock()
        future = time.time() + 600
        pool.report_rate_limit(0, future)
        pool.report_rate_limit(1, future)
        with pytest.raises(RuntimeError, match="All .* slots are rate-limited"):
            pool.get_next_slot()


class TestPoolClientAccess:
    """Getting actual twikit clients from pool slots."""

    def test_get_client_returns_client_for_slot(self):
        pool = XClientPool(slot_count=2)
        mock_client = MagicMock()
        pool._clients[0] = mock_client
        assert pool.get_client(0) is mock_client

    def test_get_client_uninitialized_raises(self):
        pool = XClientPool(slot_count=2)
        with pytest.raises(RuntimeError, match="not initialized"):
            pool.get_client(1)


class TestPoolStatus:
    """Pool status reporting for diagnostics."""

    def test_status_shows_all_slots(self):
        pool = XClientPool(slot_count=2)
        pool._clients[0] = MagicMock()
        status = pool.status()
        assert len(status) == 2
        assert status[0]["available"] is True
        assert status[1]["available"] is False
