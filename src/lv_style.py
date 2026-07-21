"""LV-stilistikas linteris brief-writer aģentam.

Mērķis: noķert tipiskās rakstības kļūdas, ko 2026-05-06 dienas brief
(context_notes #195) prasīja labot post-publish — % atstarpi, anglicismus
`aksi/startā/ataka/polemika`, blakus teikumu uzvārda atkārtojumus.

Skenējam tikai aģenta paša rakstīto naratīvu — `claims` tabulu šūnas un
`<div class="context-box">` bloki ir source-faithful no extractor-a un
context_notes DB un netiek skenēti.
"""

from __future__ import annotations

import re

def _load_tracked_surnames() -> set[str]:
    """Lasa tracked_politicians uzvārdus no DB. Return: set ar pamatformām
    (nominatīvs). Ņem tikai pēdējo vārdu personvārdā (uzvārds), kas sākas ar
    lielo burtu — tas izfiltrē institucionālos slot-us (`Saeimas ziņas`,
    `IR žurnāls`), kuru otrais vārds ir mazo burtu lietvārds. Ģenitīva u.c.
    locījumi atstāti — adjacent-repetition pārbaude uztver tikai precīzas
    atkārtojumus.
    """
    try:
        from src.db import get_db
        db = get_db()
        names = set()
        rows = db.execute("SELECT name FROM tracked_politicians WHERE relationship_type != 'inactive'").fetchall()
        for r in rows:
            tokens = (r["name"] or "").split()
            if not tokens:
                continue
            last = tokens[-1].strip(",.;:()")
            if len(last) >= 5 and last[0].isupper():
                names.add(last)
        db.close()
        return names
    except Exception:
        return set()


ANGLICISMS = {
    "aksi": "asi",
    "aksis": "ass",
    "startā": "sākumā",
    "ataka": "uzbrukums",
    "atakas": "uzbrukumi/uzbrukšana",
    "atakām": "uzbrukumiem",
    "polemika": "diskusija",
    "polemiku": "diskusiju",
    "polemikā": "diskusijā",
    # "melīšana" nav LV — pareizais ir "melošana" (no melot+šana).
    "melīšana": "melošana",
    "melīšanu": "melošanu",
    "melīšanas": "melošanas",
    "melīšanā": "melošanā",
    # "konsenss" = anglicisms → "vienprātība"/"vienota nostāja"/"saskaņa".
    "konsenss": "vienprātība",
    "konsensu": "vienprātību",
    "konsensa": "vienprātības",
    "konsensā": "vienprātībā",
}


def _strip_protected_regions(content: str) -> str:
    """Aizvieto tabulu rindas un context-box blokus ar tukšumu, lai linteris
    tos neapstrādā. Source-faithful saturs paliek nepieskartss."""
    lines = content.split("\n")
    out: list[str] = []
    in_context_box = False
    for line in lines:
        stripped = line.strip()
        # Context-box blok: <div class="context-box"> ... </div>
        if "<div class=\"context-box\"" in line:
            in_context_box = True
            out.append("")
            continue
        if in_context_box:
            if "</div>" in line:
                in_context_box = False
            out.append("")
            continue
        # Markdown tabulas rindas
        if stripped.startswith("|") and stripped.endswith("|"):
            out.append("")
            continue
        # HTML komentāri (DIENAS STATS, NARATĪVA MATERIĀLS u.c.)
        if stripped.startswith("<!--") and stripped.endswith("-->"):
            out.append("")
            continue
        out.append(line)
    return "\n".join(out)


