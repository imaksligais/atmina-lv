#!/usr/bin/env python
"""LV stila lints analīzes/atraduma md failam (`content/analizes/*.md`).

Lietošana:
    .venv/Scripts/python.exe scripts/lint_analysis.py content/analizes/<slug>.md

Laiž `src.lv_style.lint_lv_style_report()` pār MŪSU tekstu: frontmatter un
«…» citāti blockquote rindās tiek izņemti (citāti ir verbatim, CLAUDE.md
§ Grammar gate); `ol-trap` netiek skaitīts īstā numurētā sarakstā (≥2
rindas pēc kārtas, no `1.`, katra +1). Izdrukā problēmas un abus saucējus.
Izejas kods: 1 = ir problēmas; 2 = problēmu nav, bet kāds likums neskrēja
(piem., nav DB uzvārdu) — tas nav «tīrs», tas ir «neskatījos»; 0 = tīrs.
"""

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.lv_style import lint_lv_style_report  # noqa: E402

_FRONTMATTER = re.compile(r"\A---\n.*?\n---\n", re.DOTALL)
_QUOTE = re.compile(r"«[^»]*»")
_OL_LINE = re.compile(r"^\s*(\d+)\.\s")


def our_text(md: str) -> str:
    """Bez frontmatter; blockquote rindās bez «…» citātiem (rindu skaits paliek)."""
    m = _FRONTMATTER.match(md)
    if m:
        md = "\n" * m.group(0).count("\n") + md[m.end():]
    return "\n".join(
        _QUOTE.sub("«»", line) if line.lstrip().startswith(">") else line
        for line in md.split("\n"))


def mask_real_lists(text: str) -> tuple[str, int]:
    """Īstā numurētā sarakstā (≥2 rindas pēc kārtas, sākas ar `1.`, katra +1)
    numuru aizstāj ar `-`, lai ol-trap to neskaitītu. Analīzē tas ir apzināts
    saraksts; «12. martā…» / «15. martā…» nav — tie paliek un krīt."""
    lines = text.split("\n")
    nums = [int(m.group(1)) if (m := _OL_LINE.match(ln)) else None for ln in lines]
    masked = 0
    i = 0
    while i < len(lines):
        j = i
        while j < len(lines) and nums[j] == j - i + 1:
            j += 1
        if j - i >= 2:
            for k in range(i, j):
                m = _OL_LINE.match(lines[k])
                lines[k] = lines[k][:m.start(1)] + "-" + lines[k][m.end(1) + 1:]
            masked += j - i
        i = max(j, i + 1)
    return "\n".join(lines), masked


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("md", type=Path)
    args = ap.parse_args()
    text = our_text(args.md.read_text(encoding="utf-8").replace("\r\n", "\n"))
    text, masked = mask_real_lists(text)
    r = lint_lv_style_report(text)
    issues = r["issues"]
    for i in issues:
        print(f"- {i['rule']}: {i['context']!r} → {i['suggestion']}")
    print(f"{args.md}: problēmas {len(issues)} (numurēta saraksta rindas: "
          f"{masked}); teksts {r['scanned_chars']}/"
          f"{r['total_chars']} zīmes ({r['coverage_pct']} %), proza "
          f"{r['prose_scanned_chars']}; likumi {r['rules_run']}/{r['rules_total']}")
    for skip in r["rules_skipped"]:
        print(f"BRĪDINĀJUMS: likums {skip['rule']} neskrēja — {skip['reason']}")
    if issues:
        return 1
    if r["rules_run"] < r["rules_total"]:
        print(f"Izejas kods 2: skrēja tikai {r['rules_run']}/{r['rules_total']} "
              "likumi — vārti nav pilni (palaid ar īsto DB).")
        return 2
    return 0

if __name__ == "__main__":
    sys.exit(main())
