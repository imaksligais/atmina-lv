"""Profila galvenes bio: CVK kandidāta ziņas + amati pēc VID deklarācijām.

Plāns: docs/plans/2026-09-25-personu-bio.md § Task 2. Bez brīva teksta —
tikai strukturēti fakti ar avotu:

- ``data/bio/cvk_sv2026.yaml`` (scripts/fetch_cvk_candidates.py) — dzimšanas
  gads, izglītība, CVK darbavietas (pašreizējie amati, kandidāta redakcijā). Lasa TIKAI ``status: ok`` rindas; review
  rindas (vārdabrālis, partijas vai darbavietas nesakritība) netiek rādītas.
- ``vad_positions`` ⨝ ``vad_declarations`` — amati pa deklarāciju gadiem. Gads =
  ``declaration_year`` vai ``submitted_at`` gads (starpposma deklarācijām gada
  nav). Rakstības varianti ("LATVIJAS REPUBLIKAS SAEIMA" / "Latvijas Republikas
  Saeima", pēdiņas) apvienojas vienā rindā ar diapazonu min–max. Diapazons ir
  deklarāciju gadi, NE precīzi amata sākuma/beigu datumi — tā to arī nosauc UI.
- ``data/bio/ep_deputati.yaml`` (roku darbs, 2026-10-08) — EP deputātiem, kuri
  2026. g. nekandidēja: dzimšanas gads + izglītība no oficiālās deputāta lapas
  europarl.europa.eu (``source_url`` katram). Aizpilda TIKAI laukus, kuru CVK
  ierakstā nav; CVK paliek primārais avots.
"""

from __future__ import annotations

import re
import sqlite3
import sys
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from src.render._common.constants import PROJECT_ROOT

CVK_BIO_PATH = PROJECT_ROOT / "data" / "bio" / "cvk_sv2026.yaml"
EP_BIO_PATH = PROJECT_ROOT / "data" / "bio" / "ep_deputati.yaml"
SAEIMA_MANDATE_PATH = PROJECT_ROOT / "data" / "bio" / "saeima_mandats.yaml"

# docs/plans/2026-10-09-saeima-mandata-piezime.md § Teikumi.
_MANDATE_TEMPLATES = {
    "ministrs": "Ir {office}. Deputāta mandātu nolika {since} uz amata laiku, "
                "tāpēc Saeimā nebalso.",
    # «14.» burtiski, ne SAEIMA_CONVOCATION: fails apraksta tieši 14. Saeimu un
    # pēc pārslēgšanas nedrīkst sākt teikt «15. Saeimā».
    "cits_amats": "Ir {office}. Pilnvaras 14. Saeimā beidzās {since}.",
    "pilnvaras_beidzas": "Pilnvaras 14. Saeimā beidzās {since}.",
}
_CAST_BALLOTS = ("Par", "Pret", "Atturas", "Nebalsoja")

_QUOTES = re.compile(r"[\"'“”„«»]")
_WS = re.compile(r"\s+")


def _load_ok_rows(path: Path) -> dict[int, dict[str, Any]]:
    if not path.exists():
        return {}
    rows = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    return {r["politician_id"]: r for r in rows if r.get("status") == "ok"}


def load_cvk_bio(path: Path | None = None) -> dict[int, dict[str, Any]]:
    """politician_id → CVK ieraksts; tikai ``status: ok``. Nav faila → {}."""
    return _load_ok_rows(path or CVK_BIO_PATH)


def load_ep_bio(path: Path | None = None) -> dict[int, dict[str, Any]]:
    """politician_id → EP deputāta lapas ieraksts; tikai ``status: ok``. Nav faila → {}."""
    return _load_ok_rows(path or EP_BIO_PATH)


def _key(text: str | None) -> str:
    return _WS.sub(" ", _QUOTES.sub(" ", (text or "").casefold())).strip()


def _pick_text(variants: list[tuple[int, str]]) -> str:
    """Jaunākais variants; priekšroka "Parastai" rakstībai pār VERSALIJĀM/mazajiem."""
    ordered = sorted(variants, key=lambda v: (v[1].isupper(), v[1][:1].islower(), -v[0]))
    return ordered[0][1]


