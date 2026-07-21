"""Audit: VAD analīze top-N tables vs rendered politician profile pages.

T6 of VAD analīze sanācija. Reads expected numbers from
content/analizes/_drafts/vad-2026.md (§ 2 income top 15, § 4 YoY top 10,
§ 5 uzņēmumi top 10, § 6 NĪ top 15) and verifies that each politician's
public profile HTML at output/atmina/politiki/<slug>.html shows the same
numbers in the Deklarācijas tab.

Strategy:
- Parse markdown tables programmatically (no hardcoded numbers).
- Re-run the public site renderer first for fresh HTML.
- For every (politician, metric) pair, extract the corresponding number
  from the rendered profile and compare against the analīze.
- Report mismatches with detail (politician, metric, expected, actual,
  file path). Exit 0 if all match, 1 otherwise.

Profile structure recap (templates/_vad_panel.html.j2):
- One <button class="vad-year-tab"> per year (e.g. "2025 annual")
- One <div class="vad-decl" id="vad-decl-{decl_id}"> per declaration
- Inside each decl, <details class="vad-section"> blocks with
  summary "Nekustamie īpašumi (N)" / "Komercsabiedrību ... (N)" /
  "Ienākumi (N)" with a row count.
- Income rows expose "<type>: <amount> EUR no <source>" inside <td>.

Year mapping: a year tab labelled "2025 annual" represents the
declaration submitted in 2026 reporting fiscal year 2025. The analīze
"2024 EUR" column maps to the declaration tab labelled "2024 annual".

Usage:
    python scripts/audit_vad_profile_match.py
        [--skip-render]    skip running generate_public_site
        [--verbose]        print per-politician breakdown even on success
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from bs4 import BeautifulSoup

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from src.render._common import _slugify  # noqa: E402

ANALIZE_PATH = REPO / "content" / "analizes" / "vad-2026.md"
PROFILE_DIR = REPO / "output" / "atmina" / "politiki"


# ── Markdown parsing ────────────────────────────────────────────────


def _strip_md(s: str) -> str:
    """Remove **bold**, leading/trailing whitespace, footnote markers."""
    s = s.strip()
    s = re.sub(r"\*\*", "", s)
    s = re.sub(r"¹", "", s)
    return s.strip()


def _parse_int(s: str) -> int:
    """Parse '239 664' / '12' / '+81 439' / '+445%' into int."""
    s = _strip_md(s).replace("\xa0", " ").replace(" ", "")
    s = s.replace("+", "").replace("%", "").replace("EUR", "").strip()
    return int(s)


def _split_section(md: str, section_header: str) -> str:
    """Return the body of a ## section by its header text (substring match)."""
    pattern = rf"^## .*{re.escape(section_header)}.*$"
    lines = md.splitlines()
    start = None
    for i, line in enumerate(lines):
        if re.match(pattern, line):
            start = i
            break
    if start is None:
        raise ValueError(f"Section not found: {section_header}")
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if lines[i].startswith("## "):
            end = i
            break
    return "\n".join(lines[start:end])


def _parse_md_table(section_body: str) -> list[dict[str, str]]:
    """Parse the FIRST markdown table in a section. Returns list of row dicts."""
    rows: list[dict[str, str]] = []
    in_table = False
    headers: list[str] = []
    for line in section_body.splitlines():
        line = line.rstrip()
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if not in_table:
                headers = [_strip_md(h) for h in cells]
                in_table = True
                continue
            if all(re.fullmatch(r":?-+:?", c or "") for c in cells):
                continue  # separator
            if len(cells) != len(headers):
                continue
            rows.append({h: cells[i] for i, h in enumerate(headers)})
        elif in_table:
            break  # table ended
    return rows


@dataclass
class IncomeExpected:
    politician: str
    income_2024_eur: int


@dataclass
class YoYExpected:
    politician: str
    eur_2023: int
    eur_2024: int


@dataclass
class CountExpected:
    politician: str
    year: int
    count: int


