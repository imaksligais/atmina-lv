#!/usr/bin/env python
"""Atrod novecojušas `document_politicians` rindas: tādas, ko pašreizējais
saistītājs vairs neradītu.

Kāpēc: pirms vārda robežas labojuma saistītājs ķēra uzvārdu kā apakšvirkni
("Baško" ⊂ "Baškortostāna", "Daudze" ⊂ "Daudzeva", "Rajevs" ⊂ "Rajevska").
Saistītājs ir salabots, bet vecās rindas palika DB un ir redzamas profilos.

Tikai lasa. Rezultātu raksta JSON; dzēšanu dara atsevišķs solis ar rollback.

Lietojums:
    .venv/Scripts/python.exe scripts/audit_stale_politician_links.py [--json CEĻŠ] [--limit N]
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8")

from src.matcher import _load_politician_forms, _occurrences, match_politicians  # noqa: E402

DB = Path(__file__).resolve().parent.parent / "data" / "atmina.db"
# X piesaistes nāk no autora/@handle, ne no teksta — tās šī pārbaude neskar.
# 'x_mention' arī: tur subjekts ir tvīta autors, kura vārds tekstā neparādās.
SKIP_PLATFORMS = ("twitter", "x", "x_mention")


TR = str.maketrans("šķļņāēīūčžģ", "sklnaeiuczg")
LV_LOWER = "a-zāčēģīķļņšūž"

# Kāpēc piesaiste pastāv, lai gan pašreizējais saistītājs to neradītu.
# Mērīts 2026-09-22 (242 rindas): tikai "apakšvirknes_slazds" ir defekts.
REASONS = {
    "institucija": "organizācija/žurnālists — piesaiste nāk no avota, ne teksta",
    "url_celš": "uzvārds ir URL-ā (autora sleja) — `_match_politician_from_url`",
    "teksts_nomainits": "dokuments pārskrāpēts PĒC piesaistes (db.py same-URL UPDATE)",
    "piesaiste_velak": "piesaiste izveidota vēlāk nekā skrāpējums — cita kārta",
    "apakšvirknes_slazds": "uzvārds tikai kā apakšvirkne garākā vārdā — DEFEKTS",
    "varda_nav_tekstā": "vārda tekstā nav; glabātais teksts ir nogriezta ekstrakcija",
}


def _classify(con, row: dict, meta: dict, scraped) -> str:
    """Iemesls vienai `substring_only` rindai. Sk. REASONS."""
    import datetime

    pid = row["politician_id"]
    name, rel = meta.get(pid, ("", ""))
    surname = name.split()[-1] if name else ""
    url = (row["source_url"] or "").lower()

    if rel in ("organization", "journalist", "neutral"):
        return "institucija"
    if surname and len(surname) > 4 and surname.lower().translate(TR) in url.translate(TR):
        return "url_celš"

    created = con.execute(
        "select created_at from document_politicians where document_id=? and politician_id=?",
        (row["document_id"], pid),
    ).fetchone()

    def _p(x):
        try:
            return datetime.datetime.fromisoformat(str(x))
        except Exception:
            return None

    a, b = _p(scraped), _p(created[0] if created else None)
    if a and b:
        # scraped_at raksta now_lv() (UTC+3), created_at — SQLite CURRENT_TIMESTAMP
        # (UTC): vienā darbībā tapušām rindām starpība ir tieši ~3 h.
        delta_h = (a - b).total_seconds() / 3600 - 3
        if delta_h > 0.6:
            return "teksts_nomainits"
        if delta_h < -0.6:
            return "piesaiste_velak"

    text = con.execute(
        "select content from documents where id=?", (row["document_id"],)
    ).fetchone()[0] or ""
    if surname:
        stem = surname[: max(3, len(surname) - 2)]
        if re.search(re.escape(stem) + f"[{LV_LOWER}]*", text, re.I):
            return "apakšvirknes_slazds"
    return "varda_nav_tekstā"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="data/stale_politician_links.json")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    pols = {i: n for i, n in con.execute("select id, name from tracked_politicians")}
    meta = {
        i: (n, rt)
        for i, n, rt in con.execute(
            "select id, name, relationship_type from tracked_politicians"
        )
    }
    scraped_at = dict(con.execute("select id, scraped_at from documents"))

    q = """select d.id, d.source_url, d.content
             from documents d
            where d.platform not in (?, ?, ?)
              and exists (select 1 from document_politicians dp where dp.document_id = d.id)
            order by d.id"""
    rows = con.execute(q, SKIP_PLATFORMS).fetchall()
    if args.limit:
        rows = rows[: args.limit]

    # Katra politiķa vārda formas no paša saistītāja (ne pašu ģenerētas).
    forms_by_pid: dict[int, list[str]] = {}
    for pid, forms, _canon, aux in _load_politician_forms():
        forms_by_pid.setdefault(pid, []).extend(list(forms) + list(aux or []))

    stale: list[dict] = []
    t0 = time.time()
    for n_done, (doc_id, url, content) in enumerate(rows, 1):
        text = content or ""
        current = {pid for pid, _role in match_politicians(text)}
        existing = con.execute(
            "select politician_id, role from document_politicians where document_id = ?",
            (doc_id,),
        ).fetchall()
        for pid, role in existing:
            if pid in current:
                continue
            # Asākais tests: vai kāda vārda forma tekstā vispār ir pie vārda
            # robežas. Ja nav — piesaisti teksts nepamato nekādā lasījumā
            # (tā ir "Baško" ⊂ "Baškortostāna" klase). Ja ir — saistītājs to
            # noraida stingrāka noteikuma dēļ (veto, dalīts uzvārds), un tas
            # ir cits, apspriežams gadījums.
            forms = forms_by_pid.get(pid, [])
            justified = any(_occurrences(text, f) for f in forms)
            row = {
                "document_id": doc_id,
                "politician_id": pid,
                "politician": pols.get(pid, f"?{pid}"),
                "role": role,
                "source_url": url,
                "kind": "vetoed" if justified else "substring_only",
            }
            if row["kind"] == "substring_only":
                row["reason"] = _classify(con, row, meta, scraped_at.get(doc_id))
            stale.append(row)
        if n_done % 2000 == 0:
            print(f"  ... {n_done}/{len(rows)} ({time.time() - t0:.0f}s), atrastas {len(stale)}")

    out = Path(args.json)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(stale, ensure_ascii=False, indent=1), encoding="utf-8")

    subs = [s for s in stale if s["kind"] == "substring_only"]
    vet = [s for s in stale if s["kind"] == "vetoed"]
    print(f"\nPārbaudīti {len(rows)} dokumenti {time.time() - t0:.0f}s")
    print(f"Rindas, ko saistītājs vairs neradītu: {len(stale)} → {out}")
    print(f"  no tām TEKSTS NEPAMATO (apakšvirknes klase): {len(subs)}")
    print(f"  no tām vēlāka stingrāka noteikuma dēļ (veto): {len(vet)}")
    counts: dict[str, int] = {}
    for s in subs:
        counts[s.get("reason", "?")] = counts.get(s.get("reason", "?"), 0) + 1
    print("\nKāpēc rinda pastāv (tikai „teksts nepamato\" klasē):")
    for k in sorted(counts, key=lambda x: -counts[x]):
        print(f"  {counts[k]:4}  {k:22} {REASONS.get(k, '')}")

    defects = [s for s in subs if s.get("reason") == "apakšvirknes_slazds"]
    by_pol: dict[str, int] = {}
    for s in defects:
        by_pol[s["politician"]] = by_pol.get(s["politician"], 0) + 1
    print(f"\nDEFEKTI (dzēšamie kandidāti): {len(defects)}")
    for name, c in sorted(by_pol.items(), key=lambda x: -x[1]):
        print(f"  {name}: {c}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
