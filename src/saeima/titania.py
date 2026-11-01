"""titania.saeima.lv likumprojekta lapu parsētāji (tīras funkcijas, bez tīkla).

Divas lapas katram likumprojektam:
- `<BĀZE>/webSasaiste?OpenView&restricttocategory=<nr>` → `dvRow_LPView("<statuss>",
  "<nosaukums>","<nr>","<UNID>",…)` — `parse_sasaiste_row()`.
- `<BĀZE>/0/<UNID>?OpenDocument` → posmu tabula `#mainInfoTable` —
  `parse_stage_table()`.

Posmu tabulai ir trīs izkārtojumi:
- Lp (likumprojekts): kolonnas = posmi (Iesniegts, …, 1. lasījums, 2. lasījums,
  Izsludināts), rindas «Datums» un «Rezultāts».
- Lm (lēmumprojekts): kolonnas Iesniegts | Saeimas sēde | Dok. nr. | Rezultāts,
  katra datu rinda = viena izskatīšana sēdē.
- P (pieprasījums): grupas «Saeimas sēde I/II/III», katrā Datums | Dok. nr. |
  Rezultāts.
"""

from __future__ import annotations

import html as _html
import re
from datetime import datetime
from typing import Optional

_TR_RE = re.compile(r"<tr\b([^>]*)>(.*?)</tr>", re.S | re.I)
_TD_RE = re.compile(r"<td\b([^>]*)>(.*?)</td>", re.S | re.I)
_TAG_RE = re.compile(r"<[^>]+>")
_TABLE_RE = re.compile(
    r"<table\b[^>]*id=[\"']?mainInfoTable[\"']?[^>]*>(.*?)</table>", re.S | re.I)
_COLSPAN_RE = re.compile(r"colspan\s*=\s*[\"']?(\d+)", re.I)
_CLASS_RE = re.compile(r"class\s*=\s*[\"']?([\w-]+)", re.I)
_DATE_RE = re.compile(r"^(\d{2})\.(\d{2})\.(\d{4})$")
_JS_STR_RE = re.compile(r'"((?:[^"\\]|\\.)*)"')
_DVROW_RE = re.compile(r"dvRow_LPView\(\s*")
_SEP_RE = re.compile(r"[\s,]*")


def _text(fragment: str) -> str:
    """HTML šūna → tīrs teksts (tagi nost, entītijas atkodētas, &nbsp; → atstarpe)."""
    t = _html.unescape(_TAG_RE.sub("", fragment)).replace("\xa0", " ")
    return re.sub(r"\s+", " ", t).strip()


def _iso(d: str) -> Optional[str]:
    m = _DATE_RE.match(d.strip())
    if not m:
        return None
    return datetime(int(m[3]), int(m[2]), int(m[1])).date().isoformat()


def _rows(table_html: str) -> list[tuple[str, list[tuple[str, int]]]]:
    """→ [(tr klase, [(šūnas teksts, colspan)])]."""
    out = []
    for tr_attrs, body in _TR_RE.findall(table_html):
        cm = _CLASS_RE.search(tr_attrs)
        cells = []
        for td_attrs, td_body in _TD_RE.findall(body):
            sm = _COLSPAN_RE.search(td_attrs)
            cells.append((_text(td_body), int(sm[1]) if sm else 1))
        out.append((cm[1] if cm else "", cells))
    return out


def parse_sasaiste_row(page_html: str, document_nr: str) -> Optional[dict]:
    """`webSasaiste` skats → {status, title, document_nr, unid} vai None.

    Ja skatā vairākas rindas, ņem to, kuras numurs sakrīt ar `document_nr`.
    """
    for m in _DVROW_RE.finditer(page_html):
        args = []
        pos = m.end()
        for _ in range(4):  # pirmie četri argumenti ir virknes literāļi
            sm = _JS_STR_RE.match(page_html, pos)
            if not sm:
                break
            args.append(_html.unescape(sm[1].replace('\\"', '"')))
            pos = _SEP_RE.match(page_html, sm.end()).end()
        if len(args) < 4:
            continue
        if args[2].strip() == document_nr:
            return {"status": args[0].strip(), "title": args[1].strip(),
                    "document_nr": args[2].strip(), "unid": args[3].strip()}
    return None


def parse_stage_table(page_html: str) -> list[dict]:
    """Posmu tabula → [{name, date (ISO vai None), result (vai None)}] lapas secībā.

    Tukša tabula / tās trūkums → []. Parsētājs neko neizdomā: šūna bez datuma
    dod `date=None`, tukšs rezultāts — `result=None`.
    """
    m = _TABLE_RE.search(page_html)
    if not m:
        return []
    rows = _rows(m[1])
    head = next((c for k, c in rows if k == "headRowCT"), None)
    if not head:
        return []
    top = next((c for k, c in rows if k == "headRowCTtop"), None)
    data = [c for k, c in rows if k == "infoRowCT" and c]

    # Lp: pirmā galvenes šūna tukša, rindas iezīmētas ar «Datums»/«Rezultāts».
    if head[0][0] == "":
        names = [t for t, _ in head[1:]]
        by_label = {c[0][0]: [t for t, _ in c[1:]] for c in data}
        dates = by_label.get("Datums", [])
        results = by_label.get("Rezultāts", [])
        stages = []
        for i, name in enumerate(names):
            d = dates[i] if i < len(dates) else ""
            r = results[i] if i < len(results) else ""
            stages.append({"name": name, "date": _iso(d), "result": r or None})
        return stages

    labels = [t for t, _ in head]
    stages: list[dict] = []
    if top:
        # P: kolonnu grupas (colspan) virs Datums | Dok. nr. | Rezultāts.
        groups: list[str] = []
        for t, span in top:
            groups.extend([t or labels[len(groups)]] * span)
        for cells in data:
            vals = [t for t, _ in cells]
            by_group: dict[str, dict] = {}
            order: list[str] = []
            for i, v in enumerate(vals):
                g = groups[i] if i < len(groups) else f"?{i}"
                lab = labels[i] if i < len(labels) else ""
                if g not in by_group:
                    by_group[g] = {"name": g, "date": None, "result": None}
                    order.append(g)
                if lab in ("Datums", "Iesniegts"):
                    by_group[g]["date"] = _iso(v)
                elif lab == "Rezultāts":
                    by_group[g]["result"] = v or None
            stages.extend(by_group[g] for g in order
                          if by_group[g]["date"] or by_group[g]["result"])
        return stages

    # Lm: katra datu rinda = viena izskatīšana.
    idx = {lab: i for i, lab in enumerate(labels)}
    for cells in data:
        vals = [t for t, _ in cells]

        def get(lab: str, vals: list[str] = vals) -> str:
            i = idx.get(lab)
            return vals[i] if i is not None and i < len(vals) else ""

        if "Iesniegts" in idx and get("Iesniegts"):
            stages.append({"name": "Iesniegts", "date": _iso(get("Iesniegts")),
                           "result": None})
        sede = get("Saeimas sēde")
        res = get("Rezultāts")
        if sede or res:
            stages.append({"name": "Saeimas sēde", "date": _iso(sede),
                           "result": res or None})
    return stages