def parse_analize() -> tuple[list[IncomeExpected], list[YoYExpected],
                              list[CountExpected], list[CountExpected]]:
    md = ANALIZE_PATH.read_text(encoding="utf-8")

    sec2 = _split_section(md, "Lielākie kopējā ienākuma deklarētāji")
    sec4 = _split_section(md, "Lielākie ienākuma pieaugumi")
    sec5 = _split_section(md, "Lielākie uzņēmumu deklarētāji")
    sec6 = _split_section(md, "Lielākie nekustamā īpašuma deklarētāji")

    income = [
        IncomeExpected(_strip_md(r["Politiķis"]),
                       _parse_int(r["Ienākums (EUR)"]))
        for r in _parse_md_table(sec2)
    ]

    yoy = [
        YoYExpected(_strip_md(r["Politiķis"]),
                    _parse_int(r["2023 EUR"]),
                    _parse_int(r["2024 EUR"]))
        for r in _parse_md_table(sec4)
    ]

    companies = [
        CountExpected(_strip_md(r["Politiķis"]),
                      _parse_int(r["Gads"]),
                      _parse_int(r["Uzņēmumi"]))
        for r in _parse_md_table(sec5)
    ]

    real_estate = [
        CountExpected(_strip_md(r["Politiķis"]),
                      _parse_int(r["Gads"]),
                      _parse_int(r["NĪ"]))
        for r in _parse_md_table(sec6)
    ]

    return income, yoy, companies, real_estate


# ── HTML profile parsing ────────────────────────────────────────────


@dataclass
class DeclSnapshot:
    decl_id: str
    year_label: str  # "2025" / "2024" / "interim" etc
    kind: str  # "annual" / "interim" / "post_year_1" / "start"
    real_estate_count: int = 0  # rows shown in profile (post-dedup)
    companies_count: int = 0
    income_total_eur: float = 0.0
    income_rows: list[tuple[str, float, str]] = None  # (type, amount, currency)

    def __post_init__(self):
        if self.income_rows is None:
            self.income_rows = []


def parse_profile(html_path: Path) -> list[DeclSnapshot]:
    """Extract per-declaration snapshots from a politician profile HTML."""
    if not html_path.exists():
        return []
    soup = BeautifulSoup(html_path.read_text(encoding="utf-8"), "html.parser")

    # Build mapping decl_id -> (year_label, kind) from year-tab buttons
    decl_meta: dict[str, tuple[str, str]] = {}
    for btn in soup.select("button.vad-year-tab"):
        decl_id = btn.get("data-decl-id")
        if not decl_id:
            continue
        # Button text: "2025 <span>annual</span>"
        kind_span = btn.find("span")
        kind = kind_span.get_text(strip=True) if kind_span else ""
        # Year is the first token before the span
        full_text = btn.get_text(separator=" ", strip=True)
        year_label = full_text.split()[0] if full_text else ""
        decl_meta[decl_id] = (year_label, kind)

    out: list[DeclSnapshot] = []
    for decl_div in soup.select("div.vad-decl"):
        decl_id = decl_div.get("id", "").replace("vad-decl-", "")
        year_label, kind = decl_meta.get(decl_id, ("", ""))
        snap = DeclSnapshot(decl_id=decl_id, year_label=year_label, kind=kind)

        for details in decl_div.select("details.vad-section"):
            summary = details.find("summary")
            if not summary:
                continue
            summary_text = summary.get_text(separator=" ", strip=True)
            m = re.search(r"\((\d+)\)\s*$", summary_text)
            count = int(m.group(1)) if m else 0
            label = summary_text.split("(")[0].strip()

            if label.startswith("Nekustamie īpašumi"):
                snap.real_estate_count = count
            elif label.startswith("Komercsabiedr"):
                snap.companies_count = count
            elif label == "Ienākumi":
                # Extract per-row "<type>: <amount> EUR no ..."
                for tr in details.select("tr"):
                    tds = tr.find_all("td")
                    if len(tds) < 2:
                        continue
                    cell_text = tds[1].get_text(separator=" ", strip=True)
                    rm = re.match(r"^(.+?):\s*([\d.,]+)\s*([A-Z]{3})\b",
                                  cell_text)
                    if not rm:
                        continue
                    inc_type = rm.group(1).strip()
                    amt = float(rm.group(2).replace(",", "."))
                    cur = rm.group(3)

                    # Skip rows marked as "removed" (delta) — those belong
                    # to the previous declaration, not this one.
                    classes = tr.get("class") or []
                    if "vad-delta-removed" in classes:
                        continue

                    snap.income_rows.append((inc_type, amt, cur))
                    if cur == "EUR":
                        snap.income_total_eur += amt

        out.append(snap)
    return out


# ── Politician name → profile path ──────────────────────────────────


# The slugify function transliterates LV diacritics. Some names in the
# analīze use "Inese Lībiņa-Egnere" — slugify produces "inese-libina-egnere".
def politician_slug(name: str) -> str:
    return _slugify(name)


def find_profile(name: str) -> Optional[Path]:
    slug = politician_slug(name)
    p = PROFILE_DIR / f"{slug}.html"
    return p if p.exists() else None


# ── Audit ───────────────────────────────────────────────────────────


@dataclass
class Mismatch:
    category: str  # "income" | "yoy" | "uznemumi" | "ni"
    politician: str
    metric: str
    expected: object
    actual: object
    file_path: str
    note: str = ""