def lint_lv_style(content: str) -> list[dict]:
    """Atgriež problēmu sarakstu.

    Katra problēma: {"rule": str, "match": str, "context": str, "suggestion": str}.
    Empty list = brief tīrs.
    """
    scan = _strip_protected_regions(content)
    issues: list[dict] = []

    # 1. Atstarpe pirms % — meklē `<digit>%` bez priekšstāvošas atstarpes
    for m in re.finditer(r"\b(\d+(?:[.,]\d+)?)(%)", scan):
        # Konteksts ±25 simbolu
        ctx_start = max(0, m.start() - 25)
        ctx_end = min(len(scan), m.end() + 25)
        issues.append({
            "rule": "no-space-before-percent",
            "match": m.group(0),
            "context": scan[ctx_start:ctx_end].replace("\n", " "),
            "suggestion": f"{m.group(1)} %",
        })

    # 2. Anglicisms (case-insensitive, vārda robežās)
    for word, replacement in ANGLICISMS.items():
        for m in re.finditer(rf"\b{re.escape(word)}\b", scan, re.IGNORECASE):
            ctx_start = max(0, m.start() - 25)
            ctx_end = min(len(scan), m.end() + 25)
            issues.append({
                "rule": "anglicism",
                "match": m.group(0),
                "context": scan[ctx_start:ctx_end].replace("\n", " "),
                "suggestion": replacement,
            })

    # 3. Sakārtota-saraksta slazds — rindkopa, kas sākas ar "N. " (cipars +
    # punkts + atstarpe). Markdown to padara par <ol><li> un apēd ciparu, tāpēc
    # "4. jūnijā" pārlūkā parādās kā "1. jūnijā" (izskatās pēc datuma kļūdas).
    # Skenē tikai ne-bullet rindas; tabulas/context-box jau nostriptotas augšā.
    for line in scan.split("\n"):
        stripped = line.lstrip()
        if stripped.startswith("-"):
            continue
        m = re.match(r"\d+\.\s", stripped)
        if m:
            issues.append({
                "rule": "ol-trap",
                "match": m.group(0).strip(),
                "context": line.strip()[:50].replace("\n", " "),
                "suggestion": "Nesāc rindkopu ar 'N. ' — markdown to padara par sarakstu un apēd ciparu.",
            })

    # 4. Adjacent surname repetition — atrod tracked politiķu uzvārdus DB un
    # skenē, vai viens uzvārds parādās divreiz vienā teikumā/bullet-ā tuvāk
    # par 60 simboliem (paragrāfos) vai 30 simboliem (bullet rindās). Iestādes/
    # valstis (Saeima, Latvija) nav uzvārdi, jo `_load_tracked_surnames`
    # ņem tikai pēdējo personvārda tokenu.
    surnames = _load_tracked_surnames()
    if surnames:
        # Sadalīt pa rindām un grupēt — bullet rinda = atsevišķs konteksts
        for line in scan.split("\n"):
            if not line.strip():
                continue
            is_bullet = line.lstrip().startswith("-")
            gap_threshold = 30 if is_bullet else 60
            for name in surnames:
                positions = [m.start() for m in re.finditer(rf"\b{re.escape(name)}\b", line)]
                if len(positions) < 2:
                    continue
                for i in range(len(positions) - 1):
                    gap = positions[i + 1] - positions[i]
                    if gap < gap_threshold:
                        ctx = line[max(0, positions[i] - 20):positions[i + 1] + len(name) + 20]
                        issues.append({
                            "rule": "adjacent-surname-repetition",
                            "match": name,
                            "context": ctx.replace("\n", " "),
                            "suggestion": f"Pārformulē, lai {name} neparādās divreiz tuvās klauzulās.",
                        })
                        break

    return issues


def format_issues(issues: list[dict]) -> str:
    """Cilvēkam-lasāms output linter rezultātu izmestšanai konsolē."""
    if not issues:
        return "OK — LV-stilistika tīra."
    lines = [f"{len(issues)} stilistikas problēmas:"]
    for i, p in enumerate(issues, 1):
        lines.append(
            f"  {i}. [{p['rule']}] '{p['match']}' → {p['suggestion']}"
        )
        lines.append(f"     konteksts: …{p['context']}…")
    return "\n".join(lines)
