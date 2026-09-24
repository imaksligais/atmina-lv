#!/usr/bin/env python
"""Novērtē claim-extractor zelta kopas skrējienu mehāniski.

Līdz 2026-09-22 vērtēšana notika ar roku orķestratora kontekstā (sk.
`docs/eval/claim-extractor-models-v2-2026-09-16.md` § Metodikas piezīmes).
Ar roku var pārbaudīt lēmumu, bet ne citāta burtiskumu — tieši tur dzīvo
visizturīgākais defekts (fragmentārs citāts, #20850 klase), tāpēc šis skripts
dara to daļu, ko mašīna dara labāk:

  1. citāts ir NEPĀRTRAUKTA apakšvirkne gadījuma avota tekstā;
  2. ja atšķiras tikai noslēguma pieturzīme — atsevišķa, vieglāka klase;
  3. `quote=null` → `confidence` ≤ 0.65 (prompta cietais vārts, 2026-09-22; 0.6 → 0.65 skaidram atstāstam 2026-09-23);
  4. nogriezts/paywall avots → `reasoning` sākas ar `NEEDS_REVIEW:`.

Lēmumu pareizība (extract/empty) paliek cilvēkam: tā ir rubrikas, ne formas
pārbaude, un rubrika balstās operatora lēmumos.

Lietojums:
    python scripts/eval_claim_extractor_score.py docs/eval/_run-<m>-<datums>.txt
    python scripts/eval_claim_extractor_score.py <fails> --json out.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
GOLDEN = REPO / "docs/eval/_golden-2026-09-16-NO-RUBRIC.md"

# Gaidāmie lēmumi = faktiskie operatora lēmumi (rubrika
# claim-extractor-golden-cases-2026-09-16.md). 7. gadījums ir robežlēmums.
EXPECTED = {
    1: "empty", 2: "extract", 3: "extract", 4: "extract",
    5: "empty", 6: "empty", 7: "extract", 8: "extract",
    9: "empty", 10: "empty", 11: "extract", 12: "extract",
}

TERMINAL = ".!?…\"»'"


def norm(s: str) -> str:
    """Atstarpes un tipogrāfiskās pēdiņas nost — pieturzīmes PALIEK."""
    s = unicodedata.normalize("NFC", s)
    s = s.replace("\u00a0", " ").replace("\u200b", "")
    s = s.replace("„", '"').replace("“", '"').replace("”", '"')
    s = s.replace("«", '"').replace("»", '"').replace("’", "'")
    return re.sub(r"\s+", " ", s).strip()


def load_run(path: Path) -> list[dict]:
    """Izvelk JSON masīvu no raw izvades (var būt apvalks vai astes rindas)."""
    raw = path.read_text(encoding="utf-8", errors="replace")
    best: list[dict] = []
    start = raw.find("[")
    while start != -1:
        depth, in_str, esc = 0, False, False
        for i in range(start, len(raw)):
            c = raw[i]
            if in_str:
                if esc:
                    esc = False
                elif c == "\\":
                    esc = True
                elif c == '"':
                    in_str = False
                continue
            if c == '"':
                in_str = True
            elif c == "[":
                depth += 1
            elif c == "]":
                depth -= 1
                if depth == 0:
                    try:
                        data = json.loads(raw[start : i + 1])
                    except json.JSONDecodeError:
                        break
                    # Raw var saturēt vairākus masīvus (narratīvs + atbilde) —
                    # ņem to, kurā ir visvairāk «case» objektu, ne pirmo.
                    if isinstance(data, list) and data and isinstance(data[0], dict):
                        cased = [o for o in data if isinstance(o, dict) and "case" in o]
                        if len(cased) > len(best):
                            best = cased
                    break
        start = raw.find("[", start + 1)
    if best:
        return best
    raise SystemExit(f"JSON masīvs nav atrasts: {path}")


def load_cases() -> dict[int, str]:
    """Gadījuma numurs -> tā avota teksts (viss bloks līdz nākamajam gadījumam)."""
    text = GOLDEN.read_text(encoding="utf-8", errors="replace")
    parts = re.split(r"\n#+\s*(?:GADĪJUMS|Gadījums|CASE)\s*(\d+)", text)
    cases: dict[int, str] = {}
    for i in range(1, len(parts) - 1, 2):
        cases[int(parts[i])] = norm(parts[i + 1])
    return cases


def check(run: list[dict], cases: dict[int, str]) -> dict:
    rows, issues = [], []
    for obj in run:
        n = obj.get("case")
        decision = obj.get("decision")
        src = cases.get(n, "")
        exp = EXPECTED.get(n)
        truncated = bool(
            re.search(r"turpinātu lasīt|pilno rakstu|abonē|paywall", src, re.I)
        )
        row = {"case": n, "decision": decision, "expected": exp,
               "decision_ok": decision == exp, "truncated_source": truncated,
               "quotes": []}
        for c in obj.get("claims") or []:
            q, conf = c.get("quote"), c.get("confidence")
            reasoning = (c.get("reasoning") or "").strip()
            qs = {"confidence": conf, "quote": (q[:60] + "…") if q and len(q) > 60 else q}
            if q:
                nq = norm(q)
                if nq and nq in src:
                    qs["verbatim"] = "ok"
                elif nq and nq.rstrip(TERMINAL) in src:
                    qs["verbatim"] = "pieturzīme"          # ◐ klase
                    issues.append(f"{n}: citāta noslēguma pieturzīme neatbilst avotam")
                else:
                    qs["verbatim"] = "NAV APAKŠVIRKNE"     # ✗ klase
                    issues.append(f"{n}: citāts nav nepārtraukta apakšvirkne avotā")
                if nq and nq[0].islower():
                    qs["fragment_start"] = True
                    issues.append(f"{n}: citāts sākas ar mazo burtu — teikuma vidus (#20850)")
            else:
                qs["verbatim"] = "null"
                if isinstance(conf, (int, float)) and conf > 0.65:
                    qs["conf_gate"] = "PĀRSNIEGTS"
                    issues.append(f"{n}: quote=null, bet confidence {conf} > 0.65")
            # Vai avots ir nogriezts, izlemj AVOTA teksts, ne modeļa reasoning.
            # (2026-09-22: pirmā versija lasīja reasoning un noķēra atslēgvārdu
            # noliegumā — «avots NAV nogriezts paywall/stub» skaitījās defekts.
            # Tā ir CLAUDE.md T16 klase mana paša rīka iekšienē.)
            if truncated and not reasoning.upper().startswith("NEEDS_REVIEW"):
                qs["marker_gate"] = "TRŪKST"
                issues.append(f"{n}: nogriezts/paywall avots bez NEEDS_REVIEW marķiera")
            row["quotes"].append(qs)
        rows.append(row)
    return {"rows": rows, "issues": issues}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("run_file", type=Path)
    ap.add_argument("--json", type=Path)
    a = ap.parse_args()

    run = load_run(a.run_file)
    cases = load_cases()
    res = check(run, cases)
    if not cases:
        print("BRĪDINĀJUMS: gadījumu teksti nav atpazīti — citātu pārbaude nav ticama")

    ok = sum(1 for r in res["rows"] if r["decision_ok"])
    print(f"Gadījumi: {len(res['rows'])}  |  lēmums sakrīt ar rubriku: {ok}")
    for r in res["rows"]:
        mark = "OK " if r["decision_ok"] else "ATŠĶ"
        extra = "".join(
            f" [q:{q['verbatim']}"
            + (f" conf={q['confidence']}" if q.get("conf_gate") else "")
            + (" FRAGMENTS" if q.get("fragment_start") else "")
            + (" BEZ-MARĶIERA" if q.get("marker_gate") else "")
            + "]"
            for q in r["quotes"]
        )
        print(f"  {r['case']!s:>2}  {mark}  {str(r['decision']):<12} (gaida {r['expected']}){extra}")

    print(f"\nFormas defekti: {len(res['issues'])}")
    for i in res["issues"]:
        print("  -", i)
    if a.json:
        a.json.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n→ {a.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
