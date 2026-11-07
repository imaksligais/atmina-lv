"""Generate the solījumu-matrica widget from the program-promise claims.

Read-only over ``data/atmina.db``: builds a topic × party coverage matrix from
``claims WHERE claim_type='program_promise'`` and writes a self-contained HTML
fragment to the synthesis widget dir. Filled cell = a link to the party page's
``#programma`` section; empty cell = a muted middot.

  python scripts/build_solijumu_matrica.py

Rows    = topics, ordered by coverage (party count) desc, then topic alpha.
Columns = the 14 lists, ordered by promise count desc (ties alpha by short_name),
          matching the synthesis "Konteksts" table order.
Party page path follows src/render/parties.py: ``<short_name>.lower().html``.

Regenerate manually when programs change; the output carries a "do not hand-edit"
header. This script only SELECTs — no mutation, no rollback needed.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "atmina.db"
OUT = (
    ROOT
    / "wiki"
    / "synthesis"
    / "widgets"
    / "partiju-programmas-2026-solijumu-karte"
    / "solijumu-matrica.html"
)


def _esc(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _party_href(short_name: str) -> str:
    # Mirror src/render/parties.py: partijas/<short_name>.lower().html
    return f"../partijas/{short_name.lower()}.html#programma"


def main() -> int:
    if not DB_PATH.exists():
        print(f"DB not found: {DB_PATH}", file=sys.stderr)
        return 1

    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row

    # Columns: parties with program promises, by promise count desc, alpha tie.
    parties = db.execute(
        """
        SELECT p.id, p.short_name, p.name, COUNT(cl.id) AS n
        FROM parties p
        JOIN claims cl ON cl.party_id = p.id AND cl.claim_type = 'program_promise'
        GROUP BY p.id
        ORDER BY n DESC, p.short_name
        """
    ).fetchall()

    # Filled cells: (topic, party_id) pairs.
    pairs = db.execute(
        """
        SELECT DISTINCT topic, party_id
        FROM claims
        WHERE claim_type = 'program_promise' AND party_id IS NOT NULL
        """
    ).fetchall()
    db.close()

    filled: set[tuple[str, int]] = {(r["topic"], r["party_id"]) for r in pairs}

    # Rows: topics by coverage (distinct party count) desc, then topic alpha.
    coverage: dict[str, int] = {}
    for topic, _pid in filled:
        coverage[topic] = coverage.get(topic, 0) + 1
    topics = sorted(coverage, key=lambda t: (-coverage[t], t))

    total_cells = len(filled)

    # --- Render ---------------------------------------------------------
    lines: list[str] = []
    lines.append(
        "<!-- ĢENERĒTS ar scripts/build_solijumu_matrica.py — nerediģēt ar roku. -->"
    )
    lines.append('<div class="syn-w">')
    lines.append(
        '  <p class="syn-w-title">Karte: kurš saraksts par kuru tēmu runā '
        "· aizpildīta šūna = saite uz programmu</p>"
    )
    # `table-scroll` alongside the widget class so _wrap_tables
    # (src/render/syntheses.py) treats this table as already wrapped and
    # doesn't nest a second scroll container (that would break sticky).
    lines.append('  <div class="table-scroll syn-matrix-scroll">')
    lines.append('    <table class="syn-matrix">')

    # Header
    lines.append("      <thead>")
    lines.append("        <tr>")
    lines.append('          <th class="syn-matrix-topic" scope="col">Tēma</th>')
    for p in parties:
        lines.append(
            f'          <th scope="col" title="{_esc(p["name"])}">'
            f"{_esc(p['short_name'])}</th>"
        )
    lines.append("        </tr>")
    lines.append("      </thead>")

    # Body
    lines.append("      <tbody>")
    for topic in topics:
        lines.append("        <tr>")
        lines.append(
            f'          <th class="syn-matrix-topic" scope="row">{_esc(topic)}</th>'
        )
        for p in parties:
            if (topic, p["id"]) in filled:
                href = _party_href(p["short_name"])
                title = _esc(f"{p['short_name']}: {topic}")
                lines.append(
                    f'          <td><a class="syn-matrix-cell-on" href="{href}" '
                    f'title="{title}">●</a></td>'
                )
            else:
                lines.append('          <td><span class="syn-matrix-cell-off">·</span></td>')
        lines.append("        </tr>")
    lines.append("      </tbody>")

    lines.append("    </table>")
    lines.append("  </div>")
    lines.append(
        f'  <p class="syn-matrix-caption">{len(topics)} tēmas '
        f"× {len(parties)} saraksti · {total_cells} pozīcijas. "
        "Ritini tabulu, lai redzētu visus sarakstus.</p>"
    )
    lines.append("</div>")

    html = "\n".join(lines) + "\n"
    OUT.write_text(html, encoding="utf-8")

    print(f"Wrote {OUT}")
    print(f"rows (topics)   = {len(topics)}")
    print(f"cols (parties)  = {len(parties)}")
    print(f"filled cells    = {total_cells}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
