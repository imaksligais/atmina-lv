"""CLI ieeja CSP datu atsvaidzināšanai: ``python -m src.csp``.

Kāpēc šis fails eksistē (operatora lēmums 2026-08-15, izpildīts 2026-09-07,
verdikts 49b): ``src/csp/sync.py`` ir vienīgais ``data/csp.db`` atsvaidzinātājs,
un ``data/csp.db`` ir dzīvs renderēšanas ievads (``src/render/statistika.py``
importē ``src.csp.insights`` + ``src.csp.tables``). Bet ``sync_all(conn)`` ņēma
gatavu savienojumu un izsaucēja nebija — ne CLI, ne cita moduļa —, tāpēc
atsvaidzināšana nebija IZPILDĀMA. 2026-08-15 repo audits to nolasīja kā mirušu
kodu un ieteica dzēst; ieteikums noraidīts, un šeit ir tie vadi, kas trūka.

Divi režīmi:

* ``--dry-run`` (noklusējums) — nokopē esošo ``data/csp.db`` uz pagaidu failu,
  sinhronizē TO un ziņo, cik rindu katrā tabulā būtu pēc atsvaidzinājuma.
  Izsekotais binārais fails NETIEK aiztikts. Tas ir īsts tīkla palaidiens, ne
  simulācija — tāpēc tas pierāda gan API, gan parsēšanu, gan shēmu.
* ``--apply`` — tas pats pret īsto ``data/csp.db``.

``data/csp.db`` ir IZSEKOTS binārs, tāpēc atsvaidzinājums ir datu mutācija, ne
higiēna: dati iesaldēti kopš 2026-04-14, tātad pirmais reālais ``--apply`` dos
lielu diffu, kas aizies arī publiskajā spogulī. Tāpēc noklusējums ir sausais
palaidiens, un ``--apply`` jāraksta ar roku.
"""

from __future__ import annotations

import argparse
import logging
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

from src.csp.db import init_db
from src.csp.sync import sync_all
from src.csp.tables import TABLES

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = PROJECT_ROOT / "data" / "csp.db"

_COUNTED_TABLES = ("csp_data", "csp_metadata", "topic_links")


def _table_counts(conn: sqlite3.Connection) -> dict[str, int]:
    """Rindu skaits katrā uzskaitītajā tabulā — atskaites saucējs."""
    out: dict[str, int] = {}
    for name in _COUNTED_TABLES:
        row = conn.execute(f"SELECT COUNT(*) FROM {name}").fetchone()
        out[name] = int(row[0])
    return out


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="python -m src.csp",
        description="Atsvaidzina data/csp.db no CSP PxWeb API.",
    )
    ap.add_argument(
        "--apply", action="store_true",
        help="Raksta īstajā DB. Bez šī karoga darbojas sausais palaidiens.",
    )
    ap.add_argument(
        "--dry-run", action="store_true",
        help="Skaidri pieprasa sauso palaidienu (noklusējuma uzvedība).",
    )
    ap.add_argument("--db", default=str(DEFAULT_DB), help="DB ceļš.")
    ap.add_argument(
        "--verbose", "-v", action="store_true", help="INFO līmeņa žurnāls.",
    )
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.apply and args.dry_run:
        print("KĻŪDA: --apply un --dry-run izslēdz viens otru.", file=sys.stderr)
        return 2

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )

    db_path = Path(args.db)
    mode = "apply" if args.apply else "dry-run"

    tmp_dir: tempfile.TemporaryDirectory | None = None
    if args.apply:
        target = db_path
    else:
        # Sausais palaidiens strādā ar KOPIJU, ne ar atsevišķu tukšu bāzi:
        # `upsert_rows` ir INSERT OR REPLACE, tāpēc tikai pret esošajiem datiem
        # var pateikt, cik rindu tiešām ir JAUNAS.
        tmp_dir = tempfile.TemporaryDirectory(prefix="csp-dry-run-")
        target = Path(tmp_dir.name) / "csp.db"
        if db_path.exists():
            shutil.copyfile(db_path, target)

    conn = init_db(str(target))
    try:
        before = _table_counts(conn)
        results = sync_all(conn)
        after = _table_counts(conn)
    finally:
        conn.close()

    ok_tables = sum(1 for n in results.values() if n > 0)
    print(f"CSP sync ({mode}) — DB: {db_path}")
    print(f"  Tabulas konfigurācijā : {len(TABLES)}")
    print(f"  Atsvaidzinātas        : {ok_tables}/{len(results)} (0 rindu = neizdevās)")
    for table_id in sorted(results):
        print(f"    {table_id:<10} {results[table_id]:>6} rindas")
    print("  Rindu skaits pirms → pēc:")
    for name in _COUNTED_TABLES:
        delta = after[name] - before[name]
        print(f"    {name:<13} {before[name]:>6} → {after[name]:>6}  ({delta:+d})")
    if not args.apply:
        print("  Sausais palaidiens: data/csp.db NETIKA mainīta.")

    if tmp_dir is not None:
        tmp_dir.cleanup()

    # Nulle atsvaidzinātu tabulu = vārti, kas nevar kļūdīties, ir salūzuši.
    return 0 if ok_tables else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
