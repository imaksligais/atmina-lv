"""P3 Phase 0 — Saeimas sēžu UUID no kalendāra momentuzņēmuma.

Lasa Playwright pieejamības momentuzņēmumu no viena sasaukuma kalendāra:
  https://titania.saeima.lv/LIVS{N}/SaeimaLIVS2_DK.nsf/DK?ReadForm&calendar=1
Sasaukumu N nosaka `--convocation` (noklusējums — kārtējais,
`src.saeima.convocation.SAEIMA_CONVOCATION`). Katra sēdes rinda nes atslēgu
`convocation`; esošā manifesta citu sasaukumu rindas pārģenerēšanā paliek
(`_merge_convocation_rows`), jo LIVS15 kalendārs 14. Saeimas sēdes nerāda.

Emits data/saeima_backfill_sessions.json — apvalka objekts ar ģenerēšanas
datumu un sēžu sarakstu:
  { "generated_at": "2026-09-02",
    "sessions": [
      { "year": 2025, "month": 12, "day": 18,
        "session_type": "regular" | "jautajumi" | "arkartas"
                        | "arkartas_sesija" | "sviniga",
        "uuid": "...", "url": "https://...", "convocation": 14,
        "continued_on": ["2026-09-03"] }, ... ] }   # tikai turpinātām sēdēm

**Turpinājuma sēdes, 2026-09-25.** Etiķete `"A / B(sfx)"` ir sēdes turpinājums
dienā B ar SĀKOTNĒJĀS sēdes UUID. Datums B tiek pierakstīts īpašnieka rindas
`continued_on` (ISO, sakārtoti, unikāli); vecos manifestos atslēgas nav, tāpēc
lasītāji lieto `s.get("continued_on", [])`. Turpinājums, kura bāzes UUID šajā
momentuzņēmumā nav, iet `unparsed` sarakstā — ģenerators iziet ar 1. Ķēde
`A / … / Z` (vairākas turpinājuma dienas) piesaista pēdējo dienu Z; pirmajam
skaitlim A jāsakrīt ar īpašnieka dienu, citādi arī `unparsed`.

**Dzīvā (kārtējās dienas) sēde, 2026-09-16.** Kalendārs tai renderē
`./DK?ReadForm&active=1` (arī `actual=1`), nevis `nr={UUID}`. Tāda rinda tagad
manifestā IR, ar `"uuid": null, "live": true` un dzīvo URL. Līdz tam diena
manifestā neiekļuva vispār, un paritātes audits 2026-09-10 sēdei ar 16
balsojumiem izdrukāja „DK=0, trūkst 0" (backlog/saeima.md). Rinda dienu padara
REDZAMU; auditēt to nedrīkst — dzīvā lapa apakšpunktu balsojumus nerenderē, un
`active=1` nākamajā dienā rāda jau citu sēdi. Lasītājiem `not s.get("uuid")` ir
šķirtne (vecos manifestos `live` atslēgas nav).

**`generated_at` ir apvalkā, nevis blakusfailā** (2026-09-02). Blakus stāvošs
`.meta.json` var desinhronizēties — svaigs datums blakus vecam manifestam dotu
zaļu gaismu tieši tajā gadījumā, kura dēļ vārti pastāv. Apvalkā tie ir viens
ieraksts. Lasītāji iet caur `src.saeima.manifest.load_manifest()`, kas prot arī
veco (kailā saraksta) formu, bet atgriež tai `generated_at=None`; parity audits
to uzskata par STOP, ne par svaigu manifestu.

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
sys.path.insert(0, str(REPO_ROOT))

from src.saeima.convocation import SAEIMA_CONVOCATION, base_url  # noqa: E402
from src.saeima.manifest import load_manifest  # noqa: E402

SNAPSHOT_DIR = REPO_ROOT / ".playwright-mcp"
OUT_PATH = REPO_ROOT / "data" / "saeima_backfill_sessions.json"

LV_MONTHS = {
    "Janvāris": 1, "Februāris": 2, "Marts": 3, "Aprīlis": 4,
    "Maijs": 5, "Jūnijs": 6, "Jūlijs": 7, "Augusts": 8,
    "Septembris": 9, "Oktobris": 10, "Novembris": 11, "Decembris": 12,
}

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
# DZĪVĀ (kārtējās dienas) sēde — 2026-09-16. Kalendārs tai NEDOD `nr={UUID}`;
# saite ir `./DK?ReadForm&active=1` (sastopama arī `actual=1` forma). Līdz šim
# `_URL_RE` to nesatvēra, tāpēc diena manifestā neiekļuva VISPĀR, un paritātes
# audits 2026-09-10 sēdei ar 16 balsojumiem izdrukāja „DK=0, trūkst 0".
# Rinda tiek ierakstīta ar `uuid=None` + `live=True`: UUID tai vēl nav, un
# izdomāt to nedrīkst. Lasītāju pienākums — sk. `audit_saeima_agenda_parity.py`
# 4. vārtus: dzīvā diena ir REDZAMA, bet NAV auditējama.
_LIVE_URL_RE = re.compile(r"\./DK\?ReadForm&(act(?:ive|ual))=1")
# "15", "22(J)", "23(As)", "15 / 22" (turpinājums)
_LABEL_PARTS_RE = re.compile(r"^\s*([\d\s/]+?)\s*(?:\(([A-Za-z]+)\))?\s*$")


def parse_calendar(
    snapshot_text: str, convocation: int = SAEIMA_CONVOCATION
) -> tuple[list[dict], list[dict]]:
    """Return (sessions, unparsed).

    `unparsed` nes katru etiķeti, kas bija piesaistīta sēdes URL, bet ko
    neizdevās nolasīt. Izsaucējam tas JĀAPSTRĀDĀ — tieši klusa izmešana šeit
    padarīja manifestu nepilnīgu, un neviens to nepamanīja gadu.

    `convocation` ir kalendāra sasaukums: katra sēdes rinda to nes atslēgā
    `convocation`, un tās URL veido no šī sasaukuma bāzes.
    """
    base = base_url(convocation)
    lines = snapshot_text.splitlines()
    sessions: list[dict] = []
    unparsed: list[dict] = []
    seen: set[tuple[int, str]] = set()
    continuations: list[dict] = []
    seen_continuations: set[tuple[int, int, str | None, str]] = set()

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
        live_m = _LIVE_URL_RE.search(line) if um is None else None
        if not ((um or live_m) and year is not None and month is not None):
            continue

        uuid = um.group(1) if um else None
        live_param = live_m.group(1) if live_m else None
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

        parts = _LABEL_PARTS_RE.match(label)

        # "A / B" = turpinājuma sēde (2026-09-25): A ir sākotnējās sēdes diena,
        # B — ŠĪS šūnas diena parsējamajā mēnesī; UUID ir sākotnējās sēdes UUID.
        # Līdz šim šūna tika izlaista ar pieņēmumu, ka UUID „parādās savā datuma
        # rindā". Tas parādās — bet ar SĀKOTNĒJO datumu, tāpēc 2026-09-03 sēde
        # (`23 / 3(As)`, 07-23 turpinājums) datuma auditam bija neredzama, kamēr
        # DB trūka 4 balsojumu. Tagad datumu pievienojam īpašnieka rindas
        # `continued_on` pēc cikla. Pārbaude stāv PIRMS `seen` dedup, jo UUID
        # ir tas pats, kas bāzes rindai, un dedup to citādi norītu klusi.
        #
        # Ķēde `A / B / … / Z` (piem. `29 / 5 / 12`): PIRMAIS skaitlis ir
        # sākotnējās sēdes diena, PĒDĒJAIS — šīs šūnas diena; vidējie ir agrākas
        # turpinājuma dienas, kurām ir pašām sava šūna. Atkārtots mezgls ar to
        # pašu (gads, mēnesis, uuid, etiķete) tiek ņemts vienreiz — tas iet garām
        # `seen`. Gads + mēnesis ir atslēgā, jo `23 / 3` augustā un septembrī
        # ir divas dažādas dienas.
        if parts and "/" in parts.group(1):
            cont_key = (year, month, uuid, label)
            if cont_key in seen_continuations:
                continue
            seen_continuations.add(cont_key)
            try:
                days = [int(x) for x in parts.group(1).split("/")]
                cont_iso = date(year, month, days[-1]).isoformat()
            except ValueError:
                unparsed.append({"year": year, "month": month, "uuid": uuid,
                                 "label": label,
                                 "why": "turpinājuma etiķete nav „A / … / Z“ ar skaitļiem"})
                continue
            continuations.append({"year": year, "month": month, "uuid": uuid,
                                  "label": label, "base_day": days[0],
                                  "date": cont_iso})
            continue

        # Dzīvajai sēdei UUID nav, tāpēc dedup atslēga ir tās etiķete (= diena);
        # ar kailu `uuid=None` divas dzīvās dienas vienā gadā sakristu un otrā
        # pazustu klusi.
        seen_key = (year, uuid if uuid else f"live:{month}:{label}")
        if seen_key in seen:
            continue
        seen.add(seen_key)

        if not parts:
            unparsed.append({"year": year, "month": month, "uuid": uuid,
                             "label": label, "why": "etiķete neatbilst formai"})
            continue

        day_text, suffix = parts.group(1).strip(), (parts.group(2) or "")

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

        entry = {
            "year": year,
            "month": month,
            "day": day,
            "session_type": session_type,
            "uuid": uuid,
            "url": (f"{base}/DK?ReadForm&nr={uuid}" if uuid
                    else f"{base}/DK?ReadForm&{live_param}=1"),
            "convocation": convocation,
        }
        if uuid is None:
            # Karogs ir ĒRTĪBA, ne līgums: vecos manifestos tā nav, tāpēc
            # lasītājiem jātestē `not s.get("uuid")`, ne `s.get("live")`.
            entry["live"] = True
        sessions.append(entry)

    # Turpinājumus piesaista PĒC cikla: bāzes rinda var stāvēt citā mēnesī vai
    # gadā. Bez īpašnieka šajā momentuzņēmumā → `unparsed` (ģenerators iziet
    # ar 1), nevis izdomāta patstāvīga rinda: tās tips un datums nav zināmi.
    by_uuid = {s["uuid"]: s for s in sessions if s["uuid"]}
    for c in continuations:
        owner = by_uuid.get(c["uuid"]) if c["uuid"] else None
        if owner is None:
            unparsed.append({"year": c["year"], "month": c["month"], "uuid": c["uuid"],
                             "label": c["label"],
                             "why": "turpinājums bez bāzes sēdes šajā momentuzņēmumā"})
            continue
        # Etiķetes nolasījuma pārbaude: pirmajam skaitlim jābūt īpašnieka dienai,
        # un īpašniekam jābūt AGRĀKAM par turpinājumu. Neatbilstība nozīmē, ka
        # etiķetes semantika nolasīta nepareizi — apstājamies, nepiesaistām.
        owner_iso = date(owner["year"], owner["month"], owner["day"]).isoformat()
        if owner["day"] != c["base_day"] or owner_iso >= c["date"]:
            unparsed.append({"year": c["year"], "month": c["month"], "uuid": c["uuid"],
                             "label": c["label"],
                             "why": (f"turpinājuma etiķete neatbilst bāzes sēdei "
                                     f"{owner_iso} (pirmais skaitlis {c['base_day']}, "
                                     f"turpinājums {c['date']}) — semantika nolasīta nepareizi")})
            continue
        owner["continued_on"] = sorted(set(owner.get("continued_on", [])) | {c["date"]})

    return sessions, unparsed


def _merge_convocation_rows(old: list[dict], new: list[dict], convocation: int) -> list[dict]:
    """Aizvieto `convocation` rindas ar `new`, pārējo sasaukumu rindas patur.

    LIVS15 kalendārs 14. Saeimas sēdes nerāda; bez šī pēc pārģenerēšanas
    14. sasaukuma audits klusi redzētu 0 sēžu. Rinda bez atslēgas = 14."""
    kept = [s for s in old if s.get("convocation", 14) != convocation]
    return kept + new


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
    ap.add_argument("--convocation", type=int, default=SAEIMA_CONVOCATION,
                    help="kalendāra sasaukums (LIVS{N}); citu sasaukumu rindas esošajā manifestā paliek")
    args = ap.parse_args(argv)

    snapshot = args.snapshot or _newest_snapshot()
    if snapshot is None or not snapshot.exists():
        print(
            "KĻŪDA: momentuzņēmums nav atrasts.\n"
            f"  Meklēts: {args.snapshot or (SNAPSHOT_DIR / 'page-*.yml')}\n"
            "  .playwright-mcp/ ir gitignorēta skrāpes mape — vispirms uztver "
            "kalendāra lapu ar Playwright:\n"
            f"  {base_url(args.convocation)}/DK?ReadForm&calendar=1",
            file=sys.stderr,
        )
        return 1

    sessions, unparsed = parse_calendar(snapshot.read_text(encoding="utf-8"),
                                        convocation=args.convocation)

    window = [
        s for s in sessions
        if (s["year"], s["month"]) >= (2022, 9) and s["year"] <= args.max_year
    ]
    parsed = len(window)
    if not parsed:
        # T8: 0 sēžu + esošā manifesta apvienošana izskatītos pēc zaļa
        # skrējiena (citu sasaukumu rindas paliek, generated_at atjaunojas).
        print(
            f"STOP: momentuzņēmumā {snapshot} nav nevienas {args.convocation}. "
            f"sasaukuma sēdes logā 2022-09 → {args.max_year}-12. Manifests NAV "
            "ierakstīts. Iespējams, nepareizs sasaukums vai mainīts kalendāra "
            "formāts (T8/T12), nevis tukšs kalendārs.",
            file=sys.stderr,
        )
        _report_unparsed(unparsed, written=False)
        return 1
    if args.out.exists():
        old, _ = load_manifest(args.out)
        window = _merge_convocation_rows(old, window, args.convocation)
    window.sort(key=lambda s: (s["year"], s["month"], s["day"], s["session_type"]))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps({"generated_at": date.today().isoformat(), "sessions": window},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    by_year: dict[int, int] = {}
    by_type: dict[str, int] = {}
    for s in window:
        by_year[s["year"]] = by_year.get(s["year"], 0) + 1
        by_type[s["session_type"]] = by_type.get(s["session_type"], 0) + 1

    print(f"Momentuzņēmums: {snapshot}")
    print(f"{args.convocation}. sasaukuma sēdes logā 2022-09 → {args.max_year}-12: {parsed}")
    print(f"Manifestā kopā (ar citu sasaukumu rindām): {len(window)}")
    print("Pa gadiem:")
    for y, n in sorted(by_year.items()):
        print(f"  {y}: {n}")
    print("Pa tipiem:")
    for t, n in sorted(by_type.items()):
        print(f"  {t}: {n}")
    # Turpinājumu saucējs: 0 piesaistīti blakus N neparsētiem nozīmē, ka
    # turpinājuma dienas paritātes auditam nav redzamas (2026-09-03 klase).
    cont_attached = sum(len(s.get("continued_on", [])) for s in window)
    cont_unparsed = sum(1 for u in unparsed if "/" in (u.get("label") or ""))
    print(f"Turpinājumi: piesaistīti {cont_attached}, neparsēti {cont_unparsed}")
    print(f"\nIerakstīts {args.out} (generated_at={date.today().isoformat()})")

    if unparsed:
        _report_unparsed(unparsed, written=True)
        return 1

    return 0


def _report_unparsed(unparsed: list[dict], *, written: bool) -> None:
    if not unparsed:
        return
    print(f"\nNENOLASĪTAS ETIĶETES: {len(unparsed)}", file=sys.stderr)
    for u in unparsed:
        print(f"  {u['year']}-{u['month']:02d} {u['label']!r}: {u['why']} ({u['uuid']})",
              file=sys.stderr)
    if written:
        print(
            "\nManifests IR ierakstīts, bet tas ir NEPILNĪGS — katra šāda rinda ir "
            "sēde, ko parity audits nekad neredzēs. Papildini SESSION_TYPE_BY_SUFFIX "
            "vai etiķetes formu un palaid vēlreiz.",
            file=sys.stderr,
        )


if __name__ == "__main__":
    sys.exit(main())
