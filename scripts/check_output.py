#!/usr/bin/env python
"""Validē UZBŪVĒTO `output/atmina/` koku: vai katra atsauce izšķiras pret failu.

Kāpēc šis eksistē (2026-08-01 audits). `scripts/check.sh` uzrenderēja vietni un
pēc tam **neizlasīja no tās nevienu baitu**; `scripts/deploy.sh` vienīgais
priekšnosacījums bija „vai mape eksistē". Tāpēc neviens solis nekad nepārbaudīja,
vai lapas atsaucas uz failiem, kas tiešām aiziet līdzi. Tā kā `deploy.sh
--no-delete` ir standarta režīms, viss sabojātais, kas nonāk serverī, tur paliek.

Auditā šī pārbaude pirmajā palaidienā atrada, ka divi publicēti pārskati (2026-05-19,
2026-05-22) atsaucas uz hero attēlu un `og:image`, kuru nav — t.i. katrs to ierakstu
share X vai Facebook dod tukšu kartīti — un ka veselas 34 `likumi` lapas nav
`sitemap.xml`. Neviens no tiem nav eksotisks; tos vienkārši nebija kam pamanīt.

Ko pārbauda:
  1. katrs `src=` / `href=` visos HTML — vai mērķa fails eksistē kokā;
  2. `og:image` / `twitter:image` — tie ir absolūti `https://atmina.lv/...` URL,
     tāpēc tos kartē atpakaļ uz koku (tieši šeit atklājās brief attēlu robi);
  3. `sitemap.xml` `<loc>` kopa pret emitēto `.html` kopu — abos virzienos.

Ārējie URL (cita host), `mailto:`, `tel:`, `data:`, tīri fragmenti (`#x`) tiek
izlaisti — CSP allowlist tos sedz atsevišķi, un tos šis rīks pārbaudīt nevar.

Zināmie, apzināti pieņemtie izņēmumi dzīvo `scripts/output_check_allowlist.txt`
(viens paterns rindā, `#` komentāri). Tas ir apzināti tievs — ja saraksts sāk augt,
tas ir signāls, ka kaut kas ražo robus, nevis ka vajag garāku allowlist.

Saucēji tiek drukāti VIENMĒR (2026-08-09). Līdz tam tie stāvēja aiz `--verbose`,
un abi izsaucēji (`check.sh`, `deploy.sh`) to nepadeva astoņas dienas, tāpēc
vienīgais skaitlis zaļajā rindā bija allowlist izmērs — t.i. tas, ko rīks
IGNORĒJA, nevis tas, ko izlasīja. Saucējam jābūt koda, ne konfigurācijas
faktam: karogs, kas jāatceras padot, agrāk vai vēlāk netiek padots, un neviens
tests par to nekrīt. `--verbose` paliek pieņemts no-op (tāpat kā `deploy.sh`
pieņem `--no-delete`), lai vecās komandrindas nesalūztu.

Lietošana:
    .venv/Scripts/python.exe scripts/check_output.py
Izejas kods: 0 = tīrs, 1 = atrasti robi.
"""

from __future__ import annotations

import argparse
import re
import sqlite3
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

ROOT = REPO / "output" / "atmina"
DB_PATH = REPO / "data" / "atmina.db"
ALLOWLIST = REPO / "scripts" / "output_check_allowlist.txt"
BASE_URL = "https://atmina.lv"

# src=/href= ar dubultpēdiņām — renderis tās lieto konsekventi.
_REF_RE = re.compile(r"""\b(?:src|href)\s*=\s*"([^"]*)\"""", re.IGNORECASE)
_META_RE = re.compile(
    r"""<meta[^>]*\b(?:property|name)\s*=\s*"(og:image|twitter:image)"[^>]*"""
    r"""\bcontent\s*=\s*"([^"]*)\"""",
    re.IGNORECASE,
)
_LOC_RE = re.compile(r"<loc>([^<]*)</loc>")

SKIP_SCHEMES = ("mailto:", "tel:", "data:", "javascript:", "blob:")


def load_allowlist() -> list[str]:
    if not ALLOWLIST.exists():
        return []
    out = []
    for raw in ALLOWLIST.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            out.append(line)
    return out


def resolve(ref: str, page: Path) -> Path | None:
    """URL/ceļš → fails kokā, vai None, ja to nav jēgas pārbaudīt."""
    ref = ref.strip()
    if not ref or ref.startswith("#") or ref.lower().startswith(SKIP_SCHEMES):
        return None

    if ref.startswith("//"):
        return None  # protokola-relatīvs = ārējs
    if ref.startswith(("http://", "https://")):
        parsed = urlparse(ref)
        if f"{parsed.scheme}://{parsed.netloc}" != BASE_URL:
            return None  # cits hosts — ārpus šī rīka tvēruma
        path = parsed.path
        base = ROOT
    else:
        path = urlparse(ref).path
        base = ROOT if path.startswith("/") else page.parent

    if not path:
        return None
    path = unquote(path).lstrip("/") if base is ROOT else unquote(path)
    target = (base / path).resolve()
    # Katalogs (piem. "/" vai "politiki/") → index.html
    if target.is_dir() or path.endswith("/") or not path:
        target = target / "index.html"
    return target


