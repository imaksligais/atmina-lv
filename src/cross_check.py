"""Weekly full pairwise contradiction scan per politician."""

from pathlib import Path

from src.db import get_db
from src.embeddings import embed_text

_DB_PATH = Path(__file__).parent.parent / "data" / "atmina.db"


def weekly_cross_check(db_path: str = None, similarity_threshold: float = 0.75) -> list[dict]:
    """
    Full pairwise similarity scan per politician.
    Returns list of potential contradictions for human review.

    For each politician:
      1. Get ALL their claims
      2. For each pair of claims on the SAME topic, compute embedding similarity
      3. If similarity > threshold, check if stances DIFFER
      4. If stances differ + high similarity = potential contradiction
      5. Skip pairs that are already in contradictions table
    """
    db_path = db_path or str(_DB_PATH)
    db = get_db(db_path)

    # Get all politicians with at least one position claim. Saeima vote rows
    # are intentionally excluded from this weekly scanner — vote-vs-vote
    # pairs are procedural noise and flood the candidate list, while
    # rhetoric-vs-action contradictions are handled by the per-claim
    # contradiction detection flow in save_analysis via search_similar_claims
    # with a directional claim_type_filter. This module only catches
    # rhetorical flip-flops (position vs position).
    politicians = db.execute("""
        SELECT DISTINCT c.opponent_id, p.name, p.party
        FROM claims c
        JOIN tracked_politicians p ON c.opponent_id = p.id
        WHERE c.claim_type = 'position'
        ORDER BY p.name
    """).fetchall()

    # Get existing contradiction pairs to skip
    existing_pairs = set()
    for row in db.execute("SELECT claim_old_id, claim_new_id FROM contradictions").fetchall():
        existing_pairs.add((row[0], row[1]))
        existing_pairs.add((row[1], row[0]))

    potential = []

    for pol in politicians:
        pid = pol["opponent_id"]

        # Get all position claims for this politician (votes excluded — see
        # module docstring above).
        claims = db.execute("""
            SELECT id, topic, stance, quote, confidence, salience,
                   source_url, stated_at
            FROM claims
            WHERE opponent_id = ?
              AND claim_type = 'position'
            ORDER BY stated_at
        """, (pid,)).fetchall()

        if len(claims) < 2:
            continue

        # Group by topic
        by_topic: dict[str, list[dict]] = {}
        for c in claims:
            topic = c["topic"]
            by_topic.setdefault(topic, []).append(dict(c))

        # For each topic with 2+ claims, check pairwise
        for topic, topic_claims in by_topic.items():
            if len(topic_claims) < 2:
                continue

            # Embed all stances for this topic
            for c in topic_claims:
                c["embedding"] = embed_text(f"{c['topic']}: {c['stance']}")

            # Pairwise comparison
            for i in range(len(topic_claims)):
                for j in range(i + 1, len(topic_claims)):
                    c1, c2 = topic_claims[i], topic_claims[j]

                    # Skip if already a known contradiction
                    if (c1["id"], c2["id"]) in existing_pairs:
                        continue

                    # Compute cosine similarity
                    sim = _cosine_similarity(c1["embedding"], c2["embedding"])

                    if sim > similarity_threshold:
                        # High similarity on same topic — check if stances actually differ
                        # (High similarity means they're ABOUT the same thing,
                        #  but we need human to verify if they CONTRADICT)
                        potential.append({
                            "politician_name": pol["name"],
                            "politician_id": pid,
                            "party": pol["party"],
                            "topic": topic,
                            "claim_1_id": c1["id"],
                            "claim_1_stance": c1["stance"],
                            "claim_1_date": c1["stated_at"],
                            "claim_1_source": c1["source_url"],
                            "claim_2_id": c2["id"],
                            "claim_2_stance": c2["stance"],
                            "claim_2_date": c2["stated_at"],
                            "claim_2_source": c2["source_url"],
                            "similarity": round(sim, 3),
                        })

    db.close()

    # Sort by similarity descending (most likely contradictions first)
    potential.sort(key=lambda x: x["similarity"], reverse=True)

    return potential


def _cosine_similarity(a, b) -> float:
    """Compute cosine similarity between two embedding vectors."""
    import numpy as np
    a = np.array(a)
    b = np.array(b)
    dot = np.dot(a, b)
    norm = np.linalg.norm(a) * np.linalg.norm(b)
    if norm == 0:
        return 0.0
    return float(dot / norm)


def print_cross_check_report(results: list[dict]) -> None:
    """Print a readable report of potential contradictions."""
    if not results:
        print("Nav atrasti potenciāli jauni pretrunu kandidāti.")
        return

    print(f"Atrasti {len(results)} potenciāli pretrunu kandidāti:\n")
    for i, r in enumerate(results, 1):
        print(f"--- #{i} ({r['politician_name']}, {r['party']}) — {r['topic']} [sim={r['similarity']}] ---")
        print(f"  Claim {r['claim_1_id']} ({r['claim_1_date'][:10] if r['claim_1_date'] else '?'}):")
        print(f"    {r['claim_1_stance'][:120]}")
        print(f"  Claim {r['claim_2_id']} ({r['claim_2_date'][:10] if r['claim_2_date'] else '?'}):")
        print(f"    {r['claim_2_stance'][:120]}")
        print()


if __name__ == "__main__":
    results = weekly_cross_check()
    print_cross_check_report(results)