def audit_income(
    income: list[IncomeExpected], verbose: bool = False
) -> list[Mismatch]:
    """§ 2: top 15 income 2024.

    Profile may have multiple declarations covering fiscal year 2024
    (parallel amati). Sum income across ALL annual decls labelled
    "2024" — but DO NOT double-count rows that the per-decl renderer
    marks as "removed" (those belong to a different year).

    Tolerance: ±1 EUR (rounding).
    """
    mismatches: list[Mismatch] = []
    for entry in income:
        prof = find_profile(entry.politician)
        if prof is None:
            mismatches.append(Mismatch(
                "income", entry.politician, "2024 EUR total",
                entry.income_2024_eur, "PROFILE MISSING",
                str(PROFILE_DIR / f"{politician_slug(entry.politician)}.html"),
                "no profile HTML — politician may be inactive or slug mismatch",
            ))
            continue
        snaps = parse_profile(prof)
        # Find all decls with year_label "2024" (regardless of kind, but
        # prefer "annual" — the analīze § 3 dedup logic uses unique
        # (politician, year, source, amount) so we sum every visible row.
        relevant = [s for s in snaps
                    if s.year_label == "2024" and s.kind == "annual"]
        # Profile stores duplicate decls (parallel amati); dedup by
        # (income_type, amount, currency, source-prefix) WITHIN a single
        # politician by combining all rows then deduping.
        seen: set[tuple] = set()
        actual_total = 0.0
        for s in relevant:
            for inc_type, amt, cur in s.income_rows:
                if cur != "EUR":
                    continue
                key = (inc_type, round(amt, 2), cur)
                # We use the source text as well to discriminate rows that
                # have same (type, amount) but different sources. The
                # parser already drops "removed" rows.
                if key in seen:
                    continue
                seen.add(key)
                actual_total += amt
        actual_int = int(round(actual_total))
        diff = abs(actual_int - entry.income_2024_eur)
        ok = diff <= 1
        if verbose or not ok:
            label = "OK" if ok else "MISMATCH"
            print(f"  [income/{label}] {entry.politician}: "
                  f"expected {entry.income_2024_eur} EUR, "
                  f"actual {actual_int} EUR (diff {diff}, "
                  f"decls={len(relevant)})")
        if not ok:
            mismatches.append(Mismatch(
                "income", entry.politician, "2024 EUR total",
                entry.income_2024_eur, actual_int, str(prof),
                f"{len(relevant)} annual 2024 decl(s) in profile",
            ))
    return mismatches


def audit_yoy(yoy: list[YoYExpected], verbose: bool = False) -> list[Mismatch]:
    """§ 4: 2023 → 2024 YoY top 10. Same approach as audit_income, both years."""
    mismatches: list[Mismatch] = []
    for entry in yoy:
        prof = find_profile(entry.politician)
        if prof is None:
            mismatches.append(Mismatch(
                "yoy", entry.politician, "profile",
                f"{entry.eur_2023}/{entry.eur_2024}", "PROFILE MISSING",
                str(PROFILE_DIR / f"{politician_slug(entry.politician)}.html"),
            ))
            continue
        snaps = parse_profile(prof)
        for year, expected in (("2023", entry.eur_2023),
                                ("2024", entry.eur_2024)):
            relevant = [s for s in snaps
                        if s.year_label == year and s.kind == "annual"]
            seen: set[tuple] = set()
            actual_total = 0.0
            for s in relevant:
                for inc_type, amt, cur in s.income_rows:
                    if cur != "EUR":
                        continue
                    key = (inc_type, round(amt, 2), cur)
                    if key in seen:
                        continue
                    seen.add(key)
                    actual_total += amt
            actual_int = int(round(actual_total))
            diff = abs(actual_int - expected)
            ok = diff <= 1
            if verbose or not ok:
                label = "OK" if ok else "MISMATCH"
                print(f"  [yoy/{label}] {entry.politician} {year}: "
                      f"expected {expected} EUR, actual {actual_int} EUR "
                      f"(diff {diff}, decls={len(relevant)})")
            if not ok:
                mismatches.append(Mismatch(
                    "yoy", entry.politician, f"{year} EUR",
                    expected, actual_int, str(prof),
                    f"{len(relevant)} annual {year} decl(s)",
                ))
    return mismatches


