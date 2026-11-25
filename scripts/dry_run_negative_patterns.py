"""Dry-run: ko darītu `negative_patterns` papildinājums vienam politiķim. Tikai lasa.

Pārbauda (pirms rakstīšanas, `wiki/operations/seeding.md` § `negative_patterns`): visi doki,
kas DB saistīti ar politiķi, + doki, kuru tekstā ir `--grep` apakšvirkne. Katram — matcher
iznākums pirms un pēc, kad pid sarakstam pieliek jaunos paternus (DB netiek mainīta).
Atskaite: cik saišu paliek, cik zūd (katra ar fragmentu) — zudušās jāizlasa: īstu saišu
zudums > 0 → paternu NEliek. Pirmo reizi lietots 2026-11-22 (218 Lapiņš, 241 VK).

    .venv/Scripts/python.exe scripts/dry_run_negative_patterns.py --pid 241 --neg "Segalovič|Segalovic" --grep "Valsts kontrol"
"""
import argparse
import re
import sqlite3
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import src.matcher as m  # noqa: E402
from src.db import PRODUCTION_DB_PATH  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pid", type=int, required=True)
    ap.add_argument("--neg", required=True, help="jaunie paterni, atdalīti ar |")
    ap.add_argument("--grep", default=None, help="papildu doki ar šo apakšvirkni tekstā")
    ap.add_argument("--since", default="2026-09-01", help="--grep dokiem: scraped_at no")
    a = ap.parse_args()
    neg_new = [x for x in a.neg.split("|") if x]

    c = sqlite3.connect(PRODUCTION_DB_PATH)
    docs = {r[0] for r in c.execute(
        "SELECT document_id FROM document_politicians WHERE politician_id=?", (a.pid,))}
    if a.grep:
        docs |= {r[0] for r in c.execute(
            "SELECT id FROM documents WHERE content LIKE ? AND scraped_at >= ?",
            (f"%{a.grep}%", a.since))}
    docs = sorted(docs)
    text = {}
    for i in range(0, len(docs), 500):
        chunk = docs[i:i + 500]
        for d, t, ti in c.execute(
                f"SELECT id, content, title FROM documents WHERE id IN ({','.join('?' * len(chunk))})", chunk):
            text[d] = (t or "") + "\n" + (ti or "")

    def run() -> dict[int, bool]:
        m._clear_politician_cache()
        return {d: any(p == a.pid for p, _ in m.match_politicians(text[d])) for d in text}

    before = run()
    orig = m._load_politician_forms

    def patched(db_path=None):
        out = [(p, f, first, (list(neg) + neg_new) if p == a.pid else neg)
               for p, f, first, neg in orig(db_path)]
        m._politician_forms_cache = out
        return out

    m._load_politician_forms = patched
    after = run()
    lost = [d for d in text if before[d] and not after[d]]
    print(f"doki pārbaudīti {len(text)}; matcher pirms {sum(before.values())}, "
          f"pēc {sum(after.values())}, zūd {len(lost)} (izlasi katru):")
    for d in lost:
        t = text[d]
        hit = next((t.find(p) for p in neg_new if p in t), 0)
        print(f"  {d}: {t[max(0, hit - 80):hit + 60].replace(chr(10), ' ')}")


if __name__ == "__main__":
    main()
