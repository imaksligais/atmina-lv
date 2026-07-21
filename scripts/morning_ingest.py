"""Morning ingest pipeline: RSS + X timelines + mentions + Vestnesis.

Runs all four steps sequentially with simple timing telemetry.
Skips claim extraction by design (afternoon-only per project decision).
"""
import os
import sys
import time
import traceback
import subprocess
from pathlib import Path

# Windows cp1252 stdout cannot encode LV diacritics or '≤'; reconfigure before any print.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def step(name: str, fn):
    print(f"\n=== [{name}] start ===", flush=True)
    t0 = time.time()
    try:
        out = fn()
        dt = time.time() - t0
        print(f"=== [{name}] OK in {dt:.1f}s ===", flush=True)
        return out
    except Exception as e:
        dt = time.time() - t0
        print(f"=== [{name}] FAILED after {dt:.1f}s: {type(e).__name__}: {e} ===", flush=True)
        traceback.print_exc()
        return None


def main():
    # Step 1: RSS / web ingest
    def s1():
        from src.ingest import ingest_all
        return ingest_all()

    # Step 2: X timelines
    def s2():
        from src.social import fetch_all_twitter
        return fetch_all_twitter()

    # Step 3: X mentions
    def s3():
        from src.social import fetch_all_mentions
        return fetch_all_mentions()

    # Step 4: Latvijas Vēstnesis (subprocess — separate script)
    def s4():
        py = Path(".venv/Scripts/python.exe")
        if not py.exists():
            py = Path("python")
        result = subprocess.run(
            [str(py), "scripts/ingest_vestnesis.py"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            timeout=600,
        )
        print("--- vestnesis stdout ---")
        print(result.stdout)
        if result.stderr:
            print("--- vestnesis stderr ---")
            print(result.stderr)
        return {"returncode": result.returncode}

    # Step 5: politician junction backstop. Idempotent — link_politicians_to_documents
    # default branch only scans docs that currently lack any junction row. Catches
    # relay-account tweets (social.py:72 leaves politician_links=[]) and other
    # untracked-author paths where ingest stored the doc without a link.
    def s5():
        from src.matcher import link_politicians_to_documents
        linked = link_politicians_to_documents(days=2)
        return {"docs_newly_linked": len(linked)}

    step("ingest_all (RSS)", s1)
    step("fetch_all_twitter", s2)
    step("fetch_all_mentions", s3)
    step("vestnesis", s4)
    step("link_politicians_to_documents (backstop)", s5)

    print("\n=== ALL DONE ===", flush=True)


if __name__ == "__main__":
    main()
