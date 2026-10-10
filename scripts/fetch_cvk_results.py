"""CVK 15. Saeimas vēlēšanu (2026-10-03) rezultāti → data/cvk_sv2026_rezultati.yaml.

Lasa CVK statisko rezultātu lapu (provizoriskie dati, kamēr skaitīšana nav
pabeigta), saglabā neapstrādāto HTML `data/cvk_snapshots/SV2026/` (gitignored)
un raksta komitējamu YAML, ko `src/render/parties.py` rāda partijas.html.

Formāta maiņa NEDRĪKST radīt tukšu vai daļēju rezultātu (T12): ja nav atrasta
iecirkņu norāde, atjaunināšanas laiks vai sarakstu tabula, ja rindu nav 14 vai
vietu summa ≠ ievēlamo deputātu skaitam — STOP ar izejas kodu 1, YAML netiek
pārrakstīts.

Sasaiste ar `parties.id` ir TIKAI pēc saraksta numura (`LIST_TO_PARTY_ID`),
nekad pēc nosaukuma. DB tiek atvērta tikai lasīšanai (pārbauda, vai id eksistē).

`official` ir operatora lauks: skripts to pārnes no esošā YAML (sākumā false) —
CVK oficiālo apstiprinājumu atzīmē ar roku.

Lietošana:
    .venv/Scripts/python.exe scripts/fetch_cvk_results.py [--from-file PATH]
"""

from __future__ import annotations

import argparse
import re
import sqlite3
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

import httpx
import yaml
from bs4 import BeautifulSoup

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from src.db import DB_PATH, now_lv  # noqa: E402

RESULTS_URL = "https://dati.cvk.lv/SV2026/velesanu-rezultati/"
SNAPSHOT_DIR = REPO / "data" / "cvk_snapshots" / "SV2026"
OUT_PATH = REPO / "data" / "cvk_sv2026_rezultati.yaml"
# CVK serveris bez pārlūka UA atbild ar tukšu lapu.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36 (atmina.lv research)"
    )
}
EXPECTED_LISTS = 14

# CVK saraksta Nr. → parties.id. Kopsaraksts Nr. 7 (LZP+LRA+Liepājas partija)
# piesaistīts tikai Apvienotajam sarakstam (id 6).
LIST_TO_PARTY_ID: dict[int, int] = {
    1: 19,   # SUVERĒNĀ VARA / APVIENĪBA JAUNLATVIEŠI
    2: 7,    # "Mēs mainām noteikumus"
    3: 17,   # Saskaņas Centrs
    4: 3,    # ZZS
    5: 4,    # Nacionālā apvienība
    6: 18,   # "Gobzema saraksts"
    7: 6,    # APVIENOTAIS SARAKSTS
    8: 5,    # LATVIJA PIRMAJĀ VIETĀ
    9: 1,    # Jaunā VIENOTĪBA
    10: 15,  # JKP
    11: 8,   # "Latvijas attīstībai"
    12: 16,  # "Austošā Saule Latvijai"
    13: 9,   # "Stabilitātei!"
    14: 2,   # "PROGRESĪVIE"
}

_WS = re.compile(r"\s+")
_PRECINCTS_RE = re.compile(r"Dati par (\d+) no (\d+) iecirkņiem")
_UPDATED_RE = re.compile(
    r"Pēdējais atjauninājums veikts:\s*(\d{2})\.(\d{2})\.(\d{4})\.?\s*plkst\.\s*(\d{1,2}):(\d{2})"
)
_COUNT_PCT_RE = re.compile(r"^([\d ]+?)\s*\(([\d,]+)%\)$")


class CvkFormatError(ValueError):
    """Lapa neatbilst gaidītajam formātam — nekad nerakstīt daļēju rezultātu."""


def _clean(text: str | None) -> str:
    return _WS.sub(" ", unicodedata.normalize("NFKC", text or "")).strip()


def parse_lv_int(text: str) -> int:
    """'1 557 615' / '1\xa0557\xa0615' → 1557615. Kļūda, ja nav tikai cipari."""
    digits = re.sub(r"\s", "", unicodedata.normalize("NFKC", text or ""))
    if not digits.isdigit():
        raise CvkFormatError(f"Nav vesels skaitlis: {text!r}")
    return int(digits)


def parse_lv_pct(text: str) -> float:
    """'35,338%' → 35.338."""
    t = re.sub(r"\s", "", unicodedata.normalize("NFKC", text or "")).rstrip("%")
    try:
        return float(t.replace(",", "."))
    except ValueError as exc:
        raise CvkFormatError(f"Nav procentu skaitlis: {text!r}") from exc


def _blockquote_fields(soup: BeautifulSoup) -> dict[str, str]:
    out = {}
    for p in soup.select("main blockquote p"):
        strong, em = p.find("strong"), p.find("em")
        if strong and em:
            out[_clean(strong.get_text()).rstrip(":").strip()] = _clean(em.get_text())
    return out


