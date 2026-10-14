"""Render saeima.html — 15. Saeimas pusloks (sēdvietu karte ar četrām lēcām).

Spec: docs/superpowers/specs/2026-10-08-saeimas-pusloks-design.md.

Sastāvs = ievēlēto saraksta fails (šobrīd PROVIZORISKS CVK aprēķins); saraksta
nosaukums un krāsa = CVK rezultātu fails + ``parties``. Sasaiste ar profilu —
TIKAI precīzs pilnais ``tracked_politicians.name`` (T1: nekādu apakšvirkņu) un
tikai tiem, kam profila lapa tiešām tiek renderēta (tas pats WHERE kā
``_fetch_politicians``), lai sēdvieta nekad nevestu uz 404.

Visas lēcu vērtības aprēķina šeit; lapa bez JS rāda «Saraksta» lēcu un strādā.
``assets/slv1.js`` tikai pārslēdz ``data-lens`` un atver kartīti.
"""

from __future__ import annotations

import math
import sqlite3
from pathlib import Path
from typing import Any

from jinja2 import Environment

from src.render._common import (
    ASSETS_DIR,
    _lv_number,
    _lv_plural,
    _render_page,
    _slugify,
    trailing_days_cutoff,
)
from src.render._common.constants import PROJECT_ROOT
from src.render._common.cvk import read_elected, read_election_results

# Testi (test_render_chars, test_render_saeima) abus pārsien uz fixture kopijām.
ELECTED_PATH = PROJECT_ROOT / "data" / "cvk_sv2026_ievēlētie.yaml"
RESULTS_PATH = PROJECT_ROOT / "data" / "cvk_sv2026_rezultati.yaml"

SEATS_TOTAL = 100
POSITIONS_WINDOW_DAYS = 90

# Pusloka ģeometrija: 6 rindas, iekšējais rādiuss 0,36 no ārējā. Sēdvietas
# rindā ∝ rindas rādiusam, tāpēc attālumi starp apļiem visās rindās ~vienādi
# (min ~0,128 vienības; redzamais aplis 0,05, trāpījuma aplis 0,064).
_ROWS = 6
_R_INNER = 0.36
_SCALE = 200  # SVG vienības uz rādiusu 1
_DOT_R = 0.05
_HIT_R = 0.064


def _arc_positions(n: int) -> list[tuple[float, float]]:
    """n sēdvietu (x, y) SVG koordinātās, sakārtotas no kreisās uz labo.

    Kārtošana pēc leņķa (π → 0) visās rindās kopā dod saraksta «ķīli» no
    centra uz āru — tāpat kā parlamenta diagrammās.
    """
    radii = [_R_INNER + (1 - _R_INNER) * i / (_ROWS - 1) for i in range(_ROWS)]
    total_r = sum(radii)
    raw = [n * r / total_r for r in radii]
    counts = [math.floor(x) for x in raw]
    for i in sorted(range(_ROWS), key=lambda i: -(raw[i] - counts[i]))[: n - sum(counts)]:
        counts[i] += 1
    seats: list[tuple[float, int, float, float]] = []
    for row, (r, k) in enumerate(zip(radii, counts, strict=True)):
        for j in range(k):
            theta = math.pi * (1 - j / (k - 1)) if k > 1 else math.pi / 2
            seats.append((theta, row, r * math.cos(theta), r * math.sin(theta)))
    seats.sort(key=lambda s: (-round(s[0], 9), s[1]))
    return [(round(x * _SCALE, 2), round(-y * _SCALE, 2)) for _, _, x, y in seats]


def _pos_bucket(n: int | None) -> str:
    if n is None:
        return "nav"
    if n == 0:
        return "0"
    if n < 5:
        return "1"
    if n < 20:
        return "5"
    return "20"


def _ctr_bucket(n: int | None) -> str:
    if n is None:
        return "nav"
    return "0" if n == 0 else ("1" if n == 1 else "2")


def _lv_date(s: str | None) -> str:
    s = (s or "")[:10]
    return f"{s[8:10]}.{s[5:7]}.{s[:4]}" if len(s) == 10 and s[4] == "-" else s


def _seats_text(n: int) -> str:
    return f"{n} {_lv_plural(n, 'vieta', 'vietas')}"


