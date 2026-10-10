"""Saeimas aktivitāte — deputātu amati, debašu uzstāšanās, jautājumi.

Plāns: docs/plans/2026-10-06-saeimas-aktivitate.md. Katram avotam trīs slāņi:
tīrs `parse_*()` (ievade str, testējams no fixture), plāns `fetch_*()` ar httpx
un `store_*()`, kas atgriež `ActivityResult` ar `failures` sarakstu (Silent
success: ko nomet vai nesaskaņo, to nosauc).

Vārdu saskaņošana ir TIKAI precīza (`_exact_match`): `_build_name_index()`
atslēga pret «Vārds Uzvārds» vai apgriezto secību. Apakšvirkņu atbilstību
(`match_deputies_to_politicians` fallback) šeit NElieto — T1. Nesaskaņots vārds
→ `failures`, politician_id NULL; `tracked_politicians` netiek rakstīts (T6).
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime
from html import unescape

import httpx

from src.db import get_db
from src.saeima.convocation import BILL_SUFFIX, SAEIMA_CONVOCATION
from src.saeima.votes import _build_name_index, normalize_faction

HTTP_TIMEOUT = 20.0


# ---------------------------------------------------------------------------
# Kopīgais — rezultāts, saskaņotājs, palīgi
# ---------------------------------------------------------------------------

@dataclass
class ActivityResult:
    """Viena avota ielādes skaitītāji. Invariants: stored + skipped_existing == parsed."""
    parsed: int = 0
    stored: int = 0
    skipped_existing: int = 0
    closed: int = 0                            # tikai amatiem: esošai rindai ielikts date_to (ietilpst skipped_existing)
    empty_sessions: int = 0                    # tikai debatēm: sēde bez debatēm ≠ kļūda
    failures: list[dict] = field(default_factory=list)

    def summary_line(self) -> str:
        return (
            f"parsed={self.parsed} stored={self.stored} "
            f"skipped_existing={self.skipped_existing} closed={self.closed} "
            f"empty_sessions={self.empty_sessions} failures={len(self.failures)}"
        )


def _exact_match(name_index: dict[str, int], raw_name: str | None) -> int | None:
    """Precīza vārda atrašana indeksā; nekā cita.

    «Vārds Uzvārds» vai (tieši divi vārdi) «Uzvārds Vārds». Viens vārds
    (kails uzvārds) NEsaskaņojas nekad, pat ja tāda atslēga indeksā ir —
    tas ir T1 slazds (namesake).
    """
    if not raw_name:
        return None
    parts = raw_name.split()
    if len(parts) < 2:
        return None
    key = " ".join(parts).lower()
    if key in name_index:
        return name_index[key]
    if len(parts) == 2:
        return name_index.get(f"{parts[1]} {parts[0]}".lower())
    return None


def _match_rows(rows: list[dict], name_index: dict[str, int], name_key: str) -> list[dict]:
    """Uzstāda `politician_id` katrai rindai; atgriež failures (viens ieraksts uz vārdu)."""
    failures: list[dict] = []
    seen: set[str] = set()
    for row in rows:
        row["politician_id"] = _exact_match(name_index, row[name_key])
        if row["politician_id"] is None and row[name_key] not in seen:
            seen.add(row[name_key])
            failures.append({"kind": "unmatched_name", "name": row[name_key]})
    return failures


def _iso_date(raw: str | None) -> str | None:
    """`DD.MM.YYYY` → `YYYY-MM-DD`; tukšs → None. Cita forma → ValueError (paterna maiņa, T12)."""
    if raw is None or not raw.strip():
        return None
    return datetime.strptime(raw.strip(), "%d.%m.%Y").date().isoformat()


# `key:"value"` pāri titania inline JS objektos; vērtībā drīkst būt `\"`.
_JS_PAIR_RE = re.compile(r'(\w+):"((?:[^"\\]|\\.)*)"')


def _js_object(body: str) -> dict[str, str]:
    return {k: re.sub(r"\\(.)", r"\1", v) for k, v in _JS_PAIR_RE.findall(body)}


# ---------------------------------------------------------------------------
# Amati — titania Saeima{N}_DepWeb_Public
# ---------------------------------------------------------------------------

# strLvlTp → nozīme. Citi līmeņi (DG1/DG2 draudzības grupas u.c.) netiek glabāti.
POSITION_LEVELS = {
    "2": "frakcija",
    "3": "komisija",
    "4": "Prezidijs",
    "5": "apakškomisija",
    "6": "delegācija",
    "10": "mandāts",
    "11": "izmeklēšanas komisija",
}

# Sasaukumā ar deputātiem sarakstā ir 100; mazāk par 90 = paterna kļūda (T8/T12).
MIN_DEPUTIES = 90

_DRAW_DEP_RE = re.compile(r"drawDep\(\{(.*?)\}\)")
_DRAW_WN_RE = re.compile(r"drawWN\(\{(.*?)\}\)")


def _depweb_base(convocation: int) -> str:
    return f"https://titania.saeima.lv/Personal/Deputati/Saeima{convocation}_DepWeb_Public.nsf"


def deputy_list_url(convocation: int = SAEIMA_CONVOCATION) -> str:
    return f"{_depweb_base(convocation)}/deputies?OpenView&lang=LV&count=1000"


def deputy_profile_url(unid: str, convocation: int = SAEIMA_CONVOCATION) -> str:
    return f"{_depweb_base(convocation)}/0/{unid}?OpenDocument"


def parse_deputy_list(html: str) -> list[dict]:
    """Saraksta lapa → [{name, sname, unid, faction_label}] no `drawDep({...})`."""
    deputies = []
    for m in _DRAW_DEP_RE.finditer(html):
        obj = _js_object(m.group(1))
        deputies.append({
            "name": obj.get("name", ""),
            "sname": obj.get("sname", ""),
            "unid": obj.get("unid", ""),
            "faction_label": obj.get("lst", ""),
        })
    return deputies


def parse_deputy_positions(html: str) -> list[dict]:
    """Profila lapa → amatu rindas no `drawWN({...})`; tikai POSITION_LEVELS.

    Rindu NEdedublē: to skaita store (stored vs skipped_existing), lai
    parsed = stored + skipped_existing paliek burtisks.
    """
    rows = []
    for m in _DRAW_WN_RE.finditer(html):
        obj = _js_object(m.group(1))
        level = obj.get("strLvlTp", "")
        if level not in POSITION_LEVELS:
            continue
        rows.append({
            "deputy_unid": obj.get("unid", ""),
            "deputy_name": f"{obj.get('name', '')} {obj.get('sname', '')}".strip(),
            "level": level,
            "body": obj.get("str", ""),
            "position": obj.get("position", ""),
            "date_from": _iso_date(obj.get("dtF")),
            "date_to": _iso_date(obj.get("dtT")),
            "deleted": obj.get("deleted", ""),
        })
    return rows


def fetch_deputy_list(client: httpx.Client, convocation: int = SAEIMA_CONVOCATION) -> str:
    resp = client.get(deputy_list_url(convocation))
    resp.raise_for_status()
    return resp.text


def fetch_deputy_positions(
    client: httpx.Client, deputies: list[dict], convocation: int = SAEIMA_CONVOCATION,
) -> tuple[list[dict], list[dict]]:
    """Secīgi ielādē katra deputāta profilu. Atgriež (rindas ar source_url, failures).

    Neielādēts profils = `fetch_error` failures, nevis klusi 0 rindu.
    """
    rows: list[dict] = []
    failures: list[dict] = []
    for dep in deputies:
        url = deputy_profile_url(dep["unid"], convocation)
        try:
            resp = client.get(url)
            resp.raise_for_status()
            dep_rows = parse_deputy_positions(resp.text)
        except (httpx.HTTPError, ValueError) as exc:
            failures.append({"kind": "fetch_error", "unid": dep["unid"],
                             "name": f"{dep['name']} {dep['sname']}", "error": str(exc)})
            continue
        if not dep_rows:
            failures.append({"kind": "empty_profile", "unid": dep["unid"],
                             "name": f"{dep['name']} {dep['sname']}"})
        for row in dep_rows:
            row["source_url"] = url
        rows.extend(dep_rows)
    return rows, failures


def store_deputy_positions(
    db_path: str | None,
    rows: list[dict],
    convocation: int = SAEIMA_CONVOCATION,
    name_index: dict[str, int] | None = None,
) -> ActivityResult:
    """Glabā amatu rindas; idempotents pēc UNIQUE atslēgas.

    Esošai rindai ar `date_to IS NULL` ieliek jauno `date_to` (amats beidzies) — `closed`.
    `ON CONFLICT(...) DO NOTHING`, NE `INSERT OR IGNORE` — pēdējais noklusētu arī
    NOT NULL/FK kļūdas un ieskaitītu tās skipped_existing. Rinda ar ne-tukšu
    `deleted` karogu netiek glabāta (nozīme nav novērota) — tā iet failures.
    """
    if name_index is None:
        name_index = _build_name_index(db_path)
    result = ActivityResult(parsed=len(rows))
    result.failures.extend(_match_rows(rows, name_index, "deputy_name"))

    db = get_db(db_path)
    try:
        for row in rows:
            if row.get("deleted"):
                result.failures.append({"kind": "deleted_flag", "name": row["deputy_name"],
                                        "body": row["body"], "deleted": row["deleted"]})
                continue
            cur = db.execute(
                """INSERT INTO saeima_deputy_positions
                   (convocation, politician_id, deputy_unid, deputy_name, level,
                    body, position, date_from, date_to, source_url)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(convocation, deputy_unid, level, body, position, date_from)
                   DO NOTHING""",
                (convocation, row["politician_id"], row["deputy_unid"], row["deputy_name"],
                 row["level"], row["body"], row["position"], row["date_from"],
                 row["date_to"], row["source_url"]),
            )
            if cur.rowcount == 1:
                result.stored += 1
                continue
            result.skipped_existing += 1
            # Amats, kas pirmajā ielādē vēl ilga, tagad beidzies: date_to nav atslēgā,
            # tāpēc bez šī «pašreizējie amati» rādītu beigušos uz visiem laikiem.
            if row["date_to"] is not None:
                upd = db.execute(
                    """UPDATE saeima_deputy_positions SET date_to = ?
                       WHERE convocation = ? AND deputy_unid = ? AND level = ? AND body = ?
                         AND position = ? AND date_from = ? AND date_to IS NULL""",
                    (row["date_to"], convocation, row["deputy_unid"], row["level"],
                     row["body"], row["position"], row["date_from"]),
                )
                result.closed += upd.rowcount
        db.commit()
    finally:
        db.close()
    return result


# ---------------------------------------------------------------------------
# Debates — data.gov.lv `{N}.Saeimas … -deb.xml` (2. uzdevums)
# ---------------------------------------------------------------------------

CKAN_PACKAGE_URL = "https://data.gov.lv/dati/lv/api/3/action/package_show?id=saeimas-sedes"

# `#`-atdalīti PARALĒLI masīvi: indekss i = i-tais runātājs. DEBATE_SUFFIX un
# DEBATE_STATUS neglabājam, tāpēc to garumu nepārbaudām.
DEBATE_FIELDS = ("DEBATE_NAME", "DEBATE_SURNAME", "DEBATE_FRACTION",
                 "DEBATE_TIME", "DEBATE_INFO", "DEBATE_OPINION")


def _duration_sec(raw: str) -> int | None:
    """`MM:SS` vai `H:MM:SS` → sekundes; cits → None (saucējs to skaita)."""
    parts = raw.strip().split(":")
    if len(parts) not in (2, 3) or not all(p.isdigit() for p in parts):
        return None
    sec = 0
    for p in parts:
        sec = sec * 60 + int(p)
    return sec


def parse_debates(xml: bytes) -> tuple[str, list[dict], list[dict]] | None:
    """`-deb.xml` → (DK_ID, runātāju rindas, failures); None = sēdē debašu nebija.

    Fails bez `<DEBATES>` (182 B, `DK_STATUS 8`) ir tukša sēde, NAV kļūda.
    Punkts ar tukšu DEBATE_SURNAME = bez runātājiem, izlaiž. Ja sešu masīvu
    garumi atšķiras, viss DKP iet failures un NEVIENA tā rinda neglabājas
    (indeksu nobīde piesaistītu runu citam deputātam). Noteikums ir stingrs:
    tukšs lauks dod garumu 1 — reālajos failos lauki vienmēr ir `#`-papildināti.
    `faction` paliek neapstrādāts; normalizē store (T6).
    """
    root = ET.fromstring(xml)
    blocks = root.findall("DEBATES")
    if not blocks:
        return None
    rows: list[dict] = []
    failures: list[dict] = []
    for b in blocks:
        if not (b.findtext("DEBATE_SURNAME") or "").strip():
            continue
        arrays = {f: (b.findtext(f) or "").split("#") for f in DEBATE_FIELDS}
        lengths = {f: len(v) for f, v in arrays.items()}
        dkp_id = b.findtext("DKP_ID")
        if len(set(lengths.values())) != 1:
            failures.append({"kind": "array_length_mismatch", "dkp_id": dkp_id, "lengths": lengths})
            continue
        for i in range(lengths["DEBATE_SURNAME"]):
            rows.append({
                "dkp_id": dkp_id,
                "dkp_seq": b.findtext("DKP_SEQUENCE"),
                "document_nr": (b.findtext("LIVSDOCUMENTID") or "").strip() or None,
                "item_title": b.findtext("TITLE"),
                "speaker_order": i + 1,
                "speaker_name": f"{arrays['DEBATE_NAME'][i].strip()} {arrays['DEBATE_SURNAME'][i].strip()}".strip(),
                "faction": arrays["DEBATE_FRACTION"][i],
                "duration_sec": _duration_sec(arrays["DEBATE_TIME"][i]),
                "info": arrays["DEBATE_INFO"][i].strip() or None,
                "opinion": arrays["DEBATE_OPINION"][i].strip() or None,
            })
    return root.findtext("DK_ID"), rows, failures


def parse_dkp(xml: bytes) -> tuple[str | None, str | None, dict[str, dict]]:
    """`-dkp.xml` → (WORKSEQUENCEID = sēdes DK_ID, ISO DKDATE, {DKP_ID: {parent, doc_nr, title}})."""
    root = ET.fromstring(xml)
    dk = root.find("DK")
    items = {
        d.findtext("DKP_ID"): {
            "parent": (d.findtext("PARENTID") or "").strip(),
            "doc_nr": (d.findtext("LIVSDOCUMENTID") or "").strip(),
            "title": (d.findtext("TITLE") or "").strip(),
        }
        for d in root.findall("DKP")
    }
    if dk is None:
        return None, None, items
    return dk.findtext("WORKSEQUENCEID"), _iso_date(dk.findtext("DKDATE")), items


_TITLE_DOC_NR_RE = re.compile(rf"\((\d+/{BILL_SUFFIX})\)")


def resolve_parent(row: dict, items: dict[str, dict]) -> None:
    """Apakšpunkts («1. priekšlikums», procedūras punkts) bez dokumenta numura → vecāka numurs + nosaukums.

    Kāpj pa PARENTID, līdz senčam ir LIVSDOCUMENTID vai ķēde beidzas (cikla sargs).
    Vecāks nav dkp failā → rinda paliek kā ir (saucējs skaita document_nr NULL).
    """
    item = items.get(row["dkp_id"])
    if row["document_nr"] or item is None or not item["parent"]:
        return
    seen = {row["dkp_id"]}
    ancestor = None
    pid = item["parent"]
    while pid in items and pid not in seen:
        seen.add(pid)
        ancestor = items[pid]
        if ancestor["doc_nr"]:
            break
        pid = ancestor["parent"]
    if ancestor is None:
        return
    row["document_nr"] = ancestor["doc_nr"] or None
    row["item_title"] = f"{ancestor['title']} — {(row['item_title'] or '').strip()}"


def list_debate_resources(client: httpx.Client, convocation: int = SAEIMA_CONVOCATION) -> list[dict]:
    """CKAN → [{name, url, dkp_url}] sasaukuma `-deb` failiem; dkp_url None, ja blakus nav."""
    resp = client.get(CKAN_PACKAGE_URL)
    resp.raise_for_status()
    urls = {r["name"]: r["url"] for r in resp.json()["result"]["resources"]}
    return [{"name": name, "url": url, "dkp_url": urls.get(name[:-len("-deb")] + "-dkp")}
            for name, url in urls.items()
            if name.startswith(f"{convocation}.Saeimas") and name.endswith("-deb")]


def fetch_debates(client: httpx.Client, resources: list[dict]) -> tuple[list[dict], list[dict], int]:
    """Secīgi ielādē `-deb` failus (+ pilno `-dkp`). Atgriež (rindas, failures, tukšās sēdes).

    No blakus `-dkp.xml` (pārbaudīts pret DK_ID — pāris pēc vārda ir pieņēmums):
    sēdes datums = `DKDATE` un apakšpunktu vecāki (`resolve_parent`). Nav dkp vai
    cita sēde → session_date NULL, vecāki neizšķirti (rinda paliek, saucējs skaita).
    """
    rows: list[dict] = []
    failures: list[dict] = []
    empty = 0
    for res in resources:
        try:
            resp = client.get(res["url"])
            resp.raise_for_status()
            parsed = parse_debates(resp.content)
        except (httpx.HTTPError, ET.ParseError) as exc:
            failures.append({"kind": "fetch_error", "resource": res["name"], "error": str(exc)})
            continue
        if parsed is None:
            empty += 1
            continue
        dk_id, file_rows, file_failures = parsed
        failures.extend({**f, "resource": res["name"]} for f in file_failures)
        session_date = None
        if file_rows and res["dkp_url"]:
            try:
                resp = client.get(res["dkp_url"])
                resp.raise_for_status()
                dkp_dk_id, dkp_date, items = parse_dkp(resp.content)
            except (httpx.HTTPError, ET.ParseError, ValueError) as exc:
                failures.append({"kind": "fetch_error", "resource": res["name"] + " (dkp)", "error": str(exc)})
            else:
                if dkp_dk_id != dk_id:
                    failures.append({"kind": "sibling_mismatch", "resource": res["name"],
                                     "deb_dk_id": dk_id, "dkp_dk_id": dkp_dk_id})
                else:
                    session_date = dkp_date
                    for row in file_rows:
                        resolve_parent(row, items)
        for row in file_rows:
            if not row["document_nr"]:
                # Procedūras punkts bez vecāka («Par likumprojekta … (1552/Lp14)») nes numuru tikai nosaukumā.
                m = _TITLE_DOC_NR_RE.search(row["item_title"] or "")
                row["document_nr"] = m.group(1) if m else None
            row.update(session_name=res["name"][:-len("-deb")], session_date=session_date,
                       source_url=res["url"])
        rows.extend(file_rows)
    return rows, failures, empty


def store_debate_speeches(
    db_path: str | None,
    rows: list[dict],
    convocation: int = SAEIMA_CONVOCATION,
    name_index: dict[str, int] | None = None,
) -> ActivityResult:
    """Glabā debašu runātāju rindas; idempotents pēc (session_name, dkp_id, speaker_order).

    Punkts, kas pārnests uz citu sēdi, nes to pašu dkp_id. Ja citā sēdē tajā vietā ir
    tas pats runātājs ar to pašu ilgumu, tā ir tā pati runa (avots to atkārto) →
    skipped_existing; ja cits runātājs — cita runa, glabājas (2026-10-06: 20 atkārtojumi,
    2 īstas runas 23.07. ārkārtas sesijā, kas ar (dkp_id, speaker_order) atslēgu pazuda).

    `faction` TIKAI caur normalize_faction (T6 2. secinājums; vārti
    tests/test_faction_label_canonical.py). Nesaskaņots runātājs glabājas ar
    politician_id NULL un iet failures.
    """
    if name_index is None:
        name_index = _build_name_index(db_path)
    result = ActivityResult(parsed=len(rows))
    result.failures.extend(_match_rows(rows, name_index, "speaker_name"))

    db = get_db(db_path)
    try:
        for row in rows:
            repeated = db.execute(
                """SELECT 1 FROM saeima_debate_speeches
                   WHERE dkp_id = ? AND speaker_order = ? AND speaker_name = ?
                     AND duration_sec IS ? AND session_name != ?""",
                (row["dkp_id"], row["speaker_order"], row["speaker_name"],
                 row["duration_sec"], row["session_name"]),
            ).fetchone()
            if repeated:
                result.skipped_existing += 1
                continue
            cur = db.execute(
                """INSERT INTO saeima_debate_speeches
                   (convocation, session_name, session_date, dkp_id, dkp_seq, document_nr,
                    item_title, speaker_order, politician_id, speaker_name, faction,
                    duration_sec, info, opinion, source_url)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(session_name, dkp_id, speaker_order) DO NOTHING""",
                (convocation, row["session_name"], row["session_date"], row["dkp_id"],
                 row["dkp_seq"], row["document_nr"], row["item_title"], row["speaker_order"],
                 row["politician_id"], row["speaker_name"], normalize_faction(row["faction"]),
                 row["duration_sec"], row["info"], row["opinion"], row["source_url"]),
            )
            if cur.rowcount == 1:
                result.stored += 1
            else:
                result.skipped_existing += 1
        db.commit()
    finally:
        db.close()
    return result


# ---------------------------------------------------------------------------
# Jautājumi un pieprasījumi — titania LIVS{N}/SaeimaLIVS_LmP.nsf (3. uzdevums)
# ---------------------------------------------------------------------------

# kind → titania skats. Kind nāk no skata, ne no doc_nr sufiksa (J/P).
QUESTION_VIEWS = {"jautajums": "WEB_questions", "pieprasijums": "WEB_requests"}

# Nosaukumā ir iekavas («(iesniegts 08.12.2022.)»), tāpēc ķer piecus pēdiņu argumentus.
_DV_ROW_RE = re.compile(r'dvRow_LPView\("([^"]*)","([^"]*)","([^"]*)","([^"]*)","([^"]*)"\)')
_INFO_TR_RE = re.compile(r'<tr class="(headRowCT|infoRowCT)"[^>]*>(.*?)</tr>', re.S)
_TD_RE = re.compile(r"<td[^>]*>(.*?)</td>", re.S)
# «Adresāts:/Adresāti:», «Iesniedzējs:/Iesniedzēji:» — vērtība līdz <br>, nākamajam
# <font> vai </div>. Pēc etiķetes, ne pēc class="addBlock": pieprasījumā pirmais
# addBlock ir atbildīgā komisija.
_LABEL_RE = re.compile(r"<font[^>]*>([^<:]+):\s*</font>(.*?)(?=<br>|<font|</div>)", re.S)


def _livs_base(convocation: int) -> str:
    return f"https://titania.saeima.lv/LIVS{convocation}/SaeimaLIVS_LmP.nsf"


def question_list_url(kind: str, convocation: int = SAEIMA_CONVOCATION) -> str:
    return f"{_livs_base(convocation)}/{QUESTION_VIEWS[kind]}?OpenView&Count=1000"


def question_detail_url(unid: str, convocation: int = SAEIMA_CONVOCATION) -> str:
    return f"{_livs_base(convocation)}/0/{unid}?OpenDocument"


def _cell_text(fragment: str) -> str:
    text = re.sub(r"<[^>]+>", " ", re.sub(r"<br\s*/?>", " ", fragment, flags=re.I))
    return " ".join(unescape(text).split())


def parse_question_list(page: str, kind: str) -> list[dict]:
    """Saraksta skats → [{kind, status, title, doc_nr, unid}]; HTML entītijas atkodētas."""
    return [
        {"kind": kind, "status": unescape(st), "title": unescape(title),
         "doc_nr": unescape(nr), "unid": unid}
        for st, title, nr, unid, _ in _DV_ROW_RE.findall(page)
    ]


def parse_question_detail(page: str) -> dict:
    """Detaļas lapa → {submitted_date, result, submitters, addressees}.

    `submitted_date` = pirmā infoRowCT pirmā šūna (abos izkārtojumos: jautājuma
    4 kolonnas, pieprasījuma 7 — divas sēdes). `result` = visas ne-tukšās
    «Rezultāts» kolonnu šūnas pēc galvenes, savienotas ar «; ». Nav datuma →
    ValueError (paterna maiņa, T12).
    """
    header: list[str] = []
    info: list[list[str]] = []
    for cls, body in _INFO_TR_RE.findall(page):
        cells = [_cell_text(c) for c in _TD_RE.findall(body)]
        if cls == "headRowCT":
            header = cells
        else:
            info.append(cells)
    if not info or not info[0]:
        raise ValueError("detaļā nav infoRowCT rindas")
    result_cols = [i for i, h in enumerate(header) if h == "Rezultāts"]
    results = [row[i] for row in info for i in result_cols if i < len(row) and row[i]]

    labels = {_cell_text(lbl): _cell_text(val) for lbl, val in _LABEL_RE.findall(page)}
    submitters = next((v for k, v in labels.items() if k.startswith("Iesniedzēj")), "")
    addressees = next((v for k, v in labels.items() if k.startswith("Adresāt")), "")
    return {
        "submitted_date": _iso_date(info[0][0]),
        "result": "; ".join(results) or None,
        "submitters": [s.strip() for s in submitters.split(",") if s.strip()],
        "addressees": split_addressees(addressees),
    }


def split_addressees(raw: str) -> list[str]:
    """Adresātu virkne → ieraksti. Fragments, kas sākas ar mazo burtu, ir
    iepriekšējā amata turpinājums («Ministru prezidenta biedrs, tieslietu
    ministrs Jānis Bordāns») un tiek pievienots iepriekšējam."""
    entries: list[str] = []
    for part in (p.strip() for p in raw.split(",")):
        if not part:
            continue
        if entries and part[0].islower():
            entries[-1] = f"{entries[-1]}, {part}"
        else:
            entries.append(part)
    return entries


def addressee_person_name(entry: str) -> str | None:
    """«Iekšlietu ministrs Jānis Dombrava» → «Jānis Dombrava»; iestāde → None.

    Noteikums: beigu lielo burtu vārdu virkne (≥2) aiz pēdējā mazo burtu vārda.
    Latviešu amata nosaukums beidzas ar mazo burtu vārdu (ministrs, prezidents,
    priekšsēdētāja), iestāde arī («Valsts kontrole» → None). Trīsdaļīgi vārdi
    paliek veseli («Artūrs Toms Plešs», «Hosams Abu Meri»); dubultuzvārds ar
    defisi ir viens vārds. Kļūdas virziens ir redzams: kas izskatās pēc vārda,
    bet nav izsekots, nonāk unmatched_name failures, nevis klusi pazūd.
    """
    tokens = entry.split()
    run: list[str] = []
    for tok in reversed(tokens):
        if not tok[0].isupper():
            break
        run.insert(0, tok)
    return " ".join(run) if len(run) >= 2 else None



def question_links(row: dict, name_index: dict[str, int]) -> tuple[list[tuple[str, int]], list[dict]]:
    """Rinda → ([(role, politician_id)], failures). Tikai `_exact_match` (T1).

    Viens failures ieraksts uz katru gadījumu (ne uz unikālu vārdu), lai skaits
    rāda, cik saišu trūkst. Iestādes adresāts nav kļūda un failures neiet.
    """
    links: list[tuple[str, int]] = []
    failures: list[dict] = []
    names = [("submitter", n) for n in row["submitters"]]
    names += [("addressee", p) for p in map(addressee_person_name, row["addressees"]) if p]
    for role, name in names:
        pid = _exact_match(name_index, name)
        if pid is None:
            failures.append({"kind": "unmatched_name", "name": name, "role": role,
                             "doc_nr": row["doc_nr"]})
        else:
            links.append((role, pid))
    return links, failures


def fetch_question_list(client: httpx.Client, kind: str, convocation: int = SAEIMA_CONVOCATION) -> list[dict]:
    resp = client.get(question_list_url(kind, convocation))
    resp.raise_for_status()
    return parse_question_list(resp.text, kind)


def fetch_question_details(
    client: httpx.Client, items: list[dict], convocation: int = SAEIMA_CONVOCATION,
) -> tuple[list[dict], list[dict]]:
    """Secīgi ielādē katra saraksta ieraksta detaļu. Atgriež (rindas, failures).

    Neielādēta/neparsējama detaļa → `fetch_error`, rinda NEtiek glabāta (tikai
    saraksta dati bez datuma un personām būtu kluss robs). Atbilžu PDF netiek
    ielādēti — tikai detaļas URL.
    """
    rows: list[dict] = []
    failures: list[dict] = []
    for item in items:
        url = question_detail_url(item["unid"], convocation)
        try:
            resp = client.get(url)
            resp.raise_for_status()
            detail = parse_question_detail(resp.text)
        except (httpx.HTTPError, ValueError) as exc:
            failures.append({"kind": "fetch_error", "doc_nr": item["doc_nr"], "error": str(exc)})
            continue
        if not detail["submitters"]:
            failures.append({"kind": "no_submitters", "doc_nr": item["doc_nr"]})
        rows.append({**item, **detail, "source_url": url})
    return rows, failures


def store_questions(
    db_path: str | None,
    rows: list[dict],
    convocation: int = SAEIMA_CONVOCATION,
    name_index: dict[str, int] | None = None,
) -> ActivityResult:
    """Glabā jautājumus/pieprasījumus + personu saites.

    Pēc doc_nr: jauns → INSERT (`stored`); esošs → atjauno TIKAI status un result
    (tie mainās, kad atbild), `skipped_existing`. Nosaukums/datums/kind paliek.
    SELECT pirms INSERT, nevis `ON CONFLICT DO UPDATE`: tur rowcount ir 1 abos
    ceļos un lastrowid atjaunināšanā nav — nevarētu ne skaitīt, ne saistīt.
    Saites `ON CONFLICT DO NOTHING` — atkārtots skrējiens nedublē.
    """
    if name_index is None:
        name_index = _build_name_index(db_path)
    result = ActivityResult(parsed=len(rows))
    db = get_db(db_path)
    try:
        for row in rows:
            existing = db.execute("SELECT id FROM saeima_questions WHERE doc_nr = ?",
                                  (row["doc_nr"],)).fetchone()
            if existing:
                qid = existing["id"]
                db.execute("UPDATE saeima_questions SET status = ?, result = ? WHERE id = ?",
                           (row["status"], row["result"], qid))
                result.skipped_existing += 1
            else:
                cur = db.execute(
                    """INSERT INTO saeima_questions
                       (convocation, doc_nr, kind, title, status, submitted_date, result,
                        unid, source_url)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (convocation, row["doc_nr"], row["kind"], row["title"], row["status"],
                     row["submitted_date"], row["result"], row["unid"], row["source_url"]),
                )
                qid = cur.lastrowid
                result.stored += 1
            links, failures = question_links(row, name_index)
            result.failures.extend(failures)
            for role, pid in links:
                db.execute(
                    """INSERT INTO saeima_question_politicians (question_id, politician_id, role)
                       VALUES (?, ?, ?) ON CONFLICT(question_id, politician_id, role) DO NOTHING""",
                    (qid, pid, role),
                )
        db.commit()
    finally:
        db.close()
    return result