def _count_with_pct(fields: dict[str, str], label: str) -> tuple[int, float]:
    raw = fields.get(label)
    if raw is None:
        raise CvkFormatError(f"Kopsavilkumā nav lauka «{label}»")
    m = _COUNT_PCT_RE.match(raw)
    if not m:
        raise CvkFormatError(f"«{label}» neatbilst formātam 'N (P%)': {raw!r}")
    return parse_lv_int(m.group(1)), parse_lv_pct(m.group(2))


def parse_results(html: str) -> dict:
    """CVK rezultātu lapa → strukturēts rezultāts. Trūkstošs elements → CvkFormatError."""
    soup = BeautifulSoup(html, "lxml")

    table = soup.find("table", id="result-candidate-table")
    if table is None:
        raise CvkFormatError("Nav atrasta sarakstu tabula #result-candidate-table")

    # Iecirkņu norāde — TIKAI no sarakstu tabulas (apgabalu tabulas kājene var
    # atpalikt par vienu iecirkni, piem., 1023 pret 1024).
    tip = table.select_one("[data-bs-title]")
    m = _PRECINCTS_RE.search(_clean(tip["data-bs-title"])) if tip else None
    if not m:
        raise CvkFormatError("Nav atrasta iecirkņu norāde «Dati par X no Y iecirkņiem»")
    counted, total = int(m.group(1)), int(m.group(2))

    m = _UPDATED_RE.search(_clean(soup.get_text(" ")))
    if not m:
        raise CvkFormatError("Nav atrasts «Pēdējais atjauninājums veikts: …» laiks")
    dd, mm, yyyy, hh, mi = m.groups()
    cvk_updated_at = f"{yyyy}-{mm}-{dd} {int(hh):02d}:{mi}"

    fields = _blockquote_fields(soup)
    try:
        eligible = parse_lv_int(fields["Balsstiesīgie"])
        seats_total = parse_lv_int(fields["Ievēlamo deputātu skaits"])
    except KeyError as exc:
        raise CvkFormatError(f"Kopsavilkumā nav lauka «{exc.args[0]}»") from exc
    voted, turnout_pct = _count_with_pct(fields, "Nobalsojušie")
    valid_env, valid_env_pct = _count_with_pct(fields, "Derīgās aploksnes")
    valid_marks, valid_marks_pct = _count_with_pct(fields, "Derīgās zīmes")

    lists = []
    for tr in table.select("tbody tr"):
        tds = tr.find_all("td")
        if len(tds) != 5:
            raise CvkFormatError(f"Sarakstu tabulas rindā {len(tds)} šūnas, gaidītas 5")
        nr = parse_lv_int(tds[0].get_text())
        votes = parse_lv_int(tds[2].get_text())
        pct = parse_lv_pct(tds[3].get_text())
        seats = parse_lv_int(tds[4].get_text())
        # Mašīnlasāmā data-order vērtība ir neatkarīga otrā redakcija.
        for td, val in ((tds[2], votes), (tds[3], pct), (tds[4], seats)):
            order = td.get("data-order")
            if order is not None and abs(float(order) - val) > 1e-9:
                raise CvkFormatError(
                    f"Saraksts {nr}: teksts {val} ≠ data-order {order}"
                )
        lists.append({
            "list_nr": nr,
            "cvk_name": _clean(tds[1].get_text()),
            "votes": votes,
            "percent": pct,
            "seats": seats,
        })
    if not lists:
        raise CvkFormatError("Sarakstu tabula ir tukša")

    regions = []
    stat = soup.find("table", id="result-stat-table")
    if stat is not None:
        for tr in stat.select("tbody tr"):
            tds = [_clean(td.get_text()) for td in tr.find_all("td")]
            if len(tds) != 5:
                continue
            tip_r = tr.select_one("[data-bs-title]")
            mr = _PRECINCTS_RE.search(_clean(tip_r["data-bs-title"])) if tip_r else None
            regions.append({
                "name": tds[0],
                "eligible": parse_lv_int(tds[1]),
                "voted": parse_lv_int(tds[2]),
                "valid_envelopes": parse_lv_int(tds[3]),
                "valid_marks": parse_lv_int(tds[4]),
                "precincts_counted": int(mr.group(1)) if mr else None,
                "precincts_total": int(mr.group(2)) if mr else None,
            })

    return {
        "cvk_updated_at": cvk_updated_at,
        "precincts_counted": counted,
        "precincts_total": total,
        "eligible_voters": eligible,
        "voted": voted,
        "turnout_percent": turnout_pct,
        "valid_envelopes": valid_env,
        "valid_envelopes_percent": valid_env_pct,
        "valid_marks": valid_marks,
        "valid_marks_percent": valid_marks_pct,
        "seats_total": seats_total,
        "lists": lists,
        "regions": regions,
    }