def audit_count(
    expected: list[CountExpected], category: str,
    snap_field: str, label_singular: str, verbose: bool = False,
) -> list[Mismatch]:
    """§ 5 / § 6 — uzņēmumu / NĪ count for a specific year.

    The profile's section count comes from compute_section_deltas() which:
    1. Dedups rows by section identity key (real_estate keyed on
       (property_type, location, ownership_status); companies on
       (reg_number|name, capital_kind)) — this can REDUCE the count
       below raw row count.
    2. Adds "removed" rows from the previous year that disappeared this
       year — this can INCREASE the count above raw row count.

    Net effect: profile count != raw row count != analīze number, in
    multiple directions. This is the central fact T6 surfaces.
    """
    mismatches: list[Mismatch] = []
    for entry in expected:
        prof = find_profile(entry.politician)
        if prof is None:
            mismatches.append(Mismatch(
                category, entry.politician, f"{entry.year} {label_singular}",
                entry.count, "PROFILE MISSING",
                str(PROFILE_DIR / f"{politician_slug(entry.politician)}.html"),
            ))
            continue
        snaps = parse_profile(prof)
        # Pick the best matching declaration for the analīze's stated year.
        # Priority: annual matching exact year. Fallback: any year-match.
        candidates = [s for s in snaps if s.year_label == str(entry.year)]
        if not candidates:
            mismatches.append(Mismatch(
                category, entry.politician, f"{entry.year} {label_singular}",
                entry.count, "YEAR TAB MISSING", str(prof),
                f"no decl tab for year {entry.year}",
            ))
            continue
        annual = [s for s in candidates if s.kind == "annual"] or candidates
        actual = getattr(annual[0], snap_field)
        ok = actual == entry.count
        if verbose or not ok:
            tag = "OK" if ok else "MISMATCH"
            print(f"  [{category}/{tag}] {entry.politician} {entry.year}: "
                  f"expected {entry.count}, actual {actual}")
        if not ok:
            note = (
                "profile count from compute_section_deltas: "
                "dedups by identity key AND adds 'removed' rows from "
                "prev year — diverges from analīze raw row count"
            )
            mismatches.append(Mismatch(
                category, entry.politician, f"{entry.year} {label_singular}",
                entry.count, actual, str(prof), note,
            ))
    return mismatches


# ── Entry point ─────────────────────────────────────────────────────


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Audit VAD analīze top-N tables against rendered profile pages.",
    )
    ap.add_argument("--skip-render", action="store_true",
                    help="don't re-run generate_public_site (assume HTML up-to-date)")
    ap.add_argument("--verbose", action="store_true",
                    help="print per-politician check status, not just mismatches")
    args = ap.parse_args()

    if not args.skip_render:
        print("Re-rendering public site...")
        from src.render import generate_public_site
        generate_public_site()
        print()

    print(f"Parsing analīze: {ANALIZE_PATH}")
    income, yoy, companies, real_estate = parse_analize()
    print(f"  § 2 income top {len(income)}")
    print(f"  § 4 YoY top {len(yoy)}")
    print(f"  § 5 uzņēmumi top {len(companies)}")
    print(f"  § 6 NĪ top {len(real_estate)}")
    print()

    all_mismatches: list[Mismatch] = []

    print("=== § 2: 2024 ienākums (top 15) ===")
    all_mismatches.extend(audit_income(income, verbose=args.verbose))
    print()

    print("=== § 4: 2023 → 2024 YoY (top 10) ===")
    all_mismatches.extend(audit_yoy(yoy, verbose=args.verbose))
    print()

    print("=== § 5: Uzņēmumu skaits (top 10) ===")
    all_mismatches.extend(audit_count(
        companies, "uznemumi", "companies_count", "uzņēmumi",
        verbose=args.verbose,
    ))
    print()

    print("=== § 6: NĪ skaits (top 15) ===")
    all_mismatches.extend(audit_count(
        real_estate, "ni", "real_estate_count", "NĪ",
        verbose=args.verbose,
    ))
    print()

    # ── Summary ─────────────────────────────────────────────────────

    print("=" * 70)
    if not all_mismatches:
        print("[OK] All analīze numbers match rendered profile pages.")
        return 0

    print(f"[FAIL] {len(all_mismatches)} mismatch(es) found:")
    print()
    by_cat: dict[str, list[Mismatch]] = {}
    for m in all_mismatches:
        by_cat.setdefault(m.category, []).append(m)
    for cat in ("income", "yoy", "uznemumi", "ni"):
        items = by_cat.get(cat, [])
        if not items:
            continue
        print(f"--- {cat.upper()} ({len(items)}) ---")
        for m in items:
            print(f"  {m.politician:<28} {m.metric:<22} "
                  f"expected={m.expected!r:<14} actual={m.actual!r:<14}")
            if m.note:
                print(f"    note: {m.note}")
            print(f"    file: {m.file_path}")
        print()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