def merge_career(rows: list[tuple[int, str | None, str | None]]) -> list[dict[str, Any]]:
    """[(gads, amats, iestāde)] → apvienotas rindas, jaunākās pirmās.

    Atslēga = (amats, iestāde) bez reģistra/pēdiņām/liekām atstarpēm; teksts
    paliek avota redakcijā (tikai liekās atstarpes noņemtas).
    """
    groups: dict[tuple[str, str], dict[str, Any]] = {}
    for year, title, entity in rows:
        title, entity = _WS.sub(" ", title or "").strip(), _WS.sub(" ", entity or "").strip()
        if year is None or not (title or entity):
            continue
        g = groups.setdefault((_key(title), _key(entity)), {"years": set(), "t": [], "e": []})
        g["years"].add(year)
        g["t"].append((year, title))
        g["e"].append((year, entity))
    out = []
    for g in groups.values():
        first, last = min(g["years"]), max(g["years"])
        out.append({
            "position": _pick_text(g["t"]),
            "entity": _pick_text(g["e"]),
            "first": first,
            "last": last,
            "years": str(first) if first == last else f"{first}–{last}",
        })
    out.sort(key=lambda r: (-r["last"], -r["first"], r["position"].casefold()))
    return out


def fetch_career(db: sqlite3.Connection, pids: list[int]) -> dict[int, list[dict[str, Any]]]:
    """Viens vaicājums visiem profiliem; nav VAD tabulu → {}."""
    if not pids:
        return {}
    placeholders = ",".join("?" * len(pids))
    # Tikai `vad_positions`: deklarācijas galvene (institution) ministriem ir
    # Valsts kanceleja, ne darbavieta — to NEjauc klāt (2026-09-25 pārskats).
    try:
        rows = db.execute(
            f"SELECT d.opponent_id, "
            f"COALESCE(d.declaration_year, CAST(substr(d.submitted_at, 1, 4) AS INTEGER)), "
            f"p.position_title, p.entity_name "
            f"FROM vad_positions p JOIN vad_declarations d ON d.id = p.declaration_id "
            f"WHERE d.opponent_id IN ({placeholders})",
            pids,
        ).fetchall()
    except sqlite3.OperationalError:
        return {}
    by_pid: dict[int, list[tuple]] = {}
    for pid, year, title, entity in rows:
        by_pid.setdefault(pid, []).append((year, title, entity))
    return {pid: merge_career(r) for pid, r in by_pid.items()}


