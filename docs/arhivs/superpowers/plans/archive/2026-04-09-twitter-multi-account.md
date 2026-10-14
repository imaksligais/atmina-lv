# Twitter Multi-Account Pool Implementation Plan

> **STATUS:** ✅ DONE — implementācija nogādāta produkcijā ar 6 cookie slotiem (`data/x_cookies/{1..6}.json`).
> `src/x_pool.py` (133 LOC) + `tests/test_x_pool.py` (71 LOC). `src/x_scraper.py` un `src/x_mentions.py` izsauc `get_pool()` un round-robin rotē klientus; `_client_cache` modulu līmeņa cache aizvākts.
> Checkbox-i zem netika atzīmēti progresa laikā — implementācija pabeigta agrīnās 2026-04 sesijās un live operatoriskā lietošanā kopš tā laika. Saglabāts kā vēsturisks references uz arhitektūras lēmumu.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the single-account Twitter/X client with a round-robin pool that rotates across multiple cookie-authenticated accounts, automatically resting rate-limited accounts.

**Architecture:** New `XClientPool` class in `src/x_pool.py` manages N twikit `Client` instances, each loaded from its own cookie file (`data/x_cookies/1.json`, `2.json`, ...). Every API call requests a client from the pool via `pool.get_client()` — the pool returns the next available client (round-robin), skipping any that are in rate-limit cooldown. When a 429 is caught, the caller reports it via `pool.report_rate_limit(slot, reset_time)` and retries with the next available client. Existing `x_scraper.py` and `x_mentions.py` are modified to use the pool instead of the module-level `_client_cache`.

**Tech Stack:** Python 3.11+, twikit, asyncio, existing cookie JSON format

---

### Task 1: Create `XClientPool` with tests

**Files:**
- Create: `src/x_pool.py`
- Create: `tests/test_x_pool.py`

- [ ] **Step 1: Write failing tests for pool core behavior**

```python
# tests/test_x_pool.py
"""Tests for X/Twitter client pool with round-robin rotation and rate-limit cooldown."""
import time
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from src.x_pool import XClientPool


class TestPoolRotation:
    """Round-robin rotation across available slots."""

    def test_round_robin_returns_slots_in_order(self):
        pool = XClientPool(slot_count=3)
        # Manually inject mock clients
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
        pool.report_rate_limit(1, time.time() + 600)  # slot 1 resting
        slots = [pool.get_next_slot() for _ in range(4)]
        assert 1 not in slots
        assert slots == [0, 2, 0, 2]

    def test_rate_limited_slot_recovers_after_reset(self):
        pool = XClientPool(slot_count=2)
        for i in range(2):
            pool._clients[i] = MagicMock()
        pool.report_rate_limit(0, time.time() - 1)  # already expired
        assert pool.get_next_slot() == 0  # available again

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
        assert status[1]["available"] is False  # no client loaded
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_x_pool.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.x_pool'`

- [ ] **Step 3: Implement `XClientPool`**

