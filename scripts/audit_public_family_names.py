"""Vārti: vai politiķu radinieku vārdi (no VID deklarāciju ģimenes sadaļas)
nekur neparādās publiskajā būves kokā.

Ģimenes datus nepublicējam (docs/data-policy.md § 1, operatora lēmums
2026-11-27). Vārdu kopa — `src.vad.family.private_family_names()` (jaunā un vecā
forma; bez pašiem izsekotajiem politiķiem). Meklē 2–4 vārdu virknes katrā
teksta failā (html/json/xml/txt/md/js), bez reģistra.

Lietojums:
    .venv/Scripts/python.exe scripts/audit_public_family_names.py [--output output/atmina]

Krīt (exit 1) tikai trāpījums ŠĪ politiķa profila lapā (`politiki/<slug>.html`)
— tā ir vieta, kur radinieka vārds nāktu no viņa paša deklarācijas. Citur tas
pats vārds parasti ir publiska persona ziņās vai darījuma puse cita politiķa
deklarācijā — tos drukā kā informāciju; radinieks ar izsekota politiķa vārdu
parādās kā politiķis (saites) — atsevišķa informācijas grupa. 2026-11-27: renders
bez slēpšanas → 249 trāpījumi profilos (krīt), ar slēpšanu → 0.
`EXPLAINED` = izskaidroti izņēmumi ar iemeslu.

Exit 0 — nav neizskaidrotu trāpījumu profilos; 1 — ir.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

TEXT_SUFFIXES = {".html", ".json", ".xml", ".txt", ".md", ".js"}
# (vārds, profila fails) → (sagaidāmais trāpījumu skaits, iemesls). Skaits
# precīzs: ja vārds parādās vēlreiz (piem., deklarācijā), vārti krīt.
EXPLAINED = {
    ("edvards slesers", "politiki/ainars-slesers.html"): (
        1, "pats publiska persona — LPV ekonomikas ministra amata kandidāts; politiķa paša tvīts (2026-05-18)"),
}


def _plain_text(path: Path) -> str:
    """Teksts bez HTML tagiem un entītijām; JSON — atkodētas \\uXXXX virknes."""
    text = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix.lower() == ".json":
        try:
            text = json.dumps(json.loads(text), ensure_ascii=False)
        except ValueError:
            pass
    # Formatēšanas tagi (<b>, <em> …) vārdu nešķeļ; jebkurš cits tags = robeža
    # (citādi «Staķis</span><span>Edvards Ratnieks» saplūst vienā vārdā).
    text = re.sub(r"</?(?:b|i|em|strong|u|mark|small)(?=[\s>/])[^>]*>", "", text, flags=re.I)
    return html.unescape(re.sub(r"<[^>]+>", " | ", text))


def find_hits(root: Path, names: dict[frozenset[str], set[int]]) -> tuple[int, list[tuple[str, str, str]]]:
    """(failu skaits, [(fails, vārds, konteksts)]) — katrs trāpījums atsevišķi.
    Vārdu secība nav svarīga, reģistrs un garumzīmes arī ne."""
    from src.vad.family import _WORD_RE, name_tokens

    lengths = {len(n) for n in names}
    n_files = 0
    hits: list[tuple[str, str, str]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        n_files += 1
        text = _plain_text(path)
        spans = list(_WORD_RE.finditer(text))
        tokens = [name_tokens(m.group(0))[0] if name_tokens(m.group(0)) else "" for m in spans]
        rel = str(path.relative_to(root)).replace("\\", "/")
        # Blakus vārdi = tikai atstarpe starp tiem (ne «→», «,», «·»), citādi
        # «Kols → Jānis Dombrava» izskatās pēc «Jānis Kols».
        joined = [not text[spans[j].end():spans[j + 1].start()].strip()
                  for j in range(len(spans) - 1)]
        for k in lengths:
            for i in range(len(tokens) - k + 1):
                if not all(joined[i:i + k - 1]):
                    continue
                cand = frozenset(tokens[i:i + k])
                if len(cand) == k and cand in names:
                    start = spans[i].start()
                    ctx = " ".join(text[max(0, start - 120):start + 60].split())
                    hits.append((rel, " ".join(tokens[i:i + k]), ctx))
    return n_files, hits


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default=str(REPO_ROOT / "output" / "atmina"))
    ap.add_argument("--db", help="DB ceļš (noklusējums: produkcijas DB)")
    args = ap.parse_args()

    from src.db import get_db
    from src.vad.family import private_family_names

    from src.lv_text import slugify

    db = get_db(args.db) if args.db else get_db()
    pids = [r[0] for r in db.execute("SELECT DISTINCT opponent_id FROM vad_declarations")]
    tracked_rows = db.execute("SELECT id, name FROM tracked_politicians").fetchall()
    profile = {pid: f"politiki/{slugify(name)}.html" for pid, name in tracked_rows}
    names: dict[frozenset[str], set[int]] = defaultdict(set)
    for pid, fam in private_family_names(db, pids).items():
        for n in fam:  # jau ≥2 vārdi (name_variants)
            names[n].add(pid)
    root = Path(args.output)
    n_files, hits = find_hits(root, names)
    print(f"[saucējs] vārdi {len(names)}; faili {n_files} — {root}")
    own, explained, other, politicians = [], [], [], []
    from collections import Counter

    from src.vad.family import name_tokens

    # Radinieks, kura vārds = izsekots politiķis, lapā parādās kā politiķis
    # (saites, citāti, kopīgas organizācijas) — informācija, ne noplūde.
    # Deklarācijas rindās render to tik un tā slēpj (src/vad/family.py).
    tracked = {frozenset(name_tokens(n)) for _pid, n in tracked_rows}

    per_key = Counter()
    for f, name, ctx in hits:
        key = frozenset(name_tokens(name))
        if key in tracked:
            politicians.append((f, name, ctx))
        elif f not in {profile.get(pid) for pid in names[key]}:
            other.append((f, name, ctx))
        else:
            own.append((f, name, ctx))
            per_key[(" ".join(sorted(key)), f)] += 1
    for (name, f), (count, reason) in EXPLAINED.items():
        k = (" ".join(sorted(name.split())), f)
        if per_key.get(k) == count:
            own = [h for h in own if not (h[0] == f and " ".join(sorted(name_tokens(h[1]))) == k[0])]
            explained.append((f, name, reason))
    for label, rows in (("FLAG — paša profilā", own), ("izskaidrots", explained),
                        ("info — cita lapa", other)):
        if label.startswith("info") and len(rows) > 40:
            rows = rows[:40]
        for f, name, ctx in rows:
            print(f"  [{label}] {f} | {name} | …{ctx}…")
    print(f"[{'FLAG' if own else 'ok'}] profilos {len(own)}, izskaidroti {len(explained)}, "
          f"citur {len(other)}, izsekoti politiķi {len(politicians)} (kopā {len(hits)})")
    return 1 if own else 0


if __name__ == "__main__":
    raise SystemExit(main())
