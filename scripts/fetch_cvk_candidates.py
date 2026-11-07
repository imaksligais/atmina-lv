"""CVK 2026. gada Saeimas vēlēšanu kandidātu ziņu momentuzņēmums → data/bio/cvk_sv2026.yaml.

Plāns: docs/plans/2026-09-25-personu-bio.md § Task 1.

Tikai LASA DB (tracked_politicians, parties, vad_*). Tīkls: CVK alfabētiskais
saraksts + katra vārda trāpījuma VISI vārdabrāļi (≥1 s starp pieprasījumiem).

Privātums: neapstrādātais HTML (satur dzīvesvietu, tautību, īpašumus, naudu)
glabājas TIKAI `data/cvk_snapshots/SV2026/` (gitignored). Parseris izvelk vienīgi
baltā saraksta laukus (`BIO_FIELDS`) — pārējais lapā vienkārši netiek lasīts.

Sasaiste (T6/T13): aktīvs profils ar precīzi tādu pašu vārdu; pieņem tikai, ja
TIEŠI viens vārdabrālis ir sarakstā, kas atbilst `tracked_politicians.party`.
Jebkas cits → `status: review` ar iemeslu (renders review rindas nerāda).

Lietošana:
    .venv/Scripts/python.exe scripts/fetch_cvk_candidates.py [--refetch]
"""

from __future__ import annotations

import argparse
import re
import sys
import time
import unicodedata
from pathlib import Path

import httpx
import yaml
from bs4 import BeautifulSoup

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from src.coalition import lookup_party_short_name  # noqa: E402
from src.db import get_db, now_lv  # noqa: E402

BASE = "https://dati.cvk.lv/SV2026/"
LIST_URL = BASE + "kandidati/"
LISTS_URL = BASE + "kandidatu-saraksti/"
SNAPSHOT_DIR = REPO / "data" / "cvk_snapshots" / "SV2026"
OUT_PATH = REPO / "data" / "bio" / "cvk_sv2026.yaml"
# Operatora lēmumi par review rindām — pārdzīvo skripta atkārtotu palaišanu.
VERDICTS_PATH = REPO / "data" / "bio" / "cvk_sv2026_verdicts.yaml"
HEADERS = {"User-Agent": "atmina.lv political transparency research"}
REQUEST_GAP_S = 1.0

# Vienīgie lauki, kas no kandidāta lapas nonāk izvadē. Dzīvesvieta, tautība,
# ģimenes stāvoklis, īpašumi, transports, nauda, aizdevumi — NEKAD.
BIO_FIELDS = (
    "politician_id", "name", "cvk_id", "source_url", "fetched_at", "list_name",
    "birth_year", "education", "workplaces", "status", "reason",
)

# CVK saraksta nosaukums (breadcrumb, bez kārtas numura) → pieņemamie
# `parties.short_name`. Kopsaraksts pieņem jebkuru no dalībpartijām.
CVK_LIST_TO_PARTY: dict[str, tuple[str, ...]] = {
    "SUVERĒNĀ VARA / APVIENĪBA JAUNLATVIEŠI": ("SV-AJ",),
    '"Mēs mainām noteikumus"': ("MMN",),
    'Politisko partiju apvienība "Saskaņas Centrs"': ("SC",),
    "Zaļo un Zemnieku savienība": ("ZZS",),
    'Nacionālā apvienība "Visu Latvijai!"-"Tēvzemei un Brīvībai/LNNK"': ("NA",),
    '"Gobzema saraksts"': ("GS",),
    '"APVIENOTAIS SARAKSTS - Latvijas Zaļā partija, Latvijas Reģionu Apvienība, '
    'Liepājas partija"': ("AS", "LZP", "LRA"),
    "LATVIJA PIRMAJĀ VIETĀ": ("LPV",),
    "Jaunā VIENOTĪBA": ("JV",),
    "JKP Jaunā konservatīvā partija": ("JKP",),
    '"Latvijas attīstībai"': ("LA",),
    '"Austošā Saule Latvijai"': ("ASL",),
    'Politiskā partija "Stabilitātei!"': ("ST",),
    '"PROGRESĪVIE"': ("PRO",),
}

