"""Seed homonīmu disambig hints + negative_patterns post-Phase-1.5.

VAD analīze sanācija — pēc 11-pid F13 sweep (sk. seed_vad_disambig.py)
audits atklāja papildu homonīmu kontaminācijas, kas paliek redzamas
pēc Saeimas-only ingest. Šis skripts ir kanonisks vairāku-pid CONFIGS
modelis: katra T1-T4 (un nākotnes) auditā atklātā V+U sajaukuma seedēšana
pievieno entry CONFIGS sarakstam.

Atšķirībā no seed_vad_disambig.py (Phase 1.5 F13 batch) un
seed_lidaka_disambig.py (single-pid commentary contamination), šis modelis
apvieno BOTH lauk-pārveides:

  - keywords.vad_disambig (substring whitelist VAD ingest filter)
  - negative_patterns (substring reject — gan VAD filter, gan matcher)

Idempotents — atkārtota palaišana producē identiskus UPDATE statements.

Usage:
    python scripts/seed_homonimu_disambig.py
    python scripts/seed_homonimu_disambig.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.db import get_db  # noqa: E402


@dataclass
class HomonymConfig:
    """Per-politician disambig konfigurācija.

    keywords/negative_patterns abi pielāgojas VAD ingest filter
    (src.vad.declarations._row_passes_disambig). negative_patterns
    arī ietekmē claim-extractor matcher (sk. seed_lidaka_disambig.py).
    """
    pid: int
    expected_name: str
    notes: str
    keywords: dict = field(default_factory=dict)        # JSON dict; .vad_disambig key parocīgs
    negative_patterns: list[str] = field(default_factory=list)  # substring reject list


# T1 — pid=81 Mārtiņš Daģis (Saeima JV b. 1976) homonīms ar Mārtiņš Daģis
# (Kustība Par! b. 1988, Jelgavas domes priekšsēdētājs since 2025-07-01).
# Audits: 22 VAD deklarācijas mixed; tikai institution="Latvijas Republikas
# Saeima" ir mūsu Daģa.
#
# T2 — pid=158 Agnese Lāce (Progresīvo Kultūras ministre b. 1987, pre-politics
# migrācijas pētniece — Providus 2016-2023, ANO Bēgļu aģentūra, EDSO Hāga;
# LU + Amsterdamas Univ.) homonīms ar Agnese Lāce, kas strādā Neatliekamās
# medicīniskās palīdzības dienestā (NMPD). Audits: 43 VAD rindas sajauktas
# starp vairākiem homonīmiem; mūsu Lāces patiesie ieraksti ir Saeimas
# deputāte (no 2022-11), Kultūras ministrijas parlamentārā sekretāre (2023)
# un Valsts kanceleja Ministrs (2024-, Kultūras ministre).
#
# T3 — pid=10 Andris Kulbergs (AS 14. Saeimas deputāts no 2022-11-01, b. 1979)
# pre-politikas karjerā auto-industrijas uzņēmējs (Lattelekom, Auto Torino,
# Auto Group Baltic, Inchcape līdz 2013; SIA "VK Development" valdes pr-tājs,
# Auto Asociācija, LDDK padomes loceklis). Audits: 27 VAD dekl sajauktas ar
# Valsts policijas inspektoru homonīmu (2002-2024 inspektora ieraksti). Mūsu
# Kulberga patiesie ieraksti ir Saeimas deputāts (2022-2025).
#
# T4 — pid=137 Jānis Vucāns (ZZS Saeimas deputāts no 2010, b. 1956,
# matemātiķis, Ventspils Augstskolas rektors 2000-2010, 14. Saeimā kopš
# 2022). Audits: 46 VAD dekl sajauktas ar Madonas Valsts policijas
# inspektora homonīmu (Inspektors/Vecākais inspektors 2005-2024). Mūsu
# Vucāna patiesie ieraksti ir Saeimas deputāts (2010-2025) un Ventspils
# Augstskolas rektors (2000-2010, pre-Saeima).
CONFIGS: list[HomonymConfig] = [
    HomonymConfig(
        pid=81,
        expected_name="Mārtiņš Daģis",
        notes="Saeima JV b. 1976 vs Jelgavas dome priekšsēdētājs b. 1988 (Kustība Par!)",
        keywords={"vad_disambig": ["Latvijas Republikas Saeima", "Saeimas deputāts"]},
        negative_patterns=["Jelgavas valstspilsētas pašvaldības"],
    ),
    HomonymConfig(
        pid=158,
        expected_name="Agnese Lāce",
        notes=(
            "Progresīvo Kultūras ministre b. 1987 (migrācijas pētniece "
            "Providus 2016-2023) vs NMPD mediķe homonīms"
        ),
        keywords={
            "vad_disambig": [
                "Latvijas Republikas Saeima",
                "Saeimas deputāte",
                "Valsts kanceleja",
                "Kultūras ministrija",
                "Sabiedrības integrācijas fonds",
            ]
        },
        negative_patterns=["Neatliekamās medicīniskās palīdzības"],
    ),
    HomonymConfig(
        pid=10,
        expected_name="Andris Kulbergs",
        notes=(
            "AS 14. Saeimas deputāts b. 1979 (pre-politikas auto-industrijas "
            "uzņēmējs Inchcape/Auto Torino, SIA VK Development) vs Valsts "
            "policijas inspektors homonīms"
        ),
        keywords={
            "vad_disambig": ["Latvijas Republikas Saeima", "Saeimas deputāts"]
        },
        negative_patterns=["Valsts policija"],
    ),
    HomonymConfig(
        pid=137,
        expected_name="Jānis Vucāns",
        notes=(
            "ZZS Saeimas deputāts b. 1956 (matemātiķis, Ventspils Augstskolas "
            "rektors 2000-2010, 14. Saeimā kopš 2022) vs Madonas Valsts "
            "policijas inspektors homonīms"
        ),
        keywords={
            "vad_disambig": [
                "Latvijas Republikas Saeima",
                "Saeimas deputāts",
                "Ventspils Augstskola",
            ]
        },
        negative_patterns=["Valsts policija"],
    ),
]


def _apply(db, cfg: HomonymConfig, *, dry_run: bool) -> bool:
    """Validate + UPDATE viena pid; return True ja kaut kas mainīts (vai
    dry-run režīmā — ja kaut kas BŪTU mainīts)."""
    row = db.execute(
        "SELECT name, keywords, negative_patterns FROM tracked_politicians WHERE id=?",
        (cfg.pid,),
    ).fetchone()
    if row is None:
        print(f"[skip] pid={cfg.pid} not found in tracked_politicians")
        return False
    if row["name"] != cfg.expected_name:
        print(
            f"[warn] pid={cfg.pid} name mismatch: "
            f"expected {cfg.expected_name!r}, got {row['name']!r}"
        )

    # Merge keywords with existing dict (preserve other keys, e.g. tags)
    existing_kw: dict | list = {}
    if row["keywords"]:
        try:
            existing_kw = json.loads(row["keywords"])
        except json.JSONDecodeError:
            existing_kw = {}
    if isinstance(existing_kw, list):
        existing_kw = {"tags": existing_kw} if existing_kw else {}
    existing_kw.update(cfg.keywords)
    new_kw = json.dumps(existing_kw, ensure_ascii=False)

    new_neg = json.dumps(list(cfg.negative_patterns), ensure_ascii=False)

    if dry_run:
        print(f"[plan] pid={cfg.pid:>3} {row['name']}")
        print(f"       keywords          := {new_kw}")
        print(f"       negative_patterns := {new_neg}")
        if cfg.notes:
            print(f"       notes             :  {cfg.notes}")
        return True

    db.execute(
        "UPDATE tracked_politicians SET keywords=?, negative_patterns=? WHERE id=?",
        (new_kw, new_neg, cfg.pid),
    )
    print(f"[ok]   pid={cfg.pid:>3} {row['name']}")
    print(f"       keywords          := {new_kw}")
    print(f"       negative_patterns := {new_neg}")
    if cfg.notes:
        print(f"       notes             :  {cfg.notes}")
    return True


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    db = get_db()
    n_touched = 0
    for cfg in CONFIGS:
        if _apply(db, cfg, dry_run=args.dry_run):
            n_touched += 1
    if not args.dry_run:
        db.commit()
    verb = "planned (dry-run)" if args.dry_run else "updated"
    print(f"\n[done] {n_touched}/{len(CONFIGS)} pids {verb}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