```python
# src/x_pool.py
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
        self._rate_limits: dict[int, float] = {}  # slot -> reset timestamp
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
            # Skip slots without clients
            if self._clients[slot] is None:
                checked += 1
                continue
            # Skip rate-limited slots that haven't reset
            reset_time = self._rate_limits.get(slot, 0)
            if reset_time > time.time():
                checked += 1
                continue
            # Clear expired rate limit
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
            # Slot 0 falls back to legacy single-file path
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


# Module-level singleton (initialized lazily)
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_x_pool.py -v`
Expected: All 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/x_pool.py tests/test_x_pool.py
git commit -m "feat: add XClientPool with round-robin rotation and rate-limit cooldown"
```

---

### Task 2: Migrate cookie file to new directory structure

**Files:**
- Create: `data/x_cookies/` (directory)
- No code changes — just file reorganization

- [ ] **Step 1: Create `data/x_cookies/` directory**

```bash
mkdir -p data/x_cookies
```

- [ ] **Step 2: Copy existing cookies as slot 1**

```bash
cp data/x_cookies.json data/x_cookies/1.json
```

The pool's `load_all()` has a legacy fallback: if `data/x_cookies/1.json` doesn't exist, it reads `data/x_cookies.json` for slot 0. So the old file still works, but having `1.json` is the canonical location going forward.

- [ ] **Step 3: Add `data/x_cookies/` to `.gitignore`**

Check if `data/x_cookies.json` is already gitignored. If so, ensure `data/x_cookies/` is also covered. Add this line to `.gitignore` if not present:

```
data/x_cookies/
```

- [ ] **Step 4: Commit**

```bash
git add data/x_cookies/.gitkeep .gitignore
git commit -m "chore: create data/x_cookies/ directory for multi-account cookie storage"
```

**Note:** When the user creates additional accounts, they save cookies as `data/x_cookies/2.json`, `3.json`, etc. The pool auto-discovers them on next `load_all()`.

---

### Task 3: Wire `x_scraper.py` to use pool instead of single client

**Files:**
- Modify: `src/x_scraper.py`
- Modify: `tests/test_x_pool.py` (add integration-style tests)

- [ ] **Step 1: Write failing test for pool-backed fetch**

Add to `tests/test_x_pool.py`:

```python
class TestPoolIntegration:
    """Verify x_scraper functions use pool rotation."""

    @pytest.mark.asyncio
    async def test_fetch_rotates_on_rate_limit(self):
        """When slot 0 hits 429, next call uses slot 1."""
        from src.x_pool import XClientPool

        pool = XClientPool(slot_count=2)
        mock_client_0 = AsyncMock()
        mock_client_1 = AsyncMock()
        pool._clients[0] = mock_client_0
        pool._clients[1] = mock_client_1

        # Simulate: slot 0 is rate limited
        pool.report_rate_limit(0, time.time() + 600)

        slot = pool.get_next_slot()
        assert slot == 1
        client = pool.get_client(slot)
        assert client is mock_client_1
```

- [ ] **Step 2: Run test to verify it passes** (this one should pass already with Task 1's code)

Run: `python -m pytest tests/test_x_pool.py::TestPoolIntegration -v`
Expected: PASS

- [ ] **Step 3: Modify `x_scraper.py` — replace `_client_cache` with pool**

Replace the module-level client cache and `_get_client()` with pool-based functions. Key changes:

In `src/x_scraper.py`, remove:
- `_client_cache`, `_client_mode` globals
- `_try_authenticated_client()` function
- `_get_client()` function
- `reset_client()` function

Replace with:

```python
from src.x_pool import get_pool, reset_pool

async def _get_client_and_slot() -> tuple:
    """Get next available (client, slot) from the pool."""
    pool = await get_pool()
    slot = pool.get_next_slot()
    return pool.get_client(slot), slot

# Keep reset_client as a wrapper for backward compat
def reset_client():
    """Reset the client pool."""
    reset_pool()
```

Update `_wait_for_rate_limit()` to accept and report slot:

```python
async def _wait_for_rate_limit(exc: TooManyRequests, context: str, slot: int | None = None) -> None:
    """Report rate limit to pool (if slot given) and raise to trigger retry with next slot."""
    if slot is not None:
        pool = await get_pool()
        reset_time = exc.rate_limit_reset if exc.rate_limit_reset else time.time() + 60
        pool.report_rate_limit(slot, reset_time + 2)
    # Don't sleep — the pool will rotate to next client
    logger.warning("%s: slot %s rate-limited, rotating", context, slot)