_WS = re.compile(r"\s+")
# Pēdiņas un domuzīmes: „Visu Latvijai!” – … ≡ "Visu Latvijai!" - …
_QUOTES = re.compile(r"[\"'“”„«»\-–—]")
_ID_RE = re.compile(r"kandidati/(\d+)-[^/]+/?$")
# Juridiskās formas un "LR" prefiksi netraucē darbavietu salīdzinājumam.
_LEGAL_NOISE = re.compile(
    r"\b(sia|as|biedrība|nodibinājums|pašvaldības|lr|latvijas republikas)\b"
)


def _clean(text: str | None) -> str:
    # NFKC: CVK tekstā ir tipogrāfiskās ligatūras ("kvaliﬁkācija" ar U+FB01).
    return _WS.sub(" ", unicodedata.normalize("NFKC", text or "")).strip()


def _int_or_none(text: str) -> int | None:
    text = _clean(text)
    return int(text) if text.isdigit() else None


def _strip_list_number(text: str) -> str:
    return re.sub(r"^\d+\.\s*", "", _clean(text))


# ── Parseri ──────────────────────────────────────────────────────────


def parse_candidate_list(html: str) -> list[dict]:
    """Alfabētiskais saraksts → [{cvk_id, name, url, list_name}]."""
    soup = BeautifulSoup(html, "lxml")
    out = []
    for tr in soup.select("#uxCandidatesTable tbody tr"):
        cells = tr.find_all("td")
        a = cells[0].find("a", href=True) if cells else None
        m = _ID_RE.search(a["href"]) if a else None
        if not m:
            raise ValueError(f"Nesaprotama kandidāta rinda: {_clean(tr.get_text(' '))[:120]}")
        out.append({
            "cvk_id": int(m.group(1)),
            "name": _clean(a.get_text()),
            "url": LIST_URL + a["href"].split("kandidati/", 1)[1],
            "list_name": _clean(cells[1].get_text()) if len(cells) > 1 else "",
        })
    return out


def parse_list_totals(html: str) -> int:
    """Kandidātu sarakstu lapa → kandidātu kopskaits (saucējs saraksta parserim)."""
    soup = BeautifulSoup(html, "lxml")
    total = 0
    for tr in soup.select("table tr"):
        cells = [_clean(c.get_text()) for c in tr.find_all("td")]
        if len(cells) == 3 and tr.find("a", href=re.compile(r"kandidatu-saraksti/")):
            total += int(cells[2])
    return total


def _table_rows(soup: BeautifulSoup, table_id: str) -> list[list[str]]:
    table = soup.find("table", id=table_id)
    if table is None:
        return []
    return [
        [_clean(td.get_text()) for td in tr.find_all("td")]
        for tr in table.select("tbody tr")
    ]


def parse_candidate_page(html: str) -> dict:
    """Kandidāta lapa → tikai baltā saraksta lauki.

    Lasa: saraksta nosaukumu (h6), dzimšanas gadu, izglītības un darbavietu
    tabulas. Visu pārējo (dzīvesvieta, tautība, ģimene, īpašumi, nauda) ignorē.
    """
    soup = BeautifulSoup(html, "lxml")
    h6 = soup.select_one("main h6")
    if h6 is None:
        raise ValueError("Kandidāta lapā nav saraksta virsraksta (h6)")
    birth_year = None
    for p in soup.select("main blockquote p"):
        strong = p.find("strong")
        if strong and _clean(strong.get_text()).startswith("Dzimšanas gads"):
            em = p.find("em")
            birth_year = _int_or_none(em.get_text() if em else "")
    education = [
        {"institution": r[0], "year": _int_or_none(r[1]), "degree": r[2] or None}
        for r in _table_rows(soup, "uxEducationTable") if len(r) >= 3 and r[0]
    ]
    # Tā pati tabula nes vai nu [Darbavieta | Amats], vai — kandidātam bez
    # darbavietas — vienu kolonnu [Nodarbošanās / statuss] ("Žurnālists").
    workplaces = [
        {"employer": r[0], "position": r[1] or None} if len(r) >= 2
        else {"employer": None, "position": r[0]}
        for r in _table_rows(soup, "uxEmploymentTable") if r and r[0]
    ]
    return {
        "list_name": _strip_list_number(h6.get_text()),
        "birth_year": birth_year,
        "education": education,
        "workplaces": workplaces,
    }


# ── Sasaiste ─────────────────────────────────────────────────────────


