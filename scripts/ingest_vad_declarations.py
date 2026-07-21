"""Manual ingest of VID amatpersonu deklarācijas for tracked politicians.

Spec: docs/superpowers/specs/2026-05-02-vad-deklaracijas-design.md § 8

Idempotent (natural key per F11). Designed for monthly cadence (peak aprīlis-maijs).

Usage:
    python scripts/ingest_vad_declarations.py
    python scripts/ingest_vad_declarations.py --politician slesers-ainars
    python scripts/ingest_vad_declarations.py --limit 5
    python scripts/ingest_vad_declarations.py --dry-run
"""

import argparse
import re
import sys
import time
import unicodedata
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from src.db import get_db  # noqa: E402
from src.ingest_log import _resolve_log_file, append_ingest_entry  # noqa: E402
from src.vad import VadClient, fetch_for_politician, init_vad_tables  # noqa: E402

VAD_SOURCE_CONFIG = {
    "url": "https://www6.vid.gov.lv/VAD",
    "name": "VID amatpersonu deklarācijas",
    "tier": 1,
    "fetcher_mode": "fetcher",
    "rate_limit_seconds": 10,  # F12
    "legal_status": "approved",
    "legal_notes": (
        "Likuma Par interešu konflikta novēršanu valsts amatpersonu darbībā "
        "24. un 25. pants — publicēšanas pienākums un publiskais raksturs. "
        "Manuāls ingest via scripts/ingest_vad_declarations.py."
    ),
    "last_tos_review": "2026-05-02",
}


def _slugify(name: str) -> str:
    s = unicodedata.normalize("NFKD", name)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--politician", help="slug or name substring; default = visi tracked")
    p.add_argument("--limit", type=int, help="max politiķi per palaišana")
    p.add_argument("--dry-run", action="store_true", help="parser+match, bet nav DB write")
    p.add_argument("--include-legacy", action="store_true",
                   help="iekļauj /VAD2002Data legacy deklarācijas (Phase 0.5 backlog)")
    args = p.parse_args(argv)

    # Phase 1.5 F15 — ensure logs/ dir exists pirms iespējamā tee redirect.
    (REPO_ROOT / "logs").mkdir(exist_ok=True)

    db = get_db()
    init_vad_tables()  # idempotent

    rows = db.execute(
        "SELECT id, name FROM tracked_politicians "
        "WHERE relationship_type IN ('tracked') OR relationship_type IS NULL "
        "ORDER BY name"
    ).fetchall()

    politicians = []
    for r in rows:
        slug = _slugify(r["name"])
        if args.politician:
            needle = args.politician.lower()
            if needle not in slug and needle not in r["name"].lower():
                continue
        politicians.append((r["id"], r["name"], slug))

    if args.limit:
        politicians = politicians[: args.limit]

    print(f"[plan] {len(politicians)} politiķi (dry_run={args.dry_run})")

    total_new = 0
    total_skip_role = 0
    total_skip_legacy = 0
    total_present = 0
    total_errors = 0
    started = time.monotonic()

    with VadClient() as client:
        for pid, name, _slug in politicians:
            t0 = time.monotonic()
            try:
                result = fetch_for_politician(
                    pid, db, client,
                    include_legacy=args.include_legacy,
                    dry_run=args.dry_run,
                )
            except Exception as e:
                print(f"[fail] {name}: {type(e).__name__}: {e}")
                total_errors += 1
                continue
            total_new += result.new_inserted
            total_skip_role += result.rows_skipped_role
            total_skip_legacy += result.rows_skipped_legacy
            total_present += result.already_present
            total_errors += len(result.errors)
            elapsed = time.monotonic() - t0
            print(
                f"[ok]  {name:<32} new={result.new_inserted} present={result.already_present} "
                f"skip_role={result.rows_skipped_role} skip_legacy={result.rows_skipped_legacy} "
                f"errs={len(result.errors)} ({elapsed:.1f}s)"
            )

    total_elapsed = time.monotonic() - started
    print(
        f"\n[done] new={total_new} present={total_present} "
        f"skip_role={total_skip_role} skip_legacy={total_skip_legacy} "
        f"errors={total_errors} (~{total_elapsed/60:.1f} min)"
    )

    if not args.dry_run:
        try:
            append_ingest_entry(
                source_name=VAD_SOURCE_CONFIG["name"],
                source_tier=VAD_SOURCE_CONFIG["tier"],
                documents_added=total_new,
                documents_skipped=total_present + total_skip_role + total_skip_legacy,
                status="success" if total_errors == 0 else "partial",
                extra=f"manuāls; {len(politicians)} politiķi sweep'ēti",
            )
        except Exception as e:
            print(f"[warn] ingest log entry failed: {e}", file=sys.stderr)

    return 0 if total_errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
