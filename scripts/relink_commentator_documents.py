"""Re-link commentator-authored documents after demotion.

Strategy:
1. DELETE document_politicians rows where role='subject' AND politician_id IN demoted_pids.
   These were inserted by `_store_tweets` first_party path; after demotion these
   handles go through relay path which leaves politician_links empty.
2. Run link_politicians_to_documents(rescan_all=True). It will pick up the now
   unlinked docs (no document_politicians row at all) and text-scan for any
   tracked politician mentions, attaching role='mentioned' or 'mention_target'
   as appropriate.

Result: a Heinrih5 tweet that mentions "Melni" in its body now links Melnis
(157) as 'mentioned' and is visible on Melnis's profile X subtab.
"""
import argparse
import sqlite3

DEMOTED_PIDS = [62, 169, 171, 172, 174, 175, 177]


def remove_subject_links_for_demoted(
    con: sqlite3.Connection, demoted_pids: list[int]
) -> int:
    """DELETE document_politicians rows where role='subject' AND politician_id IN demoted.
    Returns count of rows deleted."""
    placeholders = ",".join("?" * len(demoted_pids))
    cur = con.cursor()
    cur.execute(
        f"DELETE FROM document_politicians "
        f"WHERE role='subject' AND politician_id IN ({placeholders})",
        demoted_pids,
    )
    con.commit()
    return cur.rowcount


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="data/atmina.db")
    parser.add_argument("--days", type=int, default=30,
                        help="Window for link_politicians_to_documents rescan")
    args = parser.parse_args()

    con = sqlite3.connect(args.db)
    removed = remove_subject_links_for_demoted(con, DEMOTED_PIDS)
    print(f"Removed {removed} role='subject' links for {len(DEMOTED_PIDS)} demoted commentators")
    con.close()

    from src.matcher import link_politicians_to_documents
    linked = link_politicians_to_documents(days=args.days, rescan_all=True)
    total_links = sum(len(v) for v in linked.values())
    print(f"link_politicians_to_documents: {len(linked)} docs got new links, "
          f"{total_links} total politician-doc links added")


if __name__ == "__main__":
    main()
