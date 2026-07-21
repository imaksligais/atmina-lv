"""Pillar-specific text templates (≤280 chars)."""
from __future__ import annotations

MAX_LEN = 280
ELLIPSIS = "…"

# Mirrors CATEGORY_LV in src.generate — duplicated here to avoid a circular import.
_CATEGORY_SUBTITLE = {
    ("position", "position"): "pozīcijas maiņa",
    ("position", "saeima_vote"): "vārdi vs. darbi",
    ("saeima_vote", "saeima_vote"): "balsojuma maiņa",
}


def _shorten(s: str, budget: int) -> str:
    if len(s) <= budget:
        return s
    if budget <= 1:
        return ELLIPSIS
    return s[: budget - 1].rstrip() + ELLIPSIS


def _category_subtitle(old_ct: str | None, new_ct: str | None) -> str:
    key = tuple(sorted([old_ct or "position", new_ct or "position"]))
    return _CATEGORY_SUBTITLE.get(key, "pretruna")


def draft_pretrunas(row: dict) -> str:
    """Generate a ≤280-char pretrunas draft aligned with atmina.lv framing.

    Contract: the caller (candidates.fetch_pretrunas_candidates) is expected
    to hand over the row already sorted chronologically — old_* = earlier,
    new_* = later.

    Layout:
        {name} — {category} par {topic}.

        {old_date}: {old_line}
        {new_date}: {new_line}

        atmina.lv/pretrunas/{id}.html
    """
    name = row["politician_name"]
    topic = row["topic"]
    cid = row["contradiction_id"]
    old_ct = row.get("old_claim_type") or "position"
    new_ct = row.get("new_claim_type") or "position"

    # Prefer quote; fall back to stance paraphrase.
    old_text = row.get("old_quote") or row.get("old_stance") or ""
    new_text = row.get("new_quote") or row.get("new_stance") or ""
    old_d = (row.get("old_stated_at") or "")[:10]
    new_d = (row.get("new_stated_at") or "")[:10]

    subtitle = _category_subtitle(old_ct, new_ct)
    # Topic names are DB-canonical (nominative form) — joining with "par" would
    # require proper Latvian declension per topic, which we don't have. A bullet
    # separator keeps both labels grammatically neutral.
    header = f"{name} — {subtitle} · {topic}\n\n"
    link = f"atmina.lv/pretrunas/{cid}.html"
    footer = f"\n\n{link}"

    prefix_old = f"{old_d}: "
    prefix_new = f"{new_d}: "
    # Quote wrapping only for verbatim quotes (presence-check) — keeps
    # paraphrased stances unquoted per house style (see social-agent.md).
    wrap_old = row.get("old_quote") is not None and row.get("old_quote") != ""
    wrap_new = row.get("new_quote") is not None and row.get("new_quote") != ""
    quote_overhead = (2 if wrap_old else 0) + (2 if wrap_new else 0)

    budget = MAX_LEN - len(header) - len(footer) - len(prefix_old) - len(prefix_new) - 1 - quote_overhead
    half = max(20, budget // 2)
    old_short = _shorten(old_text, half)
    remaining = budget - len(old_short)
    new_short = _shorten(new_text, remaining)

    old_line = f'"{old_short}"' if wrap_old else old_short
    new_line = f'"{new_short}"' if wrap_new else new_short

    text = f"{header}{prefix_old}{old_line}\n{prefix_new}{new_line}{footer}"
    return text[:MAX_LEN]


def draft_stats(payload: dict) -> str:
    """Generate the weekly leaderboard draft."""
    board = payload["leaderboard"][:3]
    lines = ["Aktīvākie deputāti šonedēļ:"]
    for i, entry in enumerate(board, start=1):
        lines.append(f"{i}. {entry['name']} — {entry['count']} pozīcijas")
    lines.append("")
    lines.append("Kas klusē? Skaties pilno sarakstu:")
    lines.append("atmina.lv/statistika")

    text = "\n".join(lines)
    # Budget guard — shouldn't trigger in practice with top-3 names
    if len(text) > MAX_LEN:
        text = text[: MAX_LEN - 1] + ELLIPSIS
    return text


def draft_highlight(row: dict) -> str:
    """Dispatch to attack or tension sub-renderer."""
    kind = row.get("kind")
    if kind == "attack":
        return _draft_attack(row)
    if kind == "tension":
        return _draft_tension(row)
    raise ValueError(f"Unknown highlight kind: {kind!r}")


def _draft_attack(row: dict) -> str:
    name = row["politician_name"]
    slug = row.get("slug") or ""
    body = row["text"]
    link = f"atmina.lv/{slug}".rstrip("/")
    static = f"\n\nPar ko runā atmina.lv: {link}"
    budget = MAX_LEN - len(static)
    body_short = _shorten(body, budget)
    return f"{body_short}{static}"


def _draft_tension(row: dict) -> str:
    src = row["source_name"]
    tgt = row["target_name"]
    topic = row["topic"]
    desc = row["description"]
    static = f"\n\n{src} ⇄ {tgt} — {topic}\natmina.lv/spriedzes"
    budget = MAX_LEN - len(static)
    desc_short = _shorten(desc, budget)
    return f"{desc_short}{static}"
