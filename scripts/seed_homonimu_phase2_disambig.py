"""Seed Phase 2 — sašauri 5 pids whitelist pēc 2026-05-05 audita.

Atklājumi: Phase 1.5 disambig whitelist Inese Kalniņa, Līga Kļaviņa, Jānis
Skrastiņš, Gatis Liepiņš (kuram nebija nekāda whitelist), Linda Liepiņa
iekļāva institūcijas, kas faktiski pieder homonīmiem (citiem cilvēkiem ar to
pašu vārdu un uzvārdu). Ģimenes locekļu sarakstu disjoint klasteri
(scripts/audit_vad_family_clusters.py) ir gold standard pierādījums.

Idempotents.

Apstiprinātie atklājumi:
- pid 101 Inese Kalniņa: TIKAI Saeima (LNA un Tiesu adm = 2 atšķirīgi homonīmi)
- pid 104 Līga Kļaviņa:  TIKAI Saeima (FM = atšķirīgs cilvēks ar citu vīru un meitu)
- pid 107 Linda Liepiņa: TIKAI Saeima (KNAB = atšķirīgs cilvēks ar vīru Ingu)
- pid 116 Gatis Liepiņš: TIKAI Saeima (Valsts policija = atšķirīgs cilvēks)
- pid 132 Jānis Skrastiņš: TIKAI Saeima (Tieslietu ministrija/notārs = atšķ.)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.db import get_db  # noqa: E402

CONFIGS: list[dict] = [
    {
        "pid": 101, "name": "Inese Kalniņa",
        "vad_disambig": ["Saeimas deputāts", "Saeimas deputāte", "Latvijas Republikas Saeima"],
        "negative_patterns": ["Tiesu administrācija", "Latvijas Nacionālais arhīvs"],
    },
    {
        "pid": 104, "name": "Līga Kļaviņa",
        "vad_disambig": ["Saeimas deputāts", "Saeimas deputāte", "Latvijas Republikas Saeima"],
        "negative_patterns": ["Finanšu ministrija", "Altum"],
    },
    {
        "pid": 107, "name": "Linda Liepiņa",
        "vad_disambig": ["Saeimas deputāts", "Saeimas deputāte", "Latvijas Republikas Saeima"],
        "negative_patterns": ["Korupcijas novēršanas un apkarošanas birojs"],
    },
    {
        "pid": 116, "name": "Gatis Liepiņš",
        "vad_disambig": ["Saeimas deputāts", "Saeimas deputāte", "Latvijas Republikas Saeima"],
        "negative_patterns": ["Valsts policija", "Ieslodzījuma vietu pārvalde"],
    },
    {
        "pid": 132, "name": "Jānis Skrastiņš",
        "vad_disambig": ["Saeimas deputāts", "Saeimas deputāte", "Latvijas Republikas Saeima"],
        "negative_patterns": ["Tieslietu ministrija", "Zvērināts notārs", "ZNB"],
    },
]


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    db = get_db()
    for cfg in CONFIGS:
        row = db.execute(
            "SELECT name, keywords, negative_patterns FROM tracked_politicians WHERE id = ?",
            (cfg["pid"],),
        ).fetchone()
        if row is None:
            print(f"[skip] pid={cfg['pid']} not found")
            continue
        if row["name"] != cfg["name"]:
            print(f"[warn] pid={cfg['pid']} name mismatch: expected {cfg['name']!r}, got {row['name']!r}")

        existing: dict | list = []
        if row["keywords"]:
            try:
                existing = json.loads(row["keywords"])
            except json.JSONDecodeError:
                existing = []
        if isinstance(existing, list):
            existing = {"tags": existing} if existing else {}
        existing["vad_disambig"] = cfg["vad_disambig"]

        db.execute(
            "UPDATE tracked_politicians SET keywords = ?, negative_patterns = ? WHERE id = ?",
            (
                json.dumps(existing, ensure_ascii=False),
                json.dumps(cfg["negative_patterns"], ensure_ascii=False),
                cfg["pid"],
            ),
        )
        print(f"[ok]  pid={cfg['pid']:>3} {row['name']:<22} "
              f"vad_disambig={cfg['vad_disambig']} neg={cfg['negative_patterns']}")
    db.commit()
    print(f"\n[done] {len(CONFIGS)} pids updated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
