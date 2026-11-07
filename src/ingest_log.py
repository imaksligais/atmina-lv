"""
Chronological ingest journal for atmina.

Rotates monthly: entries are appended to ``wiki/log-ingest/<YYYY-MM>.md``.

Legacy single-file mode: if ``log_path`` ends with ``.md`` the caller gets
the original append-to-single-file behavior (used by tests and for reading
historical data).
"""

from pathlib import Path

from src.db import now_lv

DEFAULT_LOG_PATH = "wiki/log-ingest"  # directory — rotates monthly

_LV_MONTHS = (
    "janvāris", "februāris", "marts", "aprīlis", "maijs", "jūnijs",
    "jūlijs", "augusts", "septembris", "oktobris", "novembris", "decembris",
)


def _ensure_index_entry(dir_path: Path, year_month: str) -> bool:
    """Add ``year_month`` to the hand-written month index next to ``dir_path``.

    The monthly files rotate automatically but ``wiki/log-ingest.md`` § Mēneši
    was maintained by hand, so it drifted silently: for three months (05–07) it
    listed only April, and on 2026-08-27 it was again one month behind. The
    file's own note asked whoever opens a new month to add the line — a gate
    that depends on a human remembering. This closes it in the code path that
    actually opens the month.

    Idempotent and self-healing: it appends only months missing from the list,
    so an index that already drifted catches up on the next ingest. Returns
    True when the index was written. No-op when the index file does not exist
    (the directory is usable without one).
    """
    index = dir_path.with_suffix(".md")
    if not index.exists():
        return False
    text = index.read_text(encoding="utf-8")
    link = f"[[log-ingest/{year_month}|"
    if link in text:
        return False
    year, month = year_month.split("-")
    label = f"{year}. gada {_LV_MONTHS[int(month) - 1]}"
    line = f"- [[log-ingest/{year_month}|{label}]]\n"
    lines = text.splitlines(True)
    # Insert after the last existing month line; fall back to after "## Mēneši".
    last = max(
        (i for i, ln in enumerate(lines) if ln.startswith("- [[log-ingest/")),
        default=None,
    )
    if last is None:
        last = next(
            (i for i, ln in enumerate(lines) if ln.strip().startswith("## Mēneši")),
            None,
        )
        if last is None:
            return False
        lines.insert(last + 1, "\n")
        last += 1
    lines.insert(last + 1, line)
    index.write_text("".join(lines), encoding="utf-8")
    return True


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
    year_month = now_lv()[:7]
    f = p / f"{year_month}.md"
    if not f.exists():
        f.write_text(f"# Ingest Log — {year_month}\n\n", encoding="utf-8")
    _ensure_index_entry(p, year_month)
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

    ts = now_lv()
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

    ts = now_lv()
    total_docs = sum(r.get("documents", 0) for r in results)
    successes = sum(1 for r in results if r.get("status") == "success")
    failures = sum(1 for r in results if r.get("status") == "failure")

    # Nogrieztais ievads (verdikts 40, 2026-09-06) — vienmēr ar saucēju.
    # Skaitlis bez saucēja nešķir kluso dienu no salūzuša detektora
    # (CLAUDE.md § A gate that cannot fail is not evidence). Rinda iet ###
    # virsrakstā, ne kā atsevišķs `- ` punkts, jo `read_ingest_log()` lasa
    # tieši `- ` rindas un uzskatītu to par ielādes ierakstu.
    cut_lede = sum(r.get("cut_lede", 0) for r in results)
    web_docs = sum(r.get("web_documents", 0) for r in results)
    lede_tail = (
        f" — {cut_lede} no {web_docs} web dokiem ar nogrieztu ievadu"
        if web_docs
        else ""
    )

    with path.open("a", encoding="utf-8") as f:
        f.write(
            f"\n### {ts} — Ingest batch: {len(results)} sources, "
            f"{total_docs} docs, {successes} ok, {failures} failed{lede_tail}\n\n"
        )

    for r in results:
        n = r.get("cut_lede", 0)
        append_ingest_entry(
            log_path=log_path,
            source_name=r.get("source", "unknown"),
            source_tier=r.get("tier", 0),
            documents_added=r.get("documents", 0),
            documents_skipped=r.get("skipped", 0),
            status=r.get("status", "unknown"),
            error=r.get("error"),
            extra=(
                f"nogriezts ievads: {n}/{r.get('web_documents', 0)}"
                if n else None
            ),
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
