"""
Wiki page primitives for atmina — frontmatter, body preservation, sync blocks.

Carved out of ``src/wiki.py`` on 2026-09-05 (plāna 5.9) with no behaviour
change; ``src.wiki`` re-exports every name below, because the split had to stay
under the SAME import path (`.claude/agents/quality-reviewer.md` imports
`src.wiki_lint` verbatim and the runbooks import `src.wiki`). Flat sibling
module, NOT a package.

This is the lowest leaf of the wiki trio (`wiki_format` → `wiki_pages` /
`wiki_index` → `wiki`), so the two path defaults live here: both the
orchestrator and ``wiki_index._build_index`` need ``DEFAULT_DB_PATH``, and a
second copy of the string would be the kind of drift this repo keeps paying for.
"""

import re
import sqlite3
from pathlib import Path

import yaml

DEFAULT_DB_PATH = "data/atmina.db"
DEFAULT_WIKI_DIR = "wiki"

def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from markdown text.

    Returns (frontmatter_dict, body_string).
    If no frontmatter, returns ({}, text).
    """
    if not text.startswith("---"):
        return {}, text

    # Find the closing ---
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text

    yaml_block = text[3:end].strip()
    body = text[end + 4:].lstrip("\n")

    try:
        fm = yaml.safe_load(yaml_block) or {}
    except yaml.YAMLError:
        fm = {}

    return fm, body


def _render_frontmatter(data: dict) -> str:
    """Render a dict as a YAML frontmatter block."""
    return "---\n" + yaml.dump(
        data,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
    ) + "---\n"


def _sanitize_body(body: str) -> str:
    """Drop NUL bytes from a page body read off disk.

    A NUL is never legitimate content here — every writer in this module emits
    UTF-8 text — so its presence always means the file was damaged, and the
    only faithful reading of a NUL run is "this content is gone".

    Why this exists: a truncated write leaves the frontmatter intact and the
    entire body replaced by a contiguous NUL run to EOF (the filesystem records
    the new length but never flushes the tail). NUL decodes cleanly as UTF-8, so
    ``_parse_frontmatter`` returned it as a perfectly ordinary body and
    ``_update_page``'s preserve-the-body contract wrote it straight back out on
    every subsequent sync. 22 tracked pages sat corrupt in the public repo from
    2026-05-31 to 2026-08-01 for exactly this reason — two party pages had no
    body left at all. Stripping on READ makes the damage self-healing: the next
    sync drops the NULs, and an emptied body falls back to the freshly built
    default (see ``_update_page``).
    """
    return body.replace("\x00", "") if "\x00" in body else body


def _update_page(path: Path, new_frontmatter: dict, default_body: str = "") -> None:
    """Create or update a wiki page.

    If the page exists: update frontmatter only, preserve body.
    If new — or if the on-disk body was destroyed (see ``_sanitize_body``) —
    create the stub with frontmatter + default_body.
    """
    body = default_body
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        _old_fm, existing_body = _parse_frontmatter(existing)
        existing_body = _sanitize_body(existing_body)
        # An empty body after sanitizing means either a genuinely bodyless page
        # or one whose body was lost — both want the freshly built default back.
        if existing_body.strip():
            body = existing_body

    content = _render_frontmatter(new_frontmatter)
    if body:
        content += "\n" + body

    path.write_text(content, encoding="utf-8")


_SYNC_START = "<!-- SYNC-AUTO -->"
_SYNC_END = "<!-- /SYNC-AUTO -->"

# A hand-era "## Biedri" section: heading up to (not incl.) the next "## " or
# a sync marker or EOF. Applied only OUTSIDE the sync block by construction —
# callers strip it from the raw file BEFORE _update_page_with_sync_block
# rebuilds the block, and the generated block starts with its own marker line.
_LEGACY_BIEDRI_RE = None  # compiled lazily below (re imported at module top)


def _strip_legacy_biedri_section(path: Path) -> None:
    """One-time migration for party pages: remove the write-once hand
    '## Biedri' section so the sync-block version doesn't duplicate it.
    Manual content in other sections is preserved verbatim."""
    global _LEGACY_BIEDRI_RE
    if not path.exists():
        return
    if _LEGACY_BIEDRI_RE is None:
        _LEGACY_BIEDRI_RE = re.compile(
            r"^## Biedri[ \t]*\n(?:(?!^## |^<!-- SYNC-AUTO -->).*\n?)*",
            re.MULTILINE,
        )
    text = path.read_text(encoding="utf-8")
    start = text.find(_SYNC_START)
    head, tail = (text, "") if start == -1 else (text[:start], text[start:])
    new_head = _LEGACY_BIEDRI_RE.sub("", head)
    if new_head != head:
        path.write_text(new_head + tail, encoding="utf-8")

_BILLS_SYNC_START = "<!-- BILLS-SYNC-AUTO -->"
_BILLS_SYNC_END = "<!-- /BILLS-SYNC-AUTO -->"


def _render_law_bills_block(slug: str, db: sqlite3.Connection, md_path: Path) -> bool:
    """Atjauno BILLS-SYNC-AUTO bloku wiki/laws/<slug>.md failā.

    Returns True ja saturs faktiski mainījies (False = idempotents, fails nav skarts).
    """
    rows = db.execute("""
        SELECT document_nr, title, current_stage, current_status, last_updated_at
        FROM saeima_bills
        WHERE base_law_slug = ?
        ORDER BY last_updated_at DESC, id DESC
    """, (slug,)).fetchall()

    if rows:
        lines = [
            _BILLS_SYNC_START,
            "## Aktuālie likumprojekti šajā likumā",
            "",
            "| Bill nr | Nosaukums | Stadija | Datums |",
            "|---|---|---|---|",
        ]
        for r in rows:
            doc_slug = r["document_nr"].lower().replace("/", "-")
            stage_with_status = r["current_stage"] or ""
            if r["current_status"]:
                stage_with_status += f" ({r['current_status']})"
            date = (r["last_updated_at"] or "")[:10]
            lines.append(
                f"| [{r['document_nr']}](/likumprojekti/{doc_slug}.html) | {r['title']} | {stage_with_status} | {date} |"
            )
        lines.append(_BILLS_SYNC_END)
    else:
        lines = [
            _BILLS_SYNC_START,
            "## Aktuālie likumprojekti šajā likumā",
            "",
            "_Šajā likumā šobrīd nav aktīvu likumprojektu Saeimā._",
            _BILLS_SYNC_END,
        ]
    new_block = "\n".join(lines)

    if not md_path.exists():
        return False

    content = md_path.read_text(encoding="utf-8")

    if _BILLS_SYNC_START in content and _BILLS_SYNC_END in content:
        # Replace existing block
        before, _, rest = content.partition(_BILLS_SYNC_START)
        _, _, after = rest.partition(_BILLS_SYNC_END)
        new_content = before + new_block + after
    else:
        # Append at end with newline separation
        new_content = content.rstrip() + "\n\n" + new_block + "\n"

    if new_content == content:
        return False

    md_path.write_text(new_content, encoding="utf-8")
    return True


def _update_page_with_sync_block(
    path: Path,
    new_frontmatter: dict,
    sync_block: str,
) -> None:
    """Create or update a wiki page with a sync-marked auto block.

    Behavior:
      - Frontmatter is always replaced by `new_frontmatter`.
      - Any existing content between SYNC markers is replaced by `sync_block`
        (or removed entirely if `sync_block` is empty).
      - Manual body content outside the markers is preserved verbatim.
      - If page is new and `sync_block` is non-empty: creates frontmatter +
        markers + sync_block. If empty: creates frontmatter only.
      - If page exists without markers and `sync_block` is non-empty: appends
        markers + sync_block to end of body (manual content above).
    """
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        _old_fm, body = _parse_frontmatter(existing)
        body = _sanitize_body(body)
    else:
        body = ""

    # Strip any existing sync block from the body.
    body = _strip_sync_block(body)

    # Rebuild body: manual content + (optional) new sync block.
    if sync_block.strip():
        block_text = f"{_SYNC_START}\n{sync_block.rstrip()}\n{_SYNC_END}\n"
        if body.strip():
            body = body.rstrip() + "\n\n" + block_text
        else:
            body = block_text

    content = _render_frontmatter(new_frontmatter)
    if body:
        content += "\n" + body

    path.write_text(content, encoding="utf-8")


def _strip_sync_block(body: str) -> str:
    """Remove the SYNC-AUTO markers and their content from `body`.

    If no markers present, returns `body` unchanged. If multiple marker pairs
    exist (should not happen in practice), removes only the first pair and
    leaves subsequent markers intact — a follow-up sync call will re-normalize.
    """
    start_idx = body.find(_SYNC_START)
    if start_idx == -1:
        return body
    end_marker_idx = body.find(_SYNC_END, start_idx)
    if end_marker_idx == -1:
        # Malformed: start without end. Leave body untouched so operator can fix manually.
        return body
    end_idx = end_marker_idx + len(_SYNC_END)
    # Also consume one trailing newline if present.
    if end_idx < len(body) and body[end_idx] == "\n":
        end_idx += 1
    before = body[:start_idx].rstrip()
    after = body[end_idx:].lstrip()
    if before and after:
        return before + "\n\n" + after
    return before or after
