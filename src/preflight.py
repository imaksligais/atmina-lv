import importlib.util
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent

# Modules save_analysis() needs to embed a claim. Checked by spec, not by
# import — find_spec costs a stat walk, importing sentence_transformers costs
# seconds and loads torch.
_EMBEDDING_DEPS = ("sentence_transformers", "simplemma")

_analysis_env_checked = False
_embeddings_live_checked = False


def repo_python() -> str | None:
    """Path to the repo's own venv interpreter, if it exists."""
    for rel in ("Scripts/python.exe", "bin/python"):
        candidate = _REPO_ROOT / ".venv" / rel
        if candidate.exists():
            return str(candidate)
    return None


def ensure_analysis_env() -> None:
    """Fail loudly when the running interpreter cannot embed claims.

    ``save_analysis()`` needs the embedding stack for every claim it stores.
    Run under an interpreter that lacks it (a foreign venv on PATH, a bare
    system python), a call WITH claims fails honestly — atomicity holds and
    the result carries ``transaction_rolled_back``. A **zero-claim** call in
    that same broken environment, however, returns ``status="success"``,
    because it never reaches ``embed_text``. "0 pozīciju" then looks exactly
    like a correct "I read these documents and there was nothing to extract" —
    the Working Conventions § *Silent success is a defect class* shape. Six
    parallel agents hit this on 2026-07-24; each recovered, but only because
    each happened to notice.

    Checking the dependency rather than ``sys.executable`` keeps this honest
    for the non-Claude-Code harnesses in wiki/operations/portability.md: any
    interpreter that CAN embed passes, wherever its venv lives.

    Raises:
        RuntimeError: with the repo venv interpreter path, when available.
    """
    global _analysis_env_checked
    if _analysis_env_checked:
        return

    missing = [m for m in _EMBEDDING_DEPS if importlib.util.find_spec(m) is None]
    if not missing:
        _analysis_env_checked = True
        return

    hint = repo_python()
    raise RuntimeError(
        f"Incomplete analysis environment: {', '.join(missing)} not importable "
        f"by {sys.executable}. A zero-claim save_analysis() would return "
        f'status="success" here and be indistinguishable from a correct empty '
        f"result, so it stops instead. "
        + (f"Re-run with the repo venv: {hint}"
           if hint else "Activate the repo .venv and re-run.")
    )


def ensure_embeddings_live() -> None:
    """Stricter sibling of ``ensure_analysis_env()`` for BULK-WRITE entry points.

    ``ensure_analysis_env()`` asks "is it installed?" (``find_spec``) because it
    runs in ``save_analysis()``'s hot path, where importing torch would cost
    seconds on every call. That answer is not the same as "does it work": a venv
    can carry ``sentence_transformers`` whose import dies on a broken native
    dependency. On 2026-07-25 ``find_spec`` returned True while the import
    raised ``OSError`` on torchcodec DLLs, so a bulk ingest passed the cheap
    guard, wrote 20 vote rows, and only then failed on its first claim.

    A script about to write thousands of claims should pay one real embed
    (~seconds, once) rather than discover that at write #1. One call covers the
    wrong interpreter, broken native libs, an undownloaded model and a dead HF
    connection alike. Keep this OUT of hot paths; it is a startup gate.

    Raises:
        RuntimeError: naming the failing interpreter and the repo venv path.
    """
    global _embeddings_live_checked
    if _embeddings_live_checked:
        return

    ensure_analysis_env()
    try:
        from src.embeddings import embed_text

        dim = len(embed_text("test"))
    except Exception as e:
        hint = repo_python()
        raise RuntimeError(
            f"Embedding stack not usable by {sys.executable}: {e}. "
            + (f"Re-run with the repo venv: {hint}"
               if hint else "Activate the repo .venv and re-run.")
        ) from e
    if dim != 384:
        raise RuntimeError(f"Embedding dimension mismatch: {dim} != 384")
    _embeddings_live_checked = True


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
            "context_notes", "logs", "metadata",
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

    # 3. Embedding model loads (same check the bulk-write gate uses)
    try:
        ensure_embeddings_live()
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

    # Checks 5–8 removed 2026-08-15 — politracker residue that fired forever.
    #
    # They required `party_ideology.md`, `campaign_voice.md` and
    # `gdpr_assessment.md` in the repo root. None of the three has existed
    # anywhere in the tree for the whole life of atmina (verified: `find` over
    # the repo returns nothing, and the only other mentions are
    # `scripts/migrate_db.py:70-71`, which lists the first two as content to
    # PURGE, and `.claude/agents/quality-reviewer.md`, whose neutrality gate
    # treats the literal strings `party_ideology|campaign_voice` as forbidden
    # CAMPAIGN LANGUAGE). So every ingest printed three WARNINGs demanding files
    # whose very names the publish gate classifies as contamination — and check
    # 8 (`<!-- LOCAL ONLY -->` markers) was wrapped in
    # `if os.path.exists("party_ideology.md")`, so it never ran at all.
    #
    # Three warnings that fire on every single run are not a safety net; they
    # are what teaches an operator to skim past preflight output, including the
    # checks above that CAN fail. Deleting them raises the signal of 1–4.
    #
    # NB for whoever reads this next: dropping check 7 is NOT a statement that
    # GDPR documentation is unnecessary. It is a statement that a WARNING for a
    # file that has never existed was never evidence that it did. If a data-
    # protection assessment is wanted, that is a real piece of work, not a line
    # here. (The public privacy statement lives in `templates/about.html.j2`.)

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
