"""titania.saeima.lv posmu tabulas visiem `saeima_bills` ar `current_status='procesā'`.

Kāpēc: līdz ~2026-09 ielāde steidzama likumprojekta galīgajā (2.) lasījumā
`saeima_bill_stages.stage_result` ierakstīja «Pieņemts», nevis Saeimas iznākumu
«Likums», tāpēc pieņemti likumi rādās «procesā». Patiesības avots ir titania;
šis skripts tikai LASA (DB `mode=ro`) un raksta CSV, ko izmanto
`scripts/backfill_bill_stage_result_from_titania.py`.

Neapstrādātais HTML → `E:/atmina/.scratch/titania_html/`. Kļūda → 1 atkārtojums,
tad ierakstīta `error` kolonnā; skrējiens neapstājas.

Lietošana:
    .venv/Scripts/python.exe scripts/scrape_titania_bill_stages.py
    .venv/Scripts/python.exe scripts/scrape_titania_bill_stages.py --limit 5 --out x.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import sys
import time
from collections import Counter
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.db import PRODUCTION_DB_PATH  # noqa: E402
from src.saeima.titania import parse_sasaiste_row, parse_stage_table  # noqa: E402

BASES = {
    "Lp14": "https://titania.saeima.lv/LIVS14/saeimalivs14.nsf",
    "Lm14": "https://titania.saeima.lv/LIVS14/saeimalivs_lmp.nsf",
    "P14": "https://titania.saeima.lv/LIVS14/saeimalivs_lmp.nsf",
}
PAUSE_S = 0.5
HTML_DIR = ROOT / ".scratch" / "titania_html"
DEFAULT_OUT = ROOT / "data" / "titania_bill_stages_2026-10-19.csv"
FIELDS = ["document_nr", "bill_type", "titania_status", "stages", "error"]


def fetch(session: requests.Session, url: str) -> tuple[bytes, str]:
    """→ (neapstrādātie baiti, atkodēts teksts). 1 atkārtojums, tad izņēmums."""
    last: Exception | None = None
    for attempt in range(2):
        time.sleep(PAUSE_S)
        try:
            r = session.get(url, timeout=30)
            r.raise_for_status()
            return r.content, r.content.decode(r.encoding or "utf-8", errors="replace")
        except Exception as e:  # noqa: BLE001 — jebkura kļūda → atkārto, tad ziņo
            last = e
    raise RuntimeError(f"{url}: {last}")


def scrape_one(session: requests.Session, nr: str, bill_type: str) -> dict:
    row = {"document_nr": nr, "bill_type": bill_type, "titania_status": "",
           "stages": "[]", "error": ""}
    suffix = nr.split("/")[-1]
    base = BASES.get(suffix)
    if base is None:
        row["error"] = f"nezināms numura sufikss {suffix!r}"
        return row
    slug = nr.replace("/", "_")
    try:
        raw, text = fetch(session, f"{base}/webSasaiste?OpenView&restricttocategory={nr}")
        (HTML_DIR / f"{slug}_sasaiste.html").write_bytes(raw)
        meta = parse_sasaiste_row(text, nr)
        if meta is None:
            row["error"] = "webSasaiste: nav dvRow_LPView rindas ar šo numuru"
            return row
        row["titania_status"] = meta["status"]
        raw, text = fetch(session, f"{base}/0/{meta['unid']}?OpenDocument")
        (HTML_DIR / f"{slug}_doc.html").write_bytes(raw)
        stages = parse_stage_table(text)
        row["stages"] = json.dumps(stages, ensure_ascii=False)
        if not stages:
            row["error"] = "posmu tabula tukša vai nav atrasta"
    except Exception as e:  # noqa: BLE001
        row["error"] = str(e)[:300]
    return row


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args(argv)

    db_path = Path(PRODUCTION_DB_PATH)
    if not db_path.is_absolute():
        db_path = ROOT / db_path
    db = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    bills = db.execute(
        "SELECT document_nr, bill_type FROM saeima_bills "
        "WHERE current_status = 'procesā' ORDER BY id").fetchall()
    db.close()
    if args.limit:
        bills = bills[: args.limit]
    HTML_DIR.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers["User-Agent"] = "atmina.lv bill-stage audit"
    rows = []
    for i, (nr, bt) in enumerate(bills, 1):
        row = scrape_one(session, nr, bt)
        rows.append(row)
        if row["error"]:
            print(f"[{i}/{len(bills)}] {nr}: KĻŪDA {row['error']}")
        elif i % 20 == 0:
            print(f"[{i}/{len(bills)}] …")

    out = Path(args.out)
    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)

    errors = sum(1 for r in rows if r["error"])
    print(f"pārbaudīti: {len(rows)}; kļūdas: {errors}; CSV: {out}")
    for st, n in Counter(r["titania_status"] or "(nav)" for r in rows).most_common():
        print(f"  {st}: {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
