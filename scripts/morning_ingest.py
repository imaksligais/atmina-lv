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


def step(name: str, fn) -> bool:
    """Palaiž vienu soli. Atgriež True, ja izdevās.

    Izņēmums tiek noķerts ar nolūku — viena soļa kļūme nedrīkst apēst pārējos,
    jo ingests ir daļēji atgūstams. Bet kļūme JĀPADOD tālāk kā izejas kods:
    šis ir vienīgais rutīnas solis, kas iet bez uzraudzības, tāpēc izejas kods
    ir vienīgais signāls, kas eksistē (sk. `main()`).
    """
    print(f"\n=== [{name}] start ===", flush=True)
    t0 = time.time()
    try:
        fn()
    except Exception as e:
        dt = time.time() - t0
        print(f"=== [{name}] FAILED after {dt:.1f}s: {type(e).__name__}: {e} ===", flush=True)
        traceback.print_exc()
        return False
    dt = time.time() - t0
    print(f"=== [{name}] OK in {dt:.1f}s ===", flush=True)
    return True


def main() -> int:
    """Palaiž visus piecus soļus. Atgriež 0 tikai tad, ja neviens nav kritis.

    Ne-nulles izejas kods ir vienīgais, ko automatizēts rīta palaidiens redz —
    līdz 2026-08-01 to neviens neatgrieza, tāpēc pilna kļūme bija neatšķirama
    no labas dienas. Neievāktais tajā dienā vairs neatgriežas ekstrakcijas
    rindā (`get_pending_politicians(days=1)`), tāpēc kļūme jāredz TAJĀ dienā.
    """
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
        # Apakšprocess nemet izņēmumu — bez šī pārbaudījuma kritušais Vēstnesis
        # atgriežas kā parasts dict un solis nodrukā OK.
        if result.returncode != 0:
            raise RuntimeError(f"ingest_vestnesis.py iziet ar kodu {result.returncode}")
        return {"returncode": result.returncode}

    # Step 5: politician junction backstop. Idempotent — link_politicians_to_documents
    # default branch only scans docs that currently lack any junction row. Catches
    # relay-account tweets (social.py:72 leaves politician_links=[]) and other
    # untracked-author paths where ingest stored the doc without a link.
    def s5():
        from src.matcher import link_politicians_to_documents
        linked = link_politicians_to_documents(days=2)
        return {"docs_newly_linked": len(linked)}

    steps = [
        ("ingest_all (RSS)", s1),
        ("fetch_all_twitter", s2),
        ("fetch_all_mentions", s3),
        ("vestnesis", s4),
        ("link_politicians_to_documents (backstop)", s5),
    ]

    failed = [name for name, fn in steps if not step(name, fn)]

    # One authoritative row per run, success OR failure. Without it the only
    # signal was the exit code, which nothing persists: a chain that stopped
    # after step 2 left NO trace anywhere (no success row, no failure row), so
    # the day read as "there were no mentions today" rather than "step 3 never
    # ran" — measured on 2026-07-22, 07-28 and 07-31. It is also what
    # src.routine._check_ingest reads to answer "did the ingest run", a
    # question the old document count could not answer.
    try:
        from src.db import log_action

        log_action(
            "morning_ingest",
            status="success" if not failed else "error",
            details={
                "steps_total": len(steps),
                "steps_ok": len(steps) - len(failed),
                "failed": failed,
            },
            error_message=", ".join(failed) or None,
        )
    except Exception as e:  # noqa: BLE001 — telemetry must never mask the run
        print(f"WARN: morning_ingest kopsavilkumu neizdevās ierakstīt: {e}",
              file=sys.stderr, flush=True)

    print(f"\n=== KOPSAVILKUMS: {len(steps) - len(failed)}/{len(steps)} soļi OK ===",
          flush=True)
    if failed:
        print("=== NEIZDEVĀS: " + ", ".join(failed) + " ===", flush=True)
        print("=== INGESTS NEPILNĪGS — izejas kods 1 ===", flush=True)
        return 1

    print("=== ALL DONE ===", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
