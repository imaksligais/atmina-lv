"""Nedēļas pārskata #547 virsraksts sākās ar mazo burtu (operatora novērojums 2026-09-08).

Virsraksts dzīvo DIVĀS vietās šai rindai (BACKLOG § «Pārskata virsraksta labojums ir
ČETRU vietu labojums»): `content` bloks «## Vizuālais brief» → «Galvenā tēze», un
denormalizētā kolonna `visual_brief_json.headline`, ko renders faktiski lasa
(`src/render/blog.py`). Bez otrās vietas labojums izietu cauri KLUSI.
Trešā un ceturtā vieta (wiki/weeklies kopija) šai nedēļai neeksistē — pārbaudīts.

Mērījums pirms labojuma: 173 pārskati ar aizpildītu `headline`, 4 sākas ar mazo
burtu — trīs no tiem ir «airBaltic» (zīmola forma, NEDRĪKST kapitalizēt), tāpēc
īstais defekts ir viens: #547.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.db import get_db

NOTE_ID = 547
ROLLBACK = ROOT / "data" / "rollback_weekly_547_headline_case_2026-09-08.sql"

OLD = "ministrs palika amatā un plāns palika nemainīts, bet koalīcijas nākamā pārbaude jau ir aviokompānijas aizņēmuma cena."
NEW = "Ministrs palika amatā un plāns palika nemainīts, bet koalīcijas nākamā pārbaude jau ir aviokompānijas aizņēmuma cena."


def sql_quote(db, value):
    return db.execute("SELECT quote(?)", (value,)).fetchone()[0]


with get_db() as db:
    row = db.execute(
        "SELECT content, visual_brief_json FROM context_notes WHERE id=?", (NOTE_ID,)
    ).fetchone()
    if row is None:
        raise SystemExit("nav context_notes #547")
    old_content, old_json = row["content"], row["visual_brief_json"]

    if old_content.count(OLD) != 1:
        raise SystemExit(f"content: gaidīts 1 trāpījums, atrasti {old_content.count(OLD)}")
    vb = json.loads(old_json)
    if vb.get("headline") != OLD:
        raise SystemExit(f"visual_brief_json.headline negaidīts: {vb.get('headline')!r}")

    ROLLBACK.write_text(
        "\n".join([
            "-- ROLLBACK for: nedēļas pārskata #547 virsraksta lielā burta labojums 2026-09-08.",
            "-- Atsauc abas vietas: content «Galvenā tēze» un visual_brief_json.headline.",
            "-- Uz priekšu vērstās izmaiņas piemērošanas datums: 2026-09-08.",
            "-- NB: pēc šī SQL jāpārrenderē blog,dashboard,static un jādeployo.",
            "BEGIN;",
            f"UPDATE context_notes SET content={sql_quote(db, old_content)}, "
            f"visual_brief_json={sql_quote(db, old_json)} WHERE id={NOTE_ID};",
            "COMMIT;",
        ]) + "\n",
        encoding="utf-8",
    )
    if ROLLBACK.stat().st_size < 1000:
        raise SystemExit("rollback nav droši uzrakstīts")

    vb["headline"] = NEW
    new_content = old_content.replace(OLD, NEW, 1)
    new_json = json.dumps(vb, ensure_ascii=False)
    db.execute(
        "UPDATE context_notes SET content=?, visual_brief_json=? WHERE id=?",
        (new_content, new_json, NOTE_ID),
    )
    db.commit()

    got = db.execute(
        "SELECT content, visual_brief_json FROM context_notes WHERE id=?", (NOTE_ID,)
    ).fetchone()
    result = {
        "rollback": ROLLBACK.name,
        "content_fixed": got["content"].count(NEW) == 1 and got["content"].count(OLD) == 0,
        "json_headline": json.loads(got["visual_brief_json"])["headline"][:40],
        "abas_vietas_sakrit": json.loads(got["visual_brief_json"])["headline"] in got["content"],
    }

print(json.dumps(result, ensure_ascii=False, indent=2))
raise SystemExit(0 if result["content_fixed"] and result["abas_vietas_sakrit"] else 1)