```

Update `fetch_user_tweets()` — get client+slot, on 429 report to pool and retry with new slot:

```python
async def fetch_user_tweets(handle: str, since_id: str | None = None,
                            limit: int = 20) -> list[dict]:
    """Fetch recent tweets for a user by handle. Rotates pool slots on rate limit."""
    pool = await get_pool()

    for attempt in range(pool.slot_count + 1):
        try:
            slot = pool.get_next_slot()
            client = pool.get_client(slot)
        except RuntimeError:
            logger.warning("fetch_user_tweets(@%s): all pool slots exhausted", handle)
            return []

        try:
            user = await client.get_user_by_screen_name(handle)
        except (UserNotFound, UserUnavailable) as e:
            logger.warning("fetch_user_tweets: @%s — %s", handle, e)
            return []
        except TooManyRequests as e:
            reset_time = e.rate_limit_reset if e.rate_limit_reset else time.time() + 60
            pool.report_rate_limit(slot, reset_time + 2)
            logger.warning("fetch_user_tweets(@%s): slot %d rate-limited, trying next", handle, slot)
            continue
        except Exception as e:
            logger.error("fetch_user_tweets: @%s lookup error — %s", handle, e)
            return []

        try:
            result = await client.get_user_tweets(
                user_id=user.id, tweet_type="Tweets", count=min(limit, 40))
        except TooManyRequests as e:
            reset_time = e.rate_limit_reset if e.rate_limit_reset else time.time() + 60
            pool.report_rate_limit(slot, reset_time + 2)
            logger.warning("fetch_user_tweets(@%s): slot %d rate-limited on tweets, trying next", handle, slot)
            continue
        except TwitterException as e:
            logger.error("fetch_user_tweets: API error for @%s — %s", handle, e)
            return []
        except Exception as e:
            logger.error("fetch_user_tweets: unexpected error for @%s — %s: %s", handle, type(e).__name__, e)
            return []

        # Success — filter and return
        tweets = []
        if result:
            for tweet in result:
                normalized = _normalize_tweet(tweet)
                if since_id and normalized["id"] <= since_id:
                    continue
                tweets.append(normalized)
                if len(tweets) >= limit:
                    break
        return tweets

    logger.warning("fetch_user_tweets(@%s): exhausted all slots", handle)
    return []
```

Apply same pattern to `fetch_user_replies()` — get client+slot per attempt, report 429 to pool, retry with next slot.

Update `fetch_all_x_accounts()` — no changes needed (it calls `fetch_user_tweets` / `fetch_user_replies` which now handle rotation internally).

- [ ] **Step 4: Update `x_mentions.py` to use pool**

In `src/x_mentions.py`, change the import:

```python
from src.x_pool import get_pool
```

Update `fetch_mentions()`:

```python
async def fetch_mentions(
    handle_to_pid: dict[str, int],
    limit: int = 20,
    batch_size: int = DEFAULT_BATCH_SIZE,
    delay: float = REQUEST_DELAY,
) -> tuple[list[dict], int]:
    queries = _build_mention_queries(handle_to_pid, batch_size=batch_size)
    if not queries:
        return [], 0

    pool = await get_pool()
    seen_ids = set()
    all_mentions = []
    errors = 0

    for i, query in enumerate(queries):
        logger.info("Mentions search [%d/%d]: %s", i + 1, len(queries), query[:80])

        # Try with pool rotation on rate limit
        success = False
        for _retry in range(pool.slot_count):
            try:
                slot = pool.get_next_slot()
                client = pool.get_client(slot)
            except RuntimeError:
                logger.warning("fetch_mentions: all pool slots exhausted")
                errors += 1
                break

            try:
                result = await client.search_tweet(query, product="Latest", count=min(limit, 40))
                success = True
                break
            except TooManyRequests as e:
                reset_time = e.rate_limit_reset if e.rate_limit_reset else time.time() + 60
                pool.report_rate_limit(slot, reset_time + 2)
                logger.warning("fetch_mentions: slot %d rate-limited, trying next", slot)
                continue
            except TwitterException as e:
                logger.error("fetch_mentions: API error on query %d — %s", i + 1, e)
                errors += 1
                break
            except Exception as e:
                logger.error("fetch_mentions: unexpected error — %s: %s", type(e).__name__, e)
                errors += 1
                break

        if not success:
            errors += 1
            if i < len(queries) - 1:
                await asyncio.sleep(delay)
            continue

        if result:
            for tweet in result:
                mention = _normalize_mention(tweet, handle_to_pid)
                if mention["id"] not in seen_ids and mention["mention_target_ids"]:
                    seen_ids.add(mention["id"])
                    all_mentions.append(mention)

        if i < len(queries) - 1:
            await asyncio.sleep(delay)

    logger.info("fetch_mentions: %d unique mentions found, %d query errors", len(all_mentions), errors)
    return all_mentions, errors
