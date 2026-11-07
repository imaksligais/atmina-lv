"""Windows socketpair shim (tests/_socketpair_shim.py, installed by conftest).

Failure this guards: on this machine a loopback connection is occasionally
lost, and the stdlib ``socket._fallback_socketpair`` then blocks forever in
``accept()`` — every new asyncio event loop calls it, so one lost SYN hung the
whole check.sh run. Here the first connect is "lost" on purpose; the shim must
time out, retry and hand back a working, blocking pair like the stdlib does.
"""

from __future__ import annotations

import socket
import sys
import threading

import pytest

from tests import _socketpair_shim as shim

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="shim is Windows-only")


def test_lost_loopback_connection_is_retried(monkeypatch):
    assert socket.socketpair is shim.socketpair, "conftest did not install the shim"
    real_connect, real_timeout = shim._connect, shim.ACCEPT_TIMEOUT
    calls = []

    def lossy_connect(csock, addr):
        calls.append(addr)
        if len(calls) == 1:
            # The SYN never reaches the listener; short wait so the test is fast.
            monkeypatch.setattr(shim, "ACCEPT_TIMEOUT", 0.3)
            return
        # Real retries keep the real timeout: on this machine a healthy accept
        # occasionally takes 1-4 s (SYN retransmit), and may itself be retried.
        monkeypatch.setattr(shim, "ACCEPT_TIMEOUT", real_timeout)
        real_connect(csock, addr)

    monkeypatch.setattr(shim, "_connect", lossy_connect)
    retries_before = shim.RETRIES
    result = {}
    # A daemon thread so a regression (accept without timeout) fails the test
    # instead of hanging the worker.
    t = threading.Thread(target=lambda: result.update(pair=socket.socketpair()), daemon=True)
    t.start()
    t.join(timeout=30)
    assert not t.is_alive(), "socketpair() never returned after a lost connection"

    a, b = result["pair"]
    try:
        assert len(calls) >= 2 and shim.RETRIES == retries_before + len(calls) - 1
        assert isinstance(a, socket.socket) and isinstance(b, socket.socket)
        assert a.gettimeout() is None and b.gettimeout() is None  # blocking, as stdlib
        a.sendall(b"x")
        assert b.recv(1) == b"x"
    finally:
        a.close()
        b.close()
