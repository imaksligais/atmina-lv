"""VAD triāža: VID deklarācijas, kuru DB nav, ar ģimenes/amatu/NĪ parakstu (tikai lasa).

Resweep dry-run `new` rindas var būt vārdabrāļi (operacijas.md § VID). Šis rīks
katrai rindai, kuras identitāte (etiķete + amats) nav `vad_declarations`, ielādē
VID detaļu lapu un izdrukā ģimeni, amatus un NĪ — salīdzini ar politiķa jau
glabātajām deklarācijām. Ģimene ir stabilākais identitātes paraksts (2026-10-08:
Zīle, Burovs, Elksniņš, Jenzis izšķirti tā). DB atver `mode=ro`; neko neraksta.

Usage:
    .venv/Scripts/python.exe scripts/vad_peek.py --pids 248,187
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from src.db import PRODUCTION_DB_PATH  # noqa: E402
from src.vad import VadClient  # noqa: E402
from src.vad.fetch import declaration_identity  # noqa: E402
from src.vad.matcher import candidate_name_pairs  # noqa: E402
from src.vad.parsing import parse_declaration_html  # noqa: E402


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--pids", required=True, help="komatatdalīti pid")
    args = p.parse_args(argv)
    path = (REPO_ROOT / PRODUCTION_DB_PATH).resolve().as_posix()
    db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    with VadClient() as client:
        for pid in (int(x) for x in args.pids.split(",") if x.strip()):
            name = db.execute("SELECT name FROM tracked_politicians WHERE id=?", (pid,)).fetchone()[0]
            stored = {(t, pos) for t, _i, pos in (declaration_identity(*r) for r in db.execute(
                "SELECT declaration_type, institution, position_title FROM vad_declarations "
                "WHERE opponent_id=?", (pid,)))}
            print(f"=== pid {pid} {name}")
            rows = []
            for given, family in candidate_name_pairs(pid, name):
                rows = client.search(given, family)
                if rows:
                    break
            for r in rows:
                t, _i, pos = r.dedup_key()
                if (t, pos) in stored or r.is_legacy:
                    continue
                try:
                    d = parse_declaration_html(client.fetch_detail(r.vad_uuid))
                except Exception as e:  # noqa: BLE001 — triāžas rīks: ziņo un turpina
                    print(f"  FAIL {r.declaration_type}: {e}")
                    continue
                print(f"## {r.declaration_type} | {r.institution} | {r.position_title}")
                print("   ģimene:", [(x.full_name, x.relation) for x in d.family])
                print("   amati: ", [(x.position_title, x.entity_name) for x in d.positions][:5])
                print("   NĪ:    ", [(x.property_type, x.location) for x in d.real_estate][:4])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
