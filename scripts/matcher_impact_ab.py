"""READ-ONLY A/B: run current match_politicians() against all web + vestnesis
documents and diff against existing document_politicians junctions.

Does NOT mutate the DB. Reports four buckets per politician and overall:

  UNCHANGED   — matcher result for this doc identical to current junction
  GAINED      — politician matches now but wasn't in junction before
                (i.e. either bug-fix recovery OR new false positive)
  LOST        — junction has politician but matcher no longer matches
                (i.e. either correct drop of old FP OR new false negative)

Also dumps the top 30 GAINED and 30 LOST samples to .scratch/ab_sample.json
for manual qualitative review.

Usage:
    PYTHONPATH=. python scripts/matcher_impact_ab.py
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

from src.db import get_db
from src.matcher import match_politicians, _filter_vestnesis_strict, _clear_politician_cache


def main() -> int:
    db = get_db()
    cur = db.cursor()

    # All textual docs the matcher operates on in production.
    # Twitter/x_mention go through a different code path (handle-based),
    # so we skip those for a clean matcher A/B.
    cur.execute("""
        SELECT id, platform, source_url, title, content
        FROM documents
        WHERE platform IN ('web', 'web_scraper', 'vestnesis')
          AND content IS NOT NULL
          AND length(content) > 100
        ORDER BY id
    """)
    docs = cur.fetchall()
    print(f"Loaded {len(docs)} matchable docs")

    # Existing junctions, keyed by doc_id.
    cur.execute("SELECT document_id, politician_id, role FROM document_politicians")
    junctions_by_doc: dict[int, set[int]] = defaultdict(set)
    junctions_by_doc_with_role: dict[int, set[tuple[int, str]]] = defaultdict(set)
    for row in cur.fetchall():
        junctions_by_doc[row["document_id"]].add(row["politician_id"])
        junctions_by_doc_with_role[row["document_id"]].add(
            (row["politician_id"], row["role"])
        )
    print(f"Loaded {sum(len(v) for v in junctions_by_doc.values())} junction rows")

    # Politician names for readable output
    cur.execute("SELECT id, name FROM tracked_politicians")
    pname = {r["id"]: r["name"] for r in cur.fetchall()}

    _clear_politician_cache()

    docs_unchanged = 0
    docs_with_gains = 0
    docs_with_losses = 0
    total_gained_links = 0
    total_lost_links = 0
    gained_by_politician: Counter = Counter()
    lost_by_politician: Counter = Counter()
    sample_gains: list[dict] = []
    sample_losses: list[dict] = []

    for i, doc in enumerate(docs, 1):
        if i % 500 == 0:
            print(f"  ... {i}/{len(docs)}")

        text = doc["content"]
        # Mirror production: vestnesis strict filter is applied AFTER
        # match_politicians in the link_politicians_to_documents flow.
        new_matches = match_politicians(text)
        if doc["platform"] == "vestnesis":
            new_matches = _filter_vestnesis_strict(new_matches, text)
        new_pids = {pid for pid, _ in new_matches}

        old_pids = junctions_by_doc.get(doc["id"], set())

        if new_pids == old_pids:
            docs_unchanged += 1
            continue

        gained = new_pids - old_pids
        lost = old_pids - new_pids

        if gained:
            docs_with_gains += 1
            total_gained_links += len(gained)
            for pid in gained:
                gained_by_politician[pid] += 1
            if len(sample_gains) < 30:
                sample_gains.append({
                    "doc_id": doc["id"],
                    "platform": doc["platform"],
                    "source_url": doc["source_url"],
                    "title": (doc["title"] or "")[:120],
                    "gained": [
                        {"id": pid, "name": pname.get(pid, f"???{pid}")}
                        for pid in sorted(gained)
                    ],
                    "text_excerpt": (text or "")[:600],
                })
        if lost:
            docs_with_losses += 1
            total_lost_links += len(lost)
            for pid in lost:
                lost_by_politician[pid] += 1
            if len(sample_losses) < 30:
                sample_losses.append({
                    "doc_id": doc["id"],
                    "platform": doc["platform"],
                    "source_url": doc["source_url"],
                    "title": (doc["title"] or "")[:120],
                    "lost": [
                        {"id": pid, "name": pname.get(pid, f"???{pid}")}
                        for pid in sorted(lost)
                    ],
                    "text_excerpt": (text or "")[:600],
                })

    db.close()

    print()
    print("=" * 70)
    print(f"Total docs scanned:    {len(docs)}")
    print(f"Unchanged:             {docs_unchanged} ({100*docs_unchanged/len(docs):.1f}%)")
    print(f"Docs with gained:      {docs_with_gains}  (+{total_gained_links} links)")
    print(f"Docs with lost:        {docs_with_losses}  (-{total_lost_links} links)")
    print()
    print("Top 15 politicians GAINED (matches the old code missed):")
    for pid, count in gained_by_politician.most_common(15):
        print(f"  +{count:>5}  id={pid:>4}  {pname.get(pid, '?')}")
    print()
    print("Top 15 politicians LOST (matches the old code wrongly included):")
    for pid, count in lost_by_politician.most_common(15):
        print(f"  -{count:>5}  id={pid:>4}  {pname.get(pid, '?')}")
    print()

    out_path = Path(".scratch/ab_sample.json")
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(
        json.dumps({"gains": sample_gains, "losses": sample_losses},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Sample diffs written to {out_path}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