def _suppressed(allow: list[str], hits: dict[str, int] | None, *texts: str) -> bool:
    """Vai kāds allowlist paterns apklusina šo robu — un KURŠ.

    `hits` ir uzskaite, kas ļauj pēc palaidiena pateikt, cik katrs paterns
    apslāpēja. Bez tās dzīvs paterns un mirlis ieraksts izskatās vienādi:
    2026-08-09 mērījumā divi no četriem paterniem sen neapklusināja neko, jo
    cēlonis bija novērsts un ierakstu neviens neizravēja.
    """
    for pat in allow:
        if any(pat in t for t in texts):
            if hits is not None:
                hits[pat] = hits.get(pat, 0) + 1
            return True
    return False


def check_refs(allow: list[str], hits: dict[str, int] | None = None) -> list[str]:
    problems: list[str] = []
    pages = sorted(ROOT.rglob("*.html"))
    n_refs = 0
    for page in pages:
        try:
            html = page.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        found: list[tuple[str, str]] = [("ref", m.group(1)) for m in _REF_RE.finditer(html)]
        found += [(m.group(1), m.group(2)) for m in _META_RE.finditer(html)]
        for kind, ref in found:
            target = resolve(ref, page)
            if target is None:
                continue
            n_refs += 1
            if target.exists():
                continue
            rel = page.relative_to(ROOT).as_posix()
            if _suppressed(allow, hits, ref, rel):
                continue
            problems.append(f"{rel}: {kind} -> {ref}")
    print(f"    pārbaudītas {len(pages)} lapas, {n_refs} iekšējās atsauces")
    # Saucējs 0 nav tīrs rezultāts — tas ir salauzti vārti (CLAUDE.md).
    if not pages:
        problems.append("uzbūvētajā kokā nav nevienas HTML lapas — nav ko pārbaudīt")
    return problems


def check_sitemap(allow: list[str], hits: dict[str, int] | None = None) -> list[str]:
    sitemap = ROOT / "sitemap.xml"
    if not sitemap.exists():
        return ["sitemap.xml neeksistē"]
    locs = set()
    for m in _LOC_RE.finditer(sitemap.read_text(encoding="utf-8")):
        path = urlparse(m.group(1)).path.lstrip("/")
        locs.add(path or "index.html")
    emitted = {p.relative_to(ROOT).as_posix() for p in ROOT.rglob("*.html")}
    # 404.html nav indeksējama; OG/preview palīglapas arī ne.
    emitted -= {"404.html"}

    problems = []
    for loc in sorted(locs - emitted):
        if _suppressed(allow, hits, loc):
            continue
        problems.append(f"sitemap.xml: <loc> uz neesošu lapu -> {loc}")
    for page in sorted(emitted - locs):
        if _suppressed(allow, hits, page):
            continue
        problems.append(f"sitemap.xml: emitēta lapa nav sitemap -> {page}")
    print(f"    sitemap {len(locs)} <loc>, kokā {len(emitted)} indeksējamas lapas")
    return problems