def choose_candidate(
    party_short: str | None, candidates: list[dict]
) -> tuple[dict | None, str | None]:
    """Izvēlas vārdabrāli, kura saraksts atbilst profila partijai.

    ``candidates`` — parsētas lapas ar ``cvk_id`` un ``list_name``.
    Atgriež (kandidāts, None) vai (None, review_iemesls).
    """
    unmapped = [c for c in candidates if c["list_name"] not in CVK_LIST_TO_PARTY]
    if unmapped:
        return None, "unmapped_list: " + "; ".join(c["list_name"] for c in unmapped)
    fits = [c for c in candidates if party_short in CVK_LIST_TO_PARTY[c["list_name"]]]
    if len(fits) == 1:
        return fits[0], None
    ids = ", ".join(str(c["cvk_id"]) for c in candidates)
    if len(fits) > 1:
        return None, f"homonym_ambiguous: {ids}"
    lists = "; ".join(c["list_name"] for c in candidates)
    return None, f"party_mismatch: profils={party_short or '—'}, CVK={lists} ({ids})"


def _norm_entity(text: str | None) -> str:
    t = _QUOTES.sub(" ", (text or "").casefold())
    t = _LEGAL_NOISE.sub(" ", t)
    return _WS.sub(" ", t).strip()


def workplaces_overlap(cvk_employers: list[str], vad_entities: list[str]) -> bool:
    """Vai kāda CVK darbavieta sakrīt ar deklarācijas iestādi (normalizēti)."""
    a = {_norm_entity(x) for x in cvk_employers if x} - {""}
    b = {_norm_entity(x) for x in vad_entities} - {""}
    for x in a:
        for y in b:
            if x == y or (min(len(x), len(y)) >= 5 and (x in y or y in x)):
                return True
    return False


def _latest_vad_entities(db, pid: int) -> list[str] | None:
    """Jaunākās deklarācijas iestādes (amatu tabula + deklarācijas iestāde).

    None = personai nav deklarāciju (krustpārbaude nav iespējama).
    """
    row = db.execute(
        "SELECT id, institution FROM vad_declarations WHERE opponent_id = ? "
        "ORDER BY COALESCE(declaration_year, CAST(substr(submitted_at, 1, 4) AS INTEGER)) DESC, "
        "submitted_at DESC LIMIT 1",
        (pid,),
    ).fetchone()
    if row is None:
        return None
    ents = [r[0] for r in db.execute(
        "SELECT entity_name FROM vad_positions WHERE declaration_id = ?", (row[0],)
    )]
    return ents + [row[1] or ""]


def load_verdicts(path: Path | None = None) -> dict[int, dict]:
    """politician_id → {cvk_id, status, note}. Nav faila → {}."""
    path = path or VERDICTS_PATH
    if not path.exists():
        return {}
    return {v["politician_id"]: v for v in yaml.safe_load(path.read_text(encoding="utf-8")) or []}


def apply_verdict(
    verdict: dict, parsed: list[dict], chosen: dict | None, reason: str | None
) -> tuple[dict | None, str | None]:
    """Operatora lēmums pārraksta automātisko: `status: ok` + `cvk_id`.

    Lēmums ir piesaistīts KONKRĒTAM cvk_id — ja tāda kandidāta sarakstā vairs
    nav (CVK pārnumurē), lēmums nenostrādā un rinda paliek review.
    """
    match = [c for c in parsed if c["cvk_id"] == verdict["cvk_id"]]
    if verdict.get("status") != "ok" or len(match) != 1:
        return chosen, reason or f"verdict_stale: cvk_id={verdict['cvk_id']}"
    return match[0], None


# ── Tīkls ────────────────────────────────────────────────────────────