def build_bio(
    cvk: dict[str, Any] | None,
    career: list[dict[str, Any]],
    ep: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Galvenes bloka dati; None, ja nav neviena fakta (bloks paslēpts).

    ``cvk`` jau ir filtrēts uz ``status: ok`` (``load_cvk_bio``). Pašreizējās
    darbavietas nāk no CVK; VID amati ir tikai vēsture (sakļauta). ``ep``
    (``load_ep_bio``) aizpilda dzimšanas gadu / izglītību tikai tad, ja CVK
    to nav; ``ep_url`` tiek rādīts «Avoti» tikai, ja EP lauks tiešām lietots.
    """
    cvk = cvk or {}
    ep = ep or {}
    birth_year = cvk.get("birth_year") or ep.get("birth_year")
    education = cvk.get("education") or ep.get("education") or []
    used_ep = bool(
        (not cvk.get("birth_year") and ep.get("birth_year"))
        or (not cvk.get("education") and ep.get("education"))
    )
    bio = {
        "birth_year": birth_year,
        "education": education,
        "workplaces": cvk.get("workplaces") or [],
        "career": career,
        "cvk_url": cvk.get("source_url"),
        "ep_url": ep.get("source_url") if used_ep else None,
    }
    if not (bio["birth_year"] or bio["education"] or bio["workplaces"] or career):
        return None
    return bio


def _mandate_warn(msg: str) -> None:
    print(f"[saeima_mandats] {msg}", file=sys.stderr)


def _parse_mandate_entries(path: Path) -> dict[int, tuple[str, str]]:
    """pid → (since ISO, teikums). Nederīgs ieraksts → viena stderr rinda, izlaists."""
    if not path.exists():
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        entries = data.get("entries") or []
    except (yaml.YAMLError, AttributeError) as exc:
        _mandate_warn(f"{path.name} nav nolasāms ({exc}); piezīmes netiek rādītas")
        return {}
    out: dict[int, tuple[str, str]] = {}
    for i, e in enumerate(entries):
        pid = e.get("pid") if isinstance(e, dict) else None
        if not isinstance(pid, int) or isinstance(pid, bool):
            _mandate_warn(f"ieraksts #{i}: nav vesela skaitļa pid; izlaists")
            continue
        kind = e.get("kind")
        if kind not in _MANDATE_TEMPLATES:
            _mandate_warn(f"pid {pid}: nezināms kind {kind!r}; izlaists")
            continue
        try:
            since = date.fromisoformat(str(e.get("since") or "")[:10])
        except ValueError:
            _mandate_warn(f"pid {pid}: nav derīga since datuma; izlaists")
            continue
        office = (e.get("office") or "").strip()
        if kind != "pilnvaras_beidzas" and not office:
            _mandate_warn(f"pid {pid}: kind {kind} bez office; izlaists")
            continue
        if pid in out:
            _mandate_warn(f"pid {pid}: dublēts ieraksts; paturēts pirmais")
            continue
        sentence = _MANDATE_TEMPLATES[kind].format(since=since.strftime("%d.%m.%Y"), office=office)
        out[pid] = (since.isoformat(), sentence)
    return out


def load_mandate_notes(db: sqlite3.Connection, pids: list[int]) -> dict[int, str]:
    """pid → Saeimā cilnes teikums, kāpēc balsojumi beidzas (``data/bio/saeima_mandats.yaml``).

    Novecošanas sargs: ja politiķim ir nodota balss (Par/Pret/Atturas/Nebalsoja)
    sēdē PĒC ``since``, teikums vairs nav patiess → netiek rādīts, stderr rinda
    ar pid un vēlāko datumu. Viens vaicājums visiem ierakstiem.
    """
    wanted = set(pids)
    entries = {pid: v for pid, v in _parse_mandate_entries(SAEIMA_MANDATE_PATH).items()
               if pid in wanted}
    if not entries:
        return {}
    listed = sorted(entries)
    try:
        last_cast = dict(db.execute(
            f"SELECT iv.politician_id, MAX(v.vote_date) "
            f"FROM saeima_individual_votes iv JOIN saeima_votes v ON v.id = iv.vote_id "
            f"WHERE iv.politician_id IN ({','.join('?' * len(listed))}) "
            f"AND iv.vote IN ({','.join('?' * len(_CAST_BALLOTS))}) "
            f"GROUP BY iv.politician_id",
            [*listed, *_CAST_BALLOTS],
        ).fetchall())
    except sqlite3.OperationalError as exc:
        # Bez sarga teikums var būt nepatiess — labāk nerādīt nevienu.
        _mandate_warn(f"sargs neizpildās ({exc}); piezīmes netiek rādītas")
        return {}
    out = {}
    for pid, (since, sentence) in entries.items():
        later = last_cast.get(pid)
        if later and later[:10] > since:
            _mandate_warn(f"pid {pid}: nodota balss {later[:10]} pēc since {since}; teikums slēpts")
            continue
        out[pid] = sentence
    return out


def load_bios(db: sqlite3.Connection, pids: list[int]) -> dict[int, dict[str, Any]]:
    """pid → bio bloks visiem profiliem ar vismaz vienu faktu."""
    cvk = load_cvk_bio()
    ep = load_ep_bio()
    career = fetch_career(db, pids)
    out = {}
    for pid in pids:
        bio = build_bio(cvk.get(pid), career.get(pid, []), ep.get(pid))
        if bio:
            out[pid] = bio
    return out
