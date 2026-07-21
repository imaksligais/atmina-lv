"""
Chronological ingest journal for atmina.

Rotates monthly: entries are appended to ``wiki/log-ingest/<YYYY-MM>.md``.

Legacy single-file mode: if ``log_path`` ends with ``.md`` the caller gets
the original append-to-single-file behavior (used by tests and for reading
historical data).
"""

from datetime import datetime, timezone, timedelta
from pathlib import Path

DEFAULT_LOG_PATH = "wiki/log-ingest"  # directory — rotates monthly

_LV_OFFSET = timedelta(hours=3)  # EEST


def _now_lv() -> str:
    return (datetime.now(timezone.utc) + _LV_OFFSET).strftime("%Y-%m-%d %H:%M:%S")


def _resolve_log_file(log_path: str) -> Path:
    """Resolve ``log_path`` to the actual file to append to.

    Paths ending in ``.md`` are treated as a single file (legacy).
    Any other path is treated as a directory and routed to the current
    month's file (``<log_path>/<YYYY-MM>.md``). Creates parent dir and
    header if the target does not yet exist.
    """
    p = Path(log_path)
    if log_path.endswith(".md"):
        if not p.exists():
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("# Ingest Log\n\n", encoding="utf-8")
        return p
    p.mkdir(parents=True, exist_ok=True)
    year_month = _now_lv()[:7]
    f = p / f"{year_month}.md"
    if not f.exists():
        f.write_text(f"# Ingest Log — {year_month}\n\n", encoding="utf-8")
    return f


def append_ingest_entry(
    log_path: str = DEFAULT_LOG_PATH,
    source_name: str = "",
    source_tier: int = 0,
    documents_added: int = 0,
    documents_skipped: int = 0,
    status: str = "success",
    error: str | None = None,
    extra: str | None = None,
) -> None:
    """Append one ingest entry to the log."""
    path = _resolve_log_file(log_path)

    ts = _now_lv()
    status_icon = "+" if status == "success" else "x" if status == "failure" else "~"
    parts = [
        f"- `{ts}` [{status_icon}] {status} **{source_name}** (tier {source_tier})",
        f"— {documents_added} new, {documents_skipped} skipped",
    ]
    if extra:
        parts.append(f"— {extra}")
    if error:
        parts.append(f"— ERROR: {error}")

    line = " ".join(parts) + "\n"

    with path.open("a", encoding="utf-8") as f:
        f.write(line)


def append_ingest_batch_summary(
    results: list[dict],
    log_path: str = DEFAULT_LOG_PATH,
) -> None:
    """Append a batch summary after ingest_all completes."""
    path = _resolve_log_file(log_path)

    ts = _now_lv()
    total_docs = sum(r.get("documents", 0) for r in results)
    successes = sum(1 for r in results if r.get("status") == "success")
    failures = sum(1 for r in results if r.get("status") == "failure")

    with path.open("a", encoding="utf-8") as f:
        f.write(
            f"\n### {ts} — Ingest batch: {len(results)} sources, "
            f"{total_docs} docs, {successes} ok, {failures} failed\n\n"
        )

    for r in results:
        append_ingest_entry(
            log_path=log_path,
            source_name=r.get("source", "unknown"),
            source_tier=r.get("tier", 0),
            documents_added=r.get("documents", 0),
            documents_skipped=r.get("skipped", 0),
            status=r.get("status", "unknown"),
            error=r.get("error"),
        )


def read_ingest_log(log_path: str = DEFAULT_LOG_PATH, last_n: int = 20) -> list[str]:
    """Read last N entry lines from the log (most recent first).

    When ``log_path`` is a directory, reads across monthly files newest
    first and concatenates until ``last_n`` entries are collected.
    """
    p = Path(log_path)
    if log_path.endswith(".md"):
        if not p.exists():
            return []
        lines = [
            line.rstrip()
            for line in p.read_text(encoding="utf-8").splitlines()
            if line.startswith("- ")
        ]
        return list(reversed(lines[-last_n:]))
    if not p.exists():
        return []
    month_files = sorted(p.glob("*.md"), reverse=True)  # newest month first
    collected: list[str] = []
    for f in month_files:
        file_lines = [
            line.rstrip()
            for line in f.read_text(encoding="utf-8").splitlines()
            if line.startswith("- ")
        ]
        collected.extend(reversed(file_lines))  # newest-in-file first
        if len(collected) >= last_n:
            break
    return collected[:last_n]
