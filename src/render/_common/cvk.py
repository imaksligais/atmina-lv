"""CVK 15. Saeimas vēlēšanu datu failu lasītāji — kopīgi vairākām lapām.

`personas.html` (ievēlēto rails), `partijas.html` (rezultātu bloks) un
`saeima.html` (pusloks) lasa tos pašus divus YAML failus. Ceļa konstantes
paliek katrā lapas modulī (testi tās pārsien uz fixture kopijām); šeit dzīvo
tikai parsēšana, lai tā nebūtu dublēta.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def read_election_results(path: Path) -> dict[str, Any] | None:
    """`cvk_sv2026_rezultati.yaml` → dict. Nav faila vai nav sarakstu → None."""
    if not path.exists():
        return None
    doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return doc if doc.get("lists") else None


def read_elected(path: Path) -> list[dict[str, Any]]:
    """`cvk_sv2026_ievēlētie.yaml` → ievēlēto ierakstu saraksts (secība kā failā).

    Trūkstošs fails ir kļūda (FileNotFoundError), nevis tukšs saraksts —
    citādi lapa klusi rādītu «0 ievēlēto».
    """
    doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return list(doc.get("elected") or [])
