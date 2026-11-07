"""Seed tracked_politicians.keywords.vad_disambig for 11 contaminated pids.

Phase 1.5 F13 — homonīmu V+U gadījumi VID portālā. Skat. plan T7
+ Telegram melnraksts apstiprinājums 2026-05-02 msg 1584.

Rule: keywords JSON kļūst dict ar lauku vad_disambig=[..substrings..].
Ja keywords ir saraksts (legacy formāts), pārveido uz dict ar "tags" key.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.db import get_db  # noqa: E402

# (pid, name, vad_disambig substrings) — apstiprināts 2026-05-02 msg 1584
HINTS: list[tuple[int, str, list[str]]] = [
    (146, "Andris Bērziņš",   ["Saeimas deputāts", "Saeimas deputāte", "Latvijas Republikas Saeima"]),
    (101, "Inese Kalniņa",    ["Saeimas deputāts", "Latvijas Republikas Saeima", "Tiesu administrācija", "Latvijas Nacionālais arhīvs"]),
    (144, "Inga Bērziņa",     ["Saeimas deputāts", "Saeimas deputāte", "Latvijas Republikas Saeima"]),
    (104, "Līga Kļaviņa",     ["Saeimas deputāts", "Saeimas deputāte", "Latvijas Republikas Saeima", "Finanšu ministrija"]),
    (138, "Jānis Zariņš",     ["Saeimas deputāts", "Latvijas Republikas Saeima", "Valsts meža dienests"]),
    (106, "Līga Kozlovska",   ["Saeimas deputāts", "Saeimas deputāte", "Latvijas Republikas Saeima"]),
    (155, "Dace Melbārde",    ["Izglītības un zinātnes ministre", "Kultūras ministre", "Valsts kanceleja", "Saeimas deputāte", "Latvijas Republikas Saeima"]),
    ( 92, "Iļja Ivanovs",     ["Saeimas deputāts", "Latvijas Republikas Saeima"]),
    ( 25, "Viktors Valainis", ["Saeimas deputāts", "Latvijas Republikas Saeima", "Ekonomikas ministrs", "Valsts kanceleja"]),
    (132, "Jānis Skrastiņš",  ["Saeimas deputāts", "Latvijas Republikas Saeima", "Zvērināts notārs", "Tieslietu ministrija"]),
    (107, "Linda Liepiņa",    ["Saeimas deputāts", "Saeimas deputāte", "Latvijas Republikas Saeima", "Korupcijas novēršanas un apkarošanas birojs"]),
]


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    db = get_db()
    for pid, expected_name, hints in HINTS:
        row = db.execute(
            "SELECT name, keywords FROM tracked_politicians WHERE id=?", (pid,)
        ).fetchone()
        if row is None:
            print(f"[skip] pid={pid} not found in tracked_politicians")
            continue
        if row["name"] != expected_name:
            print(f"[warn] pid={pid} name mismatch: expected {expected_name!r}, got {row['name']!r}")
        existing: dict | list = []
        if row["keywords"]:
            try:
                existing = json.loads(row["keywords"])
            except json.JSONDecodeError:
                existing = []
        if isinstance(existing, list):
            existing = {"tags": existing} if existing else {}
        existing["vad_disambig"] = hints
        new_kw = json.dumps(existing, ensure_ascii=False)
        db.execute("UPDATE tracked_politicians SET keywords=? WHERE id=?", (new_kw, pid))
        print(f"[ok]  pid={pid:>3} {row['name']:<28} vad_disambig={hints}")
    db.commit()
    print(f"\n[done] {len(HINTS)} pids updated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