def validate(result: dict, expected_lists: int = EXPECTED_LISTS) -> None:
    """Pilnīguma vārti: rindu skaits, numuri, vietu summa. Pārkāpums → CvkFormatError."""
    lists = result["lists"]
    if len(lists) != expected_lists:
        raise CvkFormatError(f"Sarakstu tabulā {len(lists)} rindas, gaidītas {expected_lists}")
    nrs = sorted(x["list_nr"] for x in lists)
    if nrs != list(range(1, expected_lists + 1)):
        raise CvkFormatError(f"Saraksta numuri nav 1..{expected_lists}: {nrs}")
    seat_sum = sum(x["seats"] for x in lists)
    if seat_sum != result["seats_total"]:
        raise CvkFormatError(
            f"Vietu summa {seat_sum} ≠ ievēlamo deputātu skaits {result['seats_total']}"
        )
    if not 0 < result["precincts_counted"] <= result["precincts_total"]:
        raise CvkFormatError(
            f"Neticams iecirkņu skaits {result['precincts_counted']}/{result['precincts_total']}"
        )


def attach_party_ids(lists: list[dict], known_party_ids: set[int]) -> None:
    for x in lists:
        pid = LIST_TO_PARTY_ID.get(x["list_nr"])
        if pid is None:
            raise CvkFormatError(f"Sarakstam Nr. {x['list_nr']} nav party_id kartējuma")
        if pid not in known_party_ids:
            raise CvkFormatError(
                f"Saraksts Nr. {x['list_nr']} → parties.id={pid}, bet tāda id DB nav"
            )
        x["party_id"] = pid


def _known_party_ids() -> set[int]:
    path = Path(DB_PATH)
    path = path if path.is_absolute() else REPO / path
    conn = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    try:
        return {r[0] for r in conn.execute("SELECT id FROM parties")}
    finally:
        conn.close()


def _previous_official(path: Path) -> bool:
    if not path.exists():
        return False
    prev = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return bool(prev.get("official", False))


def build_document(result: dict, fetched_at: str, official: bool) -> dict:
    counted, total = result["precincts_counted"], result["precincts_total"]
    return {
        "source_url": RESULTS_URL,
        "fetched_at": fetched_at,
        "cvk_updated_at": result["cvk_updated_at"],
        "precincts_counted": counted,
        "precincts_total": total,
        "provisional": counted < total or not official,
        "official": official,
        "eligible_voters": result["eligible_voters"],
        "voted": result["voted"],
        "turnout_percent": result["turnout_percent"],
        "valid_envelopes": result["valid_envelopes"],
        "valid_marks": result["valid_marks"],
        "seats_total": result["seats_total"],
        "lists": [
            {k: x[k] for k in ("list_nr", "cvk_name", "votes", "percent", "seats", "party_id")}
            for x in result["lists"]
        ],
        "regions": result["regions"],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--from-file", type=Path,
                    help="parsēt saglabātu HTML (bez tīkla, bez jauna momentuzņēmuma)")
    args = ap.parse_args()

    if args.from_file:
        html = args.from_file.read_text(encoding="utf-8")
        snap = args.from_file
    else:
        resp = httpx.get(RESULTS_URL, headers=HEADERS, timeout=30, follow_redirects=True)
        resp.raise_for_status()
        html = resp.text
        SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
        snap = SNAPSHOT_DIR / f"rezultati_{datetime.now():%Y%m%d_%H%M%S}.html"
        snap.write_text(html, encoding="utf-8")

    try:
        result = parse_results(html)
        validate(result)
        attach_party_ids(result["lists"], _known_party_ids())
    except CvkFormatError as exc:
        print(f"STOP (T12 — formāta maiņa vai nepilnīgi dati): {exc}", file=sys.stderr)
        print(f"Momentuzņēmums: {snap}", file=sys.stderr)
        print(f"{OUT_PATH.relative_to(REPO)} NETIKA pārrakstīts.", file=sys.stderr)
        return 1

    doc = build_document(result, now_lv(), _previous_official(OUT_PATH))
    header = (
        "# CVK 15. Saeimas vēlēšanu (2026-10-03) rezultāti — ģenerēts ar\n"
        "# scripts/fetch_cvk_results.py. `official` operators pārslēdz ar roku pēc\n"
        "# CVK oficiālā apstiprinājuma; skripts to pārnes nemainītu.\n"
    )
    OUT_PATH.write_text(
        header + yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, width=1000),
        encoding="utf-8",
    )

    lists = sorted(doc["lists"], key=lambda x: -x["votes"])
    above = [x for x in lists if x["percent"] >= 5]
    print(f"CVK atjaunināts: {doc['cvk_updated_at']}; iecirkņi {doc['precincts_counted']}/"
          f"{doc['precincts_total']}; provizoriski: {doc['provisional']}; oficiāli: {doc['official']}")
    print(f"Nobalsojuši {doc['voted']}/{doc['eligible_voters']} ({doc['turnout_percent']}%); "
          f"derīgās zīmes {doc['valid_marks']}")
    print(f"Saraksti: {len(lists)}/{EXPECTED_LISTS} parsēti; virs 5 %: {len(above)}; "
          f"vietas {sum(x['seats'] for x in lists)}/{doc['seats_total']}; "
          f"apgabali: {len(doc['regions'])}")
    for x in lists:
        print(f"  {x['list_nr']:>2} pid={x['party_id']:>2} {x['percent']:>7.3f}% "
              f"{x['votes']:>7} {x['seats']:>3}  {x['cvk_name'][:60]}")
    print(f"Momentuzņēmums: {snap}")
    print(f"→ {OUT_PATH.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