class _Fetcher:
    def __init__(self, refetch: bool):
        self.refetch = refetch
        self.client = httpx.Client(headers=HEADERS, timeout=30, follow_redirects=True)
        self._last = 0.0
        self.network = 0
        self.cached = 0

    def get(self, url: str) -> str:
        wait = REQUEST_GAP_S - (time.monotonic() - self._last)
        if wait > 0:
            time.sleep(wait)
        resp = self.client.get(url)
        self._last = time.monotonic()
        resp.raise_for_status()
        self.network += 1
        return resp.text

    def candidate(self, cvk_id: int, url: str) -> str:
        path = SNAPSHOT_DIR / f"{cvk_id}.html"
        if path.exists() and not self.refetch:
            self.cached += 1
            return path.read_text(encoding="utf-8")
        html = self.get(url)
        path.write_text(html, encoding="utf-8")
        return html


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--refetch", action="store_true",
                    help="ielādēt kandidātu lapas no jauna, ignorējot momentuzņēmumus")
    args = ap.parse_args()
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    f = _Fetcher(args.refetch)
    listing = parse_candidate_list(f.get(LIST_URL))
    expected = parse_list_totals(f.get(LISTS_URL))
    print(f"CVK saraksts: {len(listing)} kandidāti parsēti (sarakstu lapā kopā {expected})")
    if len(listing) != expected:
        print("STOP: saraksta parseris neredz visus kandidātus", file=sys.stderr)
        return 1
    by_name: dict[str, list[dict]] = {}
    for c in listing:
        by_name.setdefault(c["name"], []).append(c)

    verdicts = load_verdicts()
    db = get_db(None)
    active = db.execute(
        "SELECT id, name, party FROM tracked_politicians "
        "WHERE relationship_type != 'inactive' ORDER BY id"
    ).fetchall()
    hits = [p for p in active if p["name"] in by_name]
    print(f"Aktīvie profili: {len(active)}; vārda trāpījumi: {len(hits)}")

    rows: list[dict] = []
    parse_failures: list[str] = []
    fetched_pages = 0
    for p in hits:
        parsed = []
        for c in by_name[p["name"]]:
            try:
                page = parse_candidate_page(f.candidate(c["cvk_id"], c["url"]))
                fetched_pages += 1
            except Exception as exc:  # noqa: BLE001 — katru kļūdu saskaita un ziņo
                parse_failures.append(f"{c['cvk_id']} {c['name']}: {exc}")
                continue
            parsed.append({**c, **page})
        if len(parsed) != len(by_name[p["name"]]):
            continue
        party_short = lookup_party_short_name(p["party"], db) if p["party"] else None
        chosen, reason = choose_candidate(party_short, parsed)
        verdict = verdicts.get(p["id"])
        if chosen is None and len(parsed) == 1:
            shown = parsed[0]  # unikāls vārds: dati operatora pārbaudei
        else:
            shown = chosen
        if chosen is not None:
            vad = _latest_vad_entities(db, p["id"])
            employers = [w["employer"] for w in chosen["workplaces"]]
            if vad is not None and not workplaces_overlap(employers, vad):
                reason = "workplace_mismatch: CVK=" + "; ".join(employers)
        if verdict:
            chosen, reason = apply_verdict(verdict, parsed, chosen, reason)
            shown = chosen or shown
        row = {
            "politician_id": p["id"],
            "name": p["name"],
            "cvk_id": shown["cvk_id"] if shown else None,
            "source_url": shown["url"] if shown else None,
            "fetched_at": now_lv(),
            "list_name": shown["list_name"] if shown else None,
            "birth_year": shown["birth_year"] if shown else None,
            "education": shown["education"] if shown else [],
            "workplaces": shown["workplaces"] if shown else [],
            "status": "review" if reason else "ok",
            "reason": reason,
        }
        assert tuple(row) == BIO_FIELDS
        rows.append(row)

    header = (
        "# CVK SV2026 kandidātu ziņas (kandidāta sniegtajā redakcijā) — ģenerēts ar\n"
        "# scripts/fetch_cvk_candidates.py. Renders rāda TIKAI status: ok.\n"
        "# Review rindu operators var pārslēgt uz ok pēc pārbaudes (reason → null).\n"
    )
    OUT_PATH.write_text(
        header + yaml.safe_dump(rows, allow_unicode=True, sort_keys=False, width=1000),
        encoding="utf-8",
    )

    ok = [r for r in rows if r["status"] == "ok"]
    review = [r for r in rows if r["status"] == "review"]
    print(f"Lapas: {fetched_pages} parsētas ({f.network - 2} no tīkla, {f.cached} no momentuzņēmumiem)")
    print(f"Pieņemti (ok): {len(ok)}; review: {len(review)}; parse kļūdas: {len(parse_failures)}")
    by_reason: dict[str, int] = {}
    for r in review:
        by_reason[r["reason"].split(":")[0]] = by_reason.get(r["reason"].split(":")[0], 0) + 1
    for k, v in sorted(by_reason.items()):
        print(f"  review {k}: {v}")
    for r in review:
        print(f"  - {r['politician_id']} {r['name']}: {r['reason']}")
    for msg in parse_failures:
        print(f"  PARSE: {msg}", file=sys.stderr)
    print(f"→ {OUT_PATH.relative_to(REPO)}")
    return 1 if parse_failures else 0


if __name__ == "__main__":
    sys.exit(main())
