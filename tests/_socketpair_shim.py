"""Windows ``socket.socketpair`` with a bounded accept, for the test process only.

Why: on this machine loopback (127.0.0.1) SYNs are sometimes lost — 2026-10-29
in a bare Python process (no pytest/xdist/load), 5 and 43 of 3000 connects
needed a 1-4 s SYN retransmit and 9 of 3000 got no connection within 5 s
(.scratch/testfix/accept_latency.py; hangs: .scratch/testdiag/stress*.log,
run1.log; wiki/CHANGELOG.md 2026-10-29). Python 3.12 on Windows has no native
socketpair, so ``socket.socketpair`` is ``socket._fallback_socketpair``, which
blocks in ``lsock.accept()`` with no timeout. asyncio calls it for EVERY new
event loop (``_make_self_pipe``: ``asyncio.run``, ``sync_playwright()``), so
one lost connection hung check.sh forever.

This is the stdlib fallback (Python 3.12 Lib/socket.py) with one change: the
listener's ``accept()`` times out, and the whole pair is rebuilt up to
``MAX_ATTEMPTS`` times. The client connect is non-blocking (as in stdlib), so
it cannot hang by itself. Returned sockets are blocking, exactly as stdlib.
Production code (src/render OG cards, ingest asyncio) is NOT covered.
"""

from __future__ import annotations

import socket

ACCEPT_TIMEOUT = 5.0  # a healthy loopback accept takes well under 1 ms
MAX_ATTEMPTS = 5
RETRIES = 0  # how many lost connections were recovered (stress-run evidence)


def _connect(csock: socket.socket, addr) -> None:
    """Start the non-blocking connect; a seam so the test can lose one."""
    try:
        csock.connect(addr)
    except (BlockingIOError, InterruptedError):
        pass


def _socketpair_once(family, type, proto):
    if family == socket.AF_INET:
        host = socket._LOCALHOST
    elif family == socket.AF_INET6:
        host = socket._LOCALHOST_V6
    else:
        raise ValueError("Only AF_INET and AF_INET6 socket address families are supported")
    if type != socket.SOCK_STREAM:
        raise ValueError("Only SOCK_STREAM socket type is supported")
    if proto != 0:
        raise ValueError("Only protocol zero is supported")

    lsock = socket.socket(family, type, proto)
    try:
        lsock.bind((host, 0))
        lsock.listen()
        addr, port = lsock.getsockname()[:2]
        csock = socket.socket(family, type, proto)
        try:
            csock.setblocking(False)
            _connect(csock, (addr, port))
            csock.setblocking(True)
            lsock.settimeout(ACCEPT_TIMEOUT)  # the only change vs. stdlib
            ssock, _ = lsock.accept()
        except:  # noqa: E722 — mirror stdlib: close on ANY error, re-raise
            csock.close()
            raise
    finally:
        lsock.close()

    try:
        if (
            ssock.getsockname() != csock.getpeername()
            or csock.getsockname() != ssock.getpeername()
        ):
            raise ConnectionError("Unexpected peer connection")
    except:  # noqa: E722
        ssock.close()
        csock.close()
        raise
    return (ssock, csock)


def socketpair(family=socket.AF_INET, type=socket.SOCK_STREAM, proto=0):
    global RETRIES
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            return _socketpair_once(family, type, proto)
        except TimeoutError:
            if attempt == MAX_ATTEMPTS:
                raise TimeoutError(
                    f"socketpair: loopback connection lost {MAX_ATTEMPTS} times in a row "
                    f"({ACCEPT_TIMEOUT}s accept timeout each); see tests/_socketpair_shim.py"
                ) from None
            RETRIES += 1


def install() -> None:
    """Replace ``socket.socketpair`` (Windows only; elsewhere it is native)."""
    if socket.socketpair is socket._fallback_socketpair:
        socket.socketpair = socketpair