def _load_composition(
    elected_path: Path, results_path: Path
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Ievēlētie + rezultātu dokuments. Nepilns vai nesaskanīgs sastāvs → KRĪT."""
    elected = read_elected(elected_path)
    if len(elected) != SEATS_TOTAL:
        raise ValueError(
            f"saeima: sastāva failā {elected_path.name} ir {len(elected)} ieraksti, "
            f"jābūt {SEATS_TOTAL}"
        )
    results = read_election_results(results_path)
    if results is None:
        raise ValueError(f"saeima: nav CVK rezultātu faila {results_path}")
    known = {x["list_nr"] for x in results["lists"]}
    missing = sorted({e["list_nr"] for e in elected} - known)
    if missing:
        raise ValueError(f"saeima: saraksta nr. {missing} nav rezultātu failā")
    slugs = [_slugify(e["name"]) for e in elected]
    if len(set(slugs)) != len(slugs):
        raise ValueError("saeima: divi deputāti ar vienādu slug — #dep- enkuri sadurtos")
    return elected, results


def _fetch_people(db: sqlite3.Connection, names: list[str]) -> dict[str, dict[str, Any]]:
    """name → lēcu dati izsekotajiem (tikai precīza pilnā vārda sakritība)."""
    q = ",".join("?" * len(names))
    # Tas pats filtrs kā _fetch_politicians — profila lapa eksistē tikai šiem.
    rows = db.execute(
        f"""SELECT id, name FROM tracked_politicians
            WHERE name IN ({q})
              AND relationship_type NOT IN ('inactive', 'commentator')""",
        names,
    ).fetchall()
    cutoff = trailing_days_cutoff(POSITIONS_WINDOW_DAYS)
    people: dict[str, dict[str, Any]] = {}
    for r in rows:
        pid = r["id"]
        # Pozīcijas 90 dienās: COALESCE(stated_at, created_at) — tā pati datuma
        # izvēle kā profila pozīciju sarakstam (politicians.py). Abas kolonnas
        # glabā LV laiku, tāpēc 'localtime' NEDRĪKST likt.
        pos90 = db.execute(
            """SELECT COUNT(*) FROM claims
               WHERE opponent_id = ? AND claim_type = 'position'
                 AND substr(COALESCE(stated_at, created_at), 1, 10) >= ?""",
            (pid, cutoff),
        ).fetchone()[0]
        # Pretrunas: tas pats predikāts kā profila «Pretrunas» cilnei
        # (COALESCE(confirmed,1)=1), lai kartītes skaitlis sakrīt ar saiti.
        # 2026-10-08 NULL nav nevienā rindā — tātad ekvivalents confirmed=1.
        ctr = db.execute(
            """SELECT COUNT(*) FROM contradictions
               WHERE opponent_id = ? AND COALESCE(confirmed, 1) = 1""",
            (pid,),
        ).fetchone()[0]
        # Balsoja 14. Saeimā = vismaz viens NODOTS balsojums; klātbūtnes
        # reģistrācija nav balsojums (Data Contract 4b). Reālajā DB abi
        # varianti dod 41/100 (mērīts 2026-10-08).
        voted = db.execute(
            """SELECT 1 FROM saeima_individual_votes
               WHERE politician_id = ?
                 AND vote NOT IN ('Reģistrējies', 'Nereģistrējies') LIMIT 1""",
            (pid,),
        ).fetchone() is not None
        latest = db.execute(
            """SELECT stance, topic, source_url, COALESCE(stated_at, created_at) AS d
               FROM claims
               WHERE opponent_id = ? AND claim_type = 'position'
               ORDER BY COALESCE(stated_at, created_at) DESC, id DESC LIMIT 1""",
            (pid,),
        ).fetchone()
        people[r["name"]] = {
            "pid": pid,
            "pos90": pos90,
            "ctr": ctr,
            "voted14": voted,
            "latest": (
                {
                    "stance": latest["stance"],
                    "topic": latest["topic"],
                    "source_url": latest["source_url"],
                    "date": _lv_date(latest["d"]),
                }
                if latest
                else None
            ),
        }
    return people


def _build_context(db: sqlite3.Connection, elected_path: Path, results_path: Path) -> dict[str, Any]:
    elected, results = _load_composition(elected_path, results_path)
    parties = {r["id"]: dict(r) for r in db.execute("SELECT id, name, short_name, color FROM parties")}
    by_nr = {x["list_nr"]: x for x in results["lists"]}

    seat_counts: dict[int, int] = {}
    for e in elected:
        seat_counts[e["list_nr"]] = seat_counts.get(e["list_nr"], 0) + 1
    # Vietu skaits no SASTĀVA (ne rezultātu faila — tie var atšķirties, kamēr
    # viens ir provizorisks); vienādam skaitam — pēc balsīm.
    order = sorted(seat_counts, key=lambda nr: (-seat_counts[nr], -by_nr[nr]["votes"]))

    people = _fetch_people(db, [e["name"] for e in elected])
    photo_dir = ASSETS_DIR / "photos"

    lists: list[dict[str, Any]] = []
    for nr in order:
        x = by_nr[nr]
        party = parties.get(x.get("party_id"))
        lists.append({
            "nr": nr,
            "name": party["name"] if party else x["cvk_name"],
            "short": (party["short_name"] if party else None) or x["cvk_name"],
            "color": (party.get("color") if party else None) or "var(--text-muted)",
            "seats": seat_counts[nr],
            "seats_text": _seats_text(seat_counts[nr]),
            "members": [],
        })
    list_by_nr = {lst["nr"]: lst for lst in lists}

    for e in elected:
        p = people.get(e["name"])
        slug = _slugify(e["name"])
        lst = list_by_nr[e["list_nr"]]
        member = {
            "list": lst,
            "name": e["name"],
            "slug": slug,
            "region": e.get("region") or "",
            "tracked": p is not None,
            "voted14": bool(p and p["voted14"]),
            "pos90": p["pos90"] if p else None,
            "ctr": p["ctr"] if p else None,
            "latest": p["latest"] if p else None,
            "has_photo": p is not None and (photo_dir / f"{slug}.jpg").exists(),
        }
        member["pos_bucket"] = _pos_bucket(member["pos90"])
        member["ctr_bucket"] = _ctr_bucket(member["ctr"])
        member["pos_text"] = (
            "nav datu" if member["pos90"] is None
            else "nav pozīciju" if member["pos90"] == 0
            else f"{_lv_number(member['pos90'])} {_lv_plural(member['pos90'], 'pozīcija', 'pozīcijas')}"
        )
        member["ctr_text"] = (
            "nav datu" if member["ctr"] is None
            else "nav pretrunu" if member["ctr"] == 0
            else f"{member['ctr']} {_lv_plural(member['ctr'], 'pretruna', 'pretrunas')}"
        )
        member["v14_text"] = "balsoja" if member["voted14"] else "nebalsoja"
        lst["members"].append(member)

    coords = _arc_positions(SEATS_TOTAL)
    seats: list[dict[str, Any]] = []
    for lst in lists:
        for m in lst["members"]:
            x, y = coords[len(seats)]
            seats.append({**m, "x": x, "y": y})

    tracked_n = sum(1 for s in seats if s["tracked"])
    voted_n = sum(1 for s in seats if s["voted14"])
    pos_total = sum(s["pos90"] or 0 for s in seats)
    ctr_people = sum(1 for s in seats if s["ctr"])

    def _count(key: str, val: str) -> int:
        return sum(1 for s in seats if s[key] == val)

    updated = str(results.get("cvk_updated_at") or "")
    return {
        "seats": seats,
        "lists": lists,
        "dot_r": round(_DOT_R * _SCALE, 2),
        "hit_r": round(_HIT_R * _SCALE, 2),
        "provisional": bool(results.get("provisional", True)),
        "updated_short": f"{updated[8:10]}.{updated[5:7]}." if len(updated) >= 10 else "",
        "source_url": results.get("source_url") or "",
        "total": len(seats),
        "tracked_n": tracked_n,
        "untracked_n": len(seats) - tracked_n,
        "voted_n": voted_n,
        "pos_total": pos_total,
        "pos_total_text": _lv_number(pos_total),
        "ctr_people": ctr_people,
        "window_days": POSITIONS_WINDOW_DAYS,
        "pos_counts": {b: _count("pos_bucket", b) for b in ("0", "1", "5", "20", "nav")},
        "ctr_counts": {b: _count("ctr_bucket", b) for b in ("0", "1", "2", "nav")},
    }


def render_saeima(
    env: Environment,
    db: sqlite3.Connection,
    atmina_dir: Path,
    elected_path: Path | None = None,
    results_path: Path | None = None,
) -> dict[str, int]:
    """saeima.html. Atgriež skaitītājus; nepilns sastāvs → ValueError."""
    ctx = _build_context(db, elected_path or ELECTED_PATH, results_path or RESULTS_PATH)
    _render_page(env, "saeima.html.j2", atmina_dir / "saeima.html", ctx)
    summary = {"sēdvietas": ctx["total"], "izsekoti": ctx["tracked_n"], "bez_profila": ctx["untracked_n"]}
    print("  saeima: " + " ".join(f"{k}={v}" for k, v in summary.items()))
    return summary
