"""P3 Phase 0 — Extract 14. Saeima session UUIDs from a calendar snapshot.

Reads a Playwright accessibility snapshot of:
  https://titania.saeima.lv/LIVS14/SaeimaLIVS2_DK.nsf/DK?ReadForm&calendar=1

Emits data/saeima_backfill_sessions.json with one entry per unique session:
  { "year": 2025, "month": 12, "day": 18,
    "session_type": "regular" | "jautajumi" | "arkartas" | "arkartas_sesija"
                    | "sviniga",
    "uuid": "...", "url": "https://..." }

**Vispirms jāuztver momentuzņēmums.** `.playwright-mcp/` ir gitignorēta skrāpes
mape, tāpēc snapshot fails šeit nav garantēts. Uztver kalendāra lapu ar
Playwright (`browser_navigate` uz augšējo URL saglabā `.playwright-mcp/page-*.yml`)
un tad palaid šo skriptu. Bez `--snapshot` tiek ņemts jaunākais tās mapes fails.

Kāpēc tas ir tā vērts: līdz 2026-08-01 šis skripts bija nepalaižams — tas
norādīja uz 2026-05-26 momentuzņēmumu, kura vairs nav — tātad manifests bija
neatveidojams artefakts, uz kuru paļaujas parity audits.

## Divi klusie robi, kas slēgti 2026-08-01

**1. Gada logs bija iesaldēts uz `<= 2025`** ar komentāru „skip 2026 — already
in DB". DB to atspēkoja: 2026. gadā bija 13 sēžu dienas pret 43 kalendārā.
Robeža tagad ir `--max-year` (noklusējums: kārtējais gads).

**2. Divus sēžu tipus parseris klusi izmeta.** Kalendārs lieto PIECAS etiķešu
formas, ne trīs: bez sufiksa, `(J)`, `(A)`, `(As)` = ārkārtas SESIJAS sēde,
`(S)` = svinīgā sēde. `(As)` un `(S)` neizturēja `int()` un tika izlaisti bez
pēdām — 16 sēdes 2022.–2026. gadā, to skaitā **2026-07-23 ar 65 balsojumiem DB**.
Tāpēc nesalasāma etiķete tagad tiek UZSKAITĪTA un ziņota, un skripts iziet ar 1:
klusa izlaišana ir tieši tā klase, kuras dēļ manifests bija nepilnīgs.

Momentuzņēmuma formāts arī mainījās (T12 — formāta maiņa, ne izzušana): dienas
etiķete pārcēlās no `cell` mezgla uz `link` mezglu. Parseris tagad pieņem abus.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_DIR = REPO_ROOT / ".playwright-mcp"
OUT_PATH = REPO_ROOT / "data" / "saeima_backfill_sessions.json"

LV_MONTHS = {
    "Janvāris": 1, "Februāris": 2, "Marts": 3, "Aprīlis": 4,
    "Maijs": 5, "Jūnijs": 6, "Jūlijs": 7, "Augusts": 8,
    "Septembris": 9, "Oktobris": 10, "Novembris": 11, "Decembris": 12,
}

SAEIMA_BASE = "https://titania.saeima.lv/LIVS14/SaeimaLIVS2_DK.nsf"

# Kalendāra etiķetes sufikss → session_type. Tukšs sufikss = kārtējā sēde.
# `(As)` un `(S)` nolasīti no pašas lapas virsraksta rindas, piem.
# „Saeimas 23.07.2026. pirmās ārkārtas sesijas sēde" un
# „Saeimas 21.08.2026. svinīgā sēde".
SESSION_TYPE_BY_SUFFIX = {
    "": "regular",
    "J": "jautajumi",         # jautājumu sēde
    "A": "arkartas",          # ārkārtas sēde
    "As": "arkartas_sesija",  # ārkārtas sesijas sēde
    "S": "sviniga",           # svinīgā sēde (bez roll-call balsojumiem)
}

_YEAR_RE = re.compile(r"(\d{4})\.\s*gads")
_MONTH_RE = re.compile(r'cell\s+"(' + "|".join(LV_MONTHS) + r')"')
# Etiķete var stāvēt uz `cell` (vecais formāts) vai uz `link` (2026-08 formāts).
_LABEL_RE = re.compile(r'-\s*(?:cell|link)\s+"([^"]+)"')
_URL_RE = re.compile(r"\./DK\?ReadForm&nr=([a-f0-9-]{36})")
# "15", "22(J)", "23(As)", "15 / 22" (turpinājums)
_LABEL_PARTS_RE = re.compile(r"^\s*([\d\s/]+?)\s*(?:\(([A-Za-z]+)\))?\s*$")


def parse_calendar(snapshot_text: str) -> tuple[list[dict], list[dict]]:
    """Return (sessions, unparsed).

    `unparsed` nes katru etiķeti, kas bija piesaistīta sēdes URL, bet ko
    neizdevās nolasīt. Izsaucējam tas JĀAPSTRĀDĀ — tieši klusa izmešana šeit
    padarīja manifestu nepilnīgu, un neviens to nepamanīja gadu.
    """
    lines = snapshot_text.splitlines()
    sessions: list[dict] = []
    unparsed: list[dict] = []
    seen: set[tuple[int, str]] = set()

    year: int | None = None
    month: int | None = None

    for i, line in enumerate(lines):
        ym = _YEAR_RE.search(line)
        if ym:
            year = int(ym.group(1))
            month = None
            continue

        mm = _MONTH_RE.search(line)
        if mm:
            month = LV_MONTHS[mm.group(1)]

        um = _URL_RE.search(line)
        if not (um and year is not None and month is not None):
            continue

        uuid = um.group(1)
        # Etiķete stāv uz šīs pašas rindas vai dažas rindas augstāk (cell → link
        # → /url). Skatāmies atpakaļ, tāpēc abi momentuzņēmuma formāti der.
        label: str | None = None
        for j in range(i, max(i - 4, -1), -1):
            lm = _LABEL_RE.search(lines[j])
            if lm and lm.group(1) not in LV_MONTHS:
                label = lm.group(1).strip()
                break
        if label is None:
            unparsed.append({"year": year, "month": month, "uuid": uuid,
                             "label": None, "why": "etiķete nav atrasta"})
            continue

        if (year, uuid) in seen:
            continue
        seen.add((year, uuid))

        parts = _LABEL_PARTS_RE.match(label)
        if not parts:
            unparsed.append({"year": year, "month": month, "uuid": uuid,
                             "label": label, "why": "etiķete neatbilst formai"})
            continue

        day_text, suffix = parts.group(1).strip(), (parts.group(2) or "")

        # "A / B" = turpinājuma sēde; tā norāda uz agrāku UUID, kas parādās savā
        # datuma rindā, tāpēc to izlaižam ar nolūku (nav robs).
        if "/" in day_text:
            continue

        session_type = SESSION_TYPE_BY_SUFFIX.get(suffix)
        if session_type is None:
            unparsed.append({"year": year, "month": month, "uuid": uuid,
                             "label": label, "why": f"nezināms sufikss ({suffix})"})
            continue

        try:
            day = int(day_text)
        except ValueError:
            unparsed.append({"year": year, "month": month, "uuid": uuid,
                             "label": label, "why": "diena nav skaitlis"})
            continue

        sessions.append({
            "year": year,
            "month": month,
            "day": day,
            "session_type": session_type,
            "uuid": uuid,
            "url": f"{SAEIMA_BASE}/DK?ReadForm&nr={uuid}",
        })

    return sessions, unparsed


def _newest_snapshot() -> Path | None:
    if not SNAPSHOT_DIR.exists():
        return None
    files = sorted(SNAPSHOT_DIR.glob("page-*.yml"))
    return files[-1] if files else None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--snapshot", type=Path, default=None,
                    help="Playwright a11y momentuzņēmums; noklusējums — jaunākais .playwright-mcp/page-*.yml")
    ap.add_argument("--max-year", type=int, default=date.today().year,
                    help="pēdējais iekļaujamais gads (noklusējums: kārtējais)")
    ap.add_argument("--out", type=Path, default=OUT_PATH)
    args = ap.parse_args(argv)

    snapshot = args.snapshot or _newest_snapshot()
    if snapshot is None or not snapshot.exists():
        print(
            "KĻŪDA: momentuzņēmums nav atrasts.\n"
            f"  Meklēts: {args.snapshot or (SNAPSHOT_DIR / 'page-*.yml')}\n"
            "  .playwright-mcp/ ir gitignorēta skrāpes mape — vispirms uztver "
            "kalendāra lapu ar Playwright:\n"
            f"  {SAEIMA_BASE}/DK?ReadForm&calendar=1",
            file=sys.stderr,
        )
        return 1

    sessions, unparsed = parse_calendar(snapshot.read_text(encoding="utf-8"))

    window = [
        s for s in sessions
        if (s["year"], s["month"]) >= (2022, 9) and s["year"] <= args.max_year
    ]
    window.sort(key=lambda s: (s["year"], s["month"], s["day"], s["session_type"]))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(window, ensure_ascii=False, indent=2), encoding="utf-8")

    by_year: dict[int, int] = {}
    by_type: dict[str, int] = {}
    for s in window:
        by_year[s["year"]] = by_year.get(s["year"], 0) + 1
        by_type[s["session_type"]] = by_type.get(s["session_type"], 0) + 1

    print(f"Momentuzņēmums: {snapshot}")
    print(f"Sēdes logā 2022-09 → {args.max_year}-12: {len(window)}")
    print("Pa gadiem:")
    for y, n in sorted(by_year.items()):
        print(f"  {y}: {n}")
    print("Pa tipiem:")
    for t, n in sorted(by_type.items()):
        print(f"  {t}: {n}")
    print(f"\nIerakstīts {args.out}")

    if unparsed:
        print(f"\nNENOLASĪTAS ETIĶETES: {len(unparsed)}", file=sys.stderr)
        for u in unparsed:
            print(f"  {u['year']}-{u['month']:02d} {u['label']!r}: {u['why']} ({u['uuid']})",
                  file=sys.stderr)
        print(
            "\nManifests IR ierakstīts, bet tas ir NEPILNĪGS — katra šāda rinda ir "
            "sēde, ko parity audits nekad neredzēs. Papildini SESSION_TYPE_BY_SUFFIX "
            "vai etiķetes formu un palaid vēlreiz.",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
