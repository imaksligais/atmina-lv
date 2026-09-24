"""Rank top-N politicians by profile-style VAD counts.

Reads /tmp/vad_counts.tsv (or stdin) and prints top-N for each section.
"""

from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

# party abbreviations from existing analīze table — pre-defined map for known politicians
PARTY_ABBREV = {
    "Zaļo un Zemnieku savienība": "ZZS",
    "Jaunā Vienotība": "JV",
    "Nacionālā apvienība": "NA",
    "Progresīvie": "PRO",
    "Apvienotais saraksts": "AS",
    "Latvija Pirmajā Vietā": "LPV",
    "Stabilitātei!": "Stab",
    "Bezpartejisks": "Bezp",
    "Mums Mēs Nepiedosim": "MMN",
    "ASL": "ASL",
    "JKP": "JKP",
    "Kopā Latvijai": "KL",
    "Saskaņa": "Sask",
}


def short_party(p: str) -> str:
    return PARTY_ABBREV.get(p, p)


def main() -> None:
    src = sys.argv[1] if len(sys.argv) > 1 else "tmp_vad_counts.tsv"
    rows = []
    with open(src, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for r in reader:
            r["count"] = int(r["count"])
            r["year"] = int(r["year"])
            rows.append(r)

    # Group by section
    by_section: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_section[r["section"]].append(r)

    # Tie-break by surname (last token of name), alphabetical
    def sort_key(r):
        surname = r["name"].split()[-1] if r["name"] else ""
        return (-r["count"], surname)

    # Top-10 companies (uznemumi), top-15 real estate
    print("--- TOP 10 KOMERCSABIEDRĪBAS ---")
    companies = sorted(by_section["companies"], key=sort_key)
    for i, r in enumerate(companies[:10], 1):
        print(f"| {i} | {r['name']} | {short_party(r['party'])} | {r['year']} | {r['count']} |")

    print()
    print("--- TOP 15 NEKUSTAMIE ĪPAŠUMI ---")
    re = sorted(by_section["real_estate"], key=sort_key)
    for i, r in enumerate(re[:15], 1):
        print(f"| {i} | {r['name']} | {short_party(r['party'])} | {r['year']} | {r['count']} |")


if __name__ == "__main__":
    main()