def check_publish_gate(allow: list[str], hits: dict[str, int] | None = None) -> list[str]:
    """Publish-gate (T15, 2026-08-09): neviens deploy nedrīkst aiznest uz
    hostingu blog/<datums>.html, kuras briefs DB nav izgājis publicēšanas
    vārtus. check.sh APZINĀTI renderē melnrakstus kokā (render vingrināšana),
    un additīvais deploy tos tad publicē uz mūžu — 2026-08-09 08-09 pārskats
    tā nonāca live ar NVO lapas deploy, pirms vārtiem.

    v1 patiesības avots (heiristika, 2026-08-09): briefam jābūt
    `brief_images.approved=1` rindai — attēla apstiprinājums bija vienīgais
    mašīnlasāmais vārts, kas toreiz eksistēja. Tas noķer 2026-08-09 incidentu,
    bet ne blakusklasi: melnraksts, kuram attēls JAU ir apstiprināts, bet
    korektūra un operatora atļauja vēl nav, to izietu.

    v2 (2026-08-18, T15 atlikums): papildus prasa EKSPLICĪTU atļauju —
    `publish_approvals` rindu ar lapas slugu (`scripts/approve_publish.py`).
    Abi vārti ir UN, nevis VAI: attēls paliek atsevišķa prasība, jo tas ir par
    citu faktu (hero eksistē) nekā atļauja (šis teksts drīkst iet ārā).

    Sasaiste ar lapu iet caur SLUGU, ne datumu vien — dienas un nedēļas
    pārskatam var būt viens subjekta datums (`brief_publish_key`).
    """
    blog_dir = ROOT / "blog"
    if not blog_dir.exists():
        print("    publish-gate: blog/ nav kokā — 0 lapu, nav ko pārbaudīt")
        return []
    pages = sorted(blog_dir.glob("*.html"))
    if not pages:
        return ["publish-gate: blog/ direktorija tukša — nav ko pārbaudīt"]

    if not DB_PATH.exists():
        return [f"publish-gate: DB {DB_PATH} neeksistē — nevar pārbaudīt = nevar deployēt"]
    try:
        from src.briefs import brief_publish_key, brief_subject_date

        db = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        db.row_factory = sqlite3.Row
        briefs: dict[str, int] = {}  # lapas slugs -> note_id (jaunākā rinda)
        for r in db.execute(
            "SELECT id, topic, content, created_at, note_type FROM context_notes"
            " WHERE note_type IN ('daily_brief','weekly_brief')"
            " ORDER BY created_at DESC"
        ):
            d = brief_subject_date(r["topic"], r["content"], r["created_at"])
            if not d:
                continue
            key = brief_publish_key(r["note_type"], d)
            if key not in briefs:
                briefs[key] = r["id"]  # DESC kārtojumā pirmā rinda ir jaunākā
        approved = {
            r["note_id"]
            for r in db.execute("SELECT note_id FROM brief_images WHERE approved = 1")
        }
        # Trūkstoša tabula = vārti, kas nevar krist. Nemēģinām to uzskatīt par
        # „nav apstiprinājumu": vecs DB ir jāmigrē (init_db / backfill), nevis
        # klusi jāpalaiž garām.
        approvals = {
            r["subject_key"] for r in db.execute("SELECT subject_key FROM publish_approvals")
        }
        db.close()
    except sqlite3.Error as e:
        return [f"publish-gate: DB kļūda ({e}) — nevar pārbaudīt = nevar deployēt"]

    problems: list[str] = []
    n_ok = 0
    n_no_approval = 0
    for page in pages:
        m = re.match(r"^(?:nedela-)?(\d{4}-\d{2}-\d{2})\.html$", page.name)
        if not m:
            continue  # blog.html indekss u.c. — nav brief lapa
        key = page.name[: -len(".html")]
        date = m.group(1)
        rel = f"blog/{page.name}"
        note_id = briefs.get(key)
        if note_id is None:
            p = f"publish-gate: {rel} — orfāns (DB nav brief ar subjekta datumu {date})"
        elif note_id not in approved:
            p = f"publish-gate: {rel} — brief #{note_id} bez approved=1 attēla"
        elif key not in approvals:
            n_no_approval += 1
            p = (f"publish-gate: {rel} — nav publicēšanas apstiprinājuma"
                 f" (publish_approvals '{key}'); pēc korektūras:"
                 f" .venv/Scripts/python.exe scripts/approve_publish.py {key}")
        else:
            n_ok += 1
            continue
        if _suppressed(allow, hits, p, rel):
            continue
        problems.append(p)
    print(f"    publish-gate: {len(pages)} blog lapas, {n_ok} apstiprinātas, "
          f"{n_no_approval} bez publicēšanas apstiprinājuma, "
          f"{len(problems)} bloķētas")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--verbose", action="store_true",
                    help="pieņemts no-op — saucēji tiek drukāti vienmēr")
    ap.add_argument("--refs-only", action="store_true", help="izlaist sitemap pārbaudi")
    ap.add_argument("--publish-gate", action="store_true",
                    help="pievienot publish-gate pārbaudi (T15) pārējiem čekiem")
    ap.add_argument("--publish-gate-only", action="store_true",
                    help="palaist TIKAI publish-gate (deploy.sh preflight)")
    args = ap.parse_args()

    if not ROOT.exists():
        print(f"check_output: {ROOT} neeksistē — vispirms uzrenderē vietni", file=sys.stderr)
        return 1

    allow = load_allowlist()
    hits: dict[str, int] = {}

    if args.publish_gate_only:
        problems = check_publish_gate(allow, hits)
    else:
        problems = check_refs(allow, hits)
        if not args.refs_only:
            problems += check_sitemap(allow, hits)
        if args.publish_gate:
            problems += check_publish_gate(allow, hits)

    if problems:
        print(f"check_output: {len(problems)} robi uzbūvētajā kokā", file=sys.stderr)
        for p in problems:
            print(f"  {p}", file=sys.stderr)
        if allow:
            print(
                f"\n(allowlist: {len(allow)} paterni no "
                f"{ALLOWLIST.relative_to(REPO).as_posix()})",
                file=sys.stderr,
            )
        return 1

    unused = [p for p in allow if not hits.get(p)]
    line = (f"check_output: tīrs — {len(allow)} allowlist paterni, "
            f"apslāpēti {sum(hits.values())} robi")
    if unused:
        line += f"; BEZ TRĀPĪJUMA: {', '.join(unused)}"
    print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