```

- [ ] **Step 5: Update `social.py` — remove `reset_client` before mentions**

In `src/social.py`, the `fetch_all_mentions()` function calls `reset_client()` before searching. Replace with `reset_pool()`:

```python
from src.x_pool import reset_pool

# In fetch_all_mentions(), replace:
#   reset_client()
# with:
    reset_pool()
```

Also update the import at the top of `social.py`:
```python
from src.x_scraper import fetch_user_tweets, fetch_user_replies, fetch_all_x_accounts, reset_client
```
Change to:
```python
from src.x_scraper import fetch_user_tweets, fetch_user_replies, fetch_all_x_accounts
from src.x_pool import reset_pool
```

- [ ] **Step 6: Run all tests**

Run: `python -m pytest tests/ -v`
Expected: All tests PASS (existing tests should not break — pool with 1 cookie behaves like single client)

- [ ] **Step 7: Commit**

```bash
git add src/x_scraper.py src/x_mentions.py src/social.py tests/test_x_pool.py
git commit -m "feat: wire x_scraper and x_mentions to use XClientPool for multi-account rotation"
```

---

### Task 4: Add pool status to routine diagnostics

**Files:**
- Modify: `src/routine.py` (add pool info to `print_routine()` output)

- [ ] **Step 1: Read `src/routine.py` to find where to add pool status**

Read the file to understand the current `print_routine()` structure.

- [ ] **Step 2: Add pool status section**

At the end of `print_routine()`, add:

```python
# Pool status
try:
    from src.x_pool import XClientPool, COOKIES_DIR
    cookie_files = list(COOKIES_DIR.glob("*.json"))
    legacy = COOKIES_DIR.parent / "x_cookies.json"
    if not cookie_files and legacy.exists():
        cookie_files = [legacy]
    print(f"\n🔑 X/Twitter pool: {len(cookie_files)} cookie file(s) in {COOKIES_DIR}")
    for f in sorted(cookie_files):
        print(f"  • {f.name}")
except Exception:
    pass
```

- [ ] **Step 3: Run verification**

Run: `PYTHONIOENCODING=utf-8 python -c "from src.routine import print_routine; print_routine()"`
Expected: Shows pool status at the bottom

- [ ] **Step 4: Commit**

```bash
git add src/routine.py
git commit -m "feat: show X/Twitter pool status in routine diagnostics"
```

---

### Task 5: Manual integration test with existing single cookie

**Files:** None (manual verification only)

- [ ] **Step 1: Verify pool loads with existing single cookie**

```bash
PYTHONIOENCODING=utf-8 python -c "
import asyncio
from src.x_pool import get_pool
async def main():
    pool = await get_pool()
    for s in pool.status():
        print(s)
asyncio.run(main())
"
```
Expected: Slot 0 shows `available: True`, rest show `available: False` / `has_client: False`

- [ ] **Step 2: Test fetch with pool**

```bash
PYTHONIOENCODING=utf-8 python -c "
import asyncio
from src.x_scraper import fetch_user_tweets
tweets = asyncio.run(fetch_user_tweets('EvikaSilina', limit=3))
print(f'{len(tweets)} tweets fetched')
for t in tweets[:2]:
    print(f'  {t[\"source_url\"]}')
"
```
Expected: Tweets fetched successfully using pool slot 0

- [ ] **Step 3: Run full test suite**

Run: `python -m pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 4: Commit (if any fixups needed)**

---

## Adding New Accounts

When the user creates additional X/Twitter accounts:

1. Log in via browser, extract cookies (auth_token + ct0) from DevTools
2. Save as `data/x_cookies/2.json` (same JSON format as existing `x_cookies.json`)
3. Repeat for `3.json`, `4.json`, `5.json`
4. Pool auto-discovers on next `load_all()` — no code changes needed
5. Verify: `python -c "from src.routine import print_routine; print_routine()"` shows all slots
