"""scripts/audit_dp_readds.scan_readds (audit-integrity check 23).

Failure named first: the check's «SQL kļūdas» count is permanently non-zero
(16.11.: 9 in 8 files) because it executes rollback statements that cannot
restore a link — DELETEs whose subquery reads `tracked_politicians`, and
`UPDATE … SET extracted_at` — against an in-memory copy that has only the
junction table. A real error then hides among the noise. Statements that can
restore a link (INSERT, role UPDATE) must still run and still count errors.
"""

import sqlite3

from scripts.audit_dp_readds import scan_readds


def test_only_restoring_statements_run_and_count_errors(tmp_path):
    db = sqlite3.connect(":memory:")
    db.execute("CREATE TABLE document_politicians (document_id INT, politician_id INT, "
               "role TEXT, created_at TEXT)")
    db.execute("INSERT INTO document_politicians VALUES (1, 7, 'subject', '2026-11-10 00:00:00')")

    (tmp_path / "rollback_seed_x.sql").write_text(
        "-- Rollback seed\nBEGIN;\n"
        "DELETE FROM document_politicians WHERE politician_id = "
        "(SELECT id FROM tracked_politicians WHERE name = 'X');\n"
        "UPDATE document_politicians SET extracted_at = NULL WHERE role = 'subject' "
        "AND document_id IN (SELECT id FROM documents);\nCOMMIT;\n", encoding="utf-8")
    (tmp_path / "rollback_links_y.sql").write_text(
        "BEGIN;\n"
        "INSERT INTO document_politicians (document_id, politician_id, role, created_at) "
        "VALUES (1, 7, 'subject', '2026-09-01 00:00:00');\n"
        "INSERT INTO document_politicians (document_id, nope) VALUES (2, 8);\nCOMMIT;\n",
        encoding="utf-8")

    res = scan_readds(db, tmp_path, commit_time=lambda p: "2026-10-01 00:00:00")

    assert res["files"] == 2
    assert "rollback_seed_x.sql" not in res["errors"], res["errors"]
    assert res["error_total"] == 1  # the broken INSERT is still counted
    assert [(r["document_id"], r["politician_id"]) for r in res["readded"]] == [(1, 7)]
