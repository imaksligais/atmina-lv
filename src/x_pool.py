"""
Round-robin pool of twikit X/Twitter clients.

Each slot loads cookies from data/x_cookies/{slot}.json.
Rate-limited slots are skipped until their reset time expires.
"""
import logging
import time
from pathlib import Path

from twikit import Client

logger = logging.getLogger(__name__)

COOKIES_DIR = Path(__file__).resolve().parent.parent / "data" / "x_cookies"


class XClientPool:
    """Manages multiple twikit clients with round-robin rotation."""

    def __init__(self, slot_count: int = 5):
        self._slot_count = slot_count
        self._clients: dict[int, Client | None] = {i: None for i in range(slot_count)}
        self._rate_limits: dict[int, float] = {}
        self._next_slot = 0

    @property
    def slot_count(self) -> int:
        return self._slot_count

    def get_next_slot(self) -> int:
        """Return next available slot index (round-robin, skipping rate-limited)."""
        checked = 0
        while checked < self._slot_count:
            slot = self._next_slot
            self._next_slot = (self._next_slot + 1) % self._slot_count
            if self._clients[slot] is None:
                checked += 1
                continue
            reset_time = self._rate_limits.get(slot, 0)
            if reset_time > time.time():
                checked += 1
                continue
            self._rate_limits.pop(slot, None)
            return slot
        raise RuntimeError(
            f"All {self._slot_count} slots are rate-limited or uninitialized"
        )

    def get_client(self, slot: int) -> Client:
        """Get the twikit Client for a specific slot."""
        client = self._clients.get(slot)
        if client is None:
            raise RuntimeError(f"Slot {slot} not initialized — no cookies loaded")
        return client

    def report_rate_limit(self, slot: int, reset_time: float) -> None:
        """Mark a slot as rate-limited until reset_time (unix timestamp)."""
        self._rate_limits[slot] = reset_time
        logger.warning("Pool slot %d rate-limited until %.0f", slot, reset_time)

    async def load_all(self) -> int:
        """Load cookies from data/x_cookies/{slot}.json for each slot.
        Also supports legacy data/x_cookies.json as slot 0.
        Returns number of successfully loaded slots.
        """
        loaded = 0
        legacy_path = COOKIES_DIR.parent / "x_cookies.json"

        for slot in range(self._slot_count):
            cookie_path = COOKIES_DIR / f"{slot + 1}.json"
            if slot == 0 and not cookie_path.exists() and legacy_path.exists():
                cookie_path = legacy_path

            if not cookie_path.exists():
                logger.debug("Pool slot %d: no cookies at %s", slot, cookie_path)
                continue

            try:
                client = Client("en-US")
                client.load_cookies(str(cookie_path))
                self._clients[slot] = client
                loaded += 1
                logger.info("Pool slot %d: loaded cookies from %s", slot, cookie_path.name)
            except Exception as e:
                logger.warning("Pool slot %d: cookie load failed (%s)", slot, e)

        if loaded == 0:
            raise RuntimeError(
                f"No cookie files found in {COOKIES_DIR}/ or {legacy_path}"
            )
        logger.info("Pool ready: %d/%d slots loaded", loaded, self._slot_count)
        return loaded

    def status(self) -> list[dict]:
        """Return diagnostic status for each slot."""
        now = time.time()
        result = []
        for slot in range(self._slot_count):
            reset = self._rate_limits.get(slot, 0)
            result.append({
                "slot": slot,
                "available": self._clients[slot] is not None and reset <= now,
                "has_client": self._clients[slot] is not None,
                "rate_limited_until": reset if reset > now else None,
            })
        return result

    def reset(self) -> None:
        """Clear all clients and rate limits."""
        self._clients = {i: None for i in range(self._slot_count)}
        self._rate_limits.clear()
        self._next_slot = 0


_pool: XClientPool | None = None


async def get_pool(slot_count: int = 5) -> XClientPool:
    """Get or initialize the global client pool."""
    global _pool
    if _pool is None:
        _pool = XClientPool(slot_count=slot_count)
        await _pool.load_all()
    return _pool


def reset_pool() -> None:
    """Reset the global pool (e.g., between tweets and mentions)."""
    global _pool
    if _pool is not None:
        _pool.reset()
    _pool = None
