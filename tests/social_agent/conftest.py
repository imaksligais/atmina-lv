"""Ensure Playwright subprocess calls work on Windows even after asyncio.run() is used
by other tests in the package (publisher tests use asyncio.run, which on Windows can
leave the default loop policy in a state where subsequent subprocess_exec raises
NotImplementedError).

Root cause: twikit resets the event loop policy to WindowsSelectorEventLoopPolicy on
import. We restore it via a pytest_configure hook which runs after all modules are
collected/imported, and also via an autouse session fixture so it is active for every
test run."""
import asyncio
import sys

import pytest


def _force_proactor() -> None:
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())


def pytest_configure(config: pytest.Config) -> None:
    """Restore ProactorEventLoopPolicy after twikit import resets it."""
    _force_proactor()


@pytest.fixture(autouse=True, scope="session")
def _win_proactor_policy() -> None:
    """Re-assert ProactorEventLoopPolicy at session start (belt-and-suspenders)."""
    _force_proactor()
