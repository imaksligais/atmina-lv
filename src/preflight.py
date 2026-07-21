import os
import sys



def preflight_check(db_path: str | None = None) -> tuple[bool, list[str]]:
    issues = []
    critical_fail = False

    # 1. Database accessible and schema current
    try:
        from src.db import init_db, get_db

        init_db(db_path)
        db = get_db(db_path)
        tables = [
            r[0]
            for r in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        ]
        required = [
            "tracked_politicians", "sources", "social_accounts", "documents",
            "document_chunks", "analyses", "claims", "contradictions",
            "oppo_briefs", "context_notes", "logs", "metadata",
        ]
        for t in required:
            if t not in tables:
                issues.append(f"CRITICAL: Missing table '{t}'")
                critical_fail = True
        db.close()
    except Exception as e:
        issues.append(f"CRITICAL: Database error: {e}")
        critical_fail = True

    # 2. sources.yaml parses
    try:
        import yaml

        with open("sources.yaml", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if "sources" not in data:
            issues.append("CRITICAL: sources.yaml missing 'sources' key")
            critical_fail = True
        else:
            active = [s for s in data["sources"] if s.get("tier", 3) <= 2]
            if not active:
                issues.append("CRITICAL: No active sources (tier 1 or 2) in sources.yaml")
                critical_fail = True
    except FileNotFoundError:
        issues.append("CRITICAL: sources.yaml not found")
        critical_fail = True
    except Exception as e:
        issues.append(f"CRITICAL: sources.yaml parse error: {e}")
        critical_fail = True

    # 3. Embedding model loads
    try:
        from src.embeddings import embed_text

        vec = embed_text("test")
        if len(vec) != 384:
            issues.append(f"CRITICAL: Embedding dimension mismatch: {len(vec)} != 384")
            critical_fail = True
    except Exception as e:
        issues.append(f"CRITICAL: Embedding model failed to load: {e}")
        critical_fail = True

    # 4. Social media API credentials
    try:
        from src.credentials import verify_all

        creds = verify_all()
        missing = [k for k, v in creds.items() if not v]
        if missing:
            issues.append(f"WARNING: Missing credentials: {', '.join(missing)}")
    except Exception as e:
        issues.append(f"WARNING: Credential check failed: {e}")

    # 5. party_ideology.md existence
    if not os.path.exists("party_ideology.md"):
        issues.append("WARNING: party_ideology.md not found")

    # 6. campaign_voice.md existence
    if not os.path.exists("campaign_voice.md"):
        issues.append("WARNING: campaign_voice.md not found")

    # 7. gdpr_assessment.md existence
    if not os.path.exists("gdpr_assessment.md"):
        issues.append("WARNING: gdpr_assessment.md not found")

    # 8. Check for LOCAL ONLY markers in party_ideology.md
    #
    # This is a safety check — the <!-- LOCAL ONLY --> marker tags content
    # that must never be sent to Claude. Previously an unreadable file
    # silently passed the check (bare `except Exception: pass`), which meant
    # a transient read error could hide the presence of sensitive content
    # from the operator. The bypass was flagged in the 2026-04-11 silent-
    # swallow audit. We now surface the failure as a WARNING so the operator
    # knows the safety check could not run and can re-verify manually before
    # any export.
    if os.path.exists("party_ideology.md"):
        try:
            with open("party_ideology.md", encoding="utf-8") as f:
                content = f.read()
            if "<!-- LOCAL ONLY -->" in content:
                issues.append(
                    "WARNING: party_ideology.md contains <!-- LOCAL ONLY --> sections "
                    "— these must never be sent to Claude"
                )
        except OSError as e:
            issues.append(
                f"WARNING: cannot read party_ideology.md to verify <!-- LOCAL ONLY --> "
                f"markers ({e}); the safety check is BYPASSED until the file is "
                f"readable — verify manually before any Claude export"
            )
        except UnicodeDecodeError as e:
            issues.append(
                f"WARNING: party_ideology.md is not valid UTF-8 ({e}); the "
                f"<!-- LOCAL ONLY --> safety check is BYPASSED — fix encoding "
                f"and re-run preflight before any Claude export"
            )

    passed = not critical_fail
    return passed, issues


def main():
    ok, issues = preflight_check()
    print(f"Preflight: {'PASS' if ok else 'FAIL'}")
    for issue in issues:
        print(f"  - {issue}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
