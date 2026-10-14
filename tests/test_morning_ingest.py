"""`scripts/morning_ingest.py` izejas kods ir vienīgais signāls, kas eksistē.

Rīta ingests ir vienīgais rutīnas solis, kas iet bez uzraudzības — neviens
neskatās tā konsolē. Līdz 2026-08-01 `step()` noķēra katru izņēmumu un `main()`
neatgrieza neko, tāpēc pilna piecu soļu kļūme izgāja ar kodu 0 un izdrukāja
„ALL DONE": tieši tā „klusās veiksmes" klase, ko CLAUDE.md sauc par šī projekta
defektu #1. Zaudējums nav atgūstams — `get_pending_politicians(days=1)` nozīmē,
ka tajā dienā neievāktais nekad neatgriežas ekstrakcijas rindā.

Tāpēc katrs tests šeit apgalvo, ka konkrēta kļūmes forma TIEK padota tālāk kā
ne-nulles izejas kods, nevis tikai to, ka labs skrējiens iziet ar nulli.
"""

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "morning_ingest.py"

_spec = importlib.util.spec_from_file_location("morning_ingest", SCRIPT)
morning_ingest = importlib.util.module_from_spec(_spec)
sys.modules["morning_ingest"] = morning_ingest
_spec.loader.exec_module(morning_ingest)


def _boom(*_args, **_kwargs):
    raise RuntimeError("upstream nokrita")


class _FakeCompleted:
    def __init__(self, returncode: int):
        self.returncode = returncode
        self.stdout = "vestnesis izvade"
        self.stderr = ""


@pytest.fixture
def all_steps_ok(monkeypatch):
    """Visi pieci soļi izdodas; testi pēc tam salauž tieši vienu."""

    class _Calls(list):
        """list + a `logged` slot for the summary rows main() would have written."""
        logged: list

    calls = _Calls()

    def _rec(name, result=None):
        def _fn(*_a, **_kw):
            calls.append(name)
            return result
        return _fn

    monkeypatch.setattr("src.ingest.ingest_all", _rec("s1", {}), raising=True)
    monkeypatch.setattr("src.social.fetch_all_twitter", _rec("s2", {}), raising=True)
    monkeypatch.setattr("src.social.fetch_all_mentions", _rec("s3", {}), raising=True)
    monkeypatch.setattr(
        "src.matcher.link_politicians_to_documents", _rec("s5", []), raising=True
    )

    def _fake_run(*_a, **_kw):
        calls.append("s4")
        return _FakeCompleted(0)

    monkeypatch.setattr(subprocess, "run", _fake_run)

    return calls



@pytest.fixture(autouse=True)
def summary_rows(monkeypatch):
    """main() writes one `morning_ingest` summary row — stub it, ALWAYS.

    `log_action()` takes no db_path here, so it hits the LIVE data/atmina.db.
    main() is a production entry point: a test that calls it for real performs
    every side effect it has. Leaving this unstubbed put 18 rows into the real
    `logs` table on 2026-08-02, and the routine reporter began reading that
    table the same afternoon, so it showed a failed ingest that never happened.

    Autouse rather than part of `all_steps_ok`, because two tests in this file
    drive main() without that fixture — which is exactly how the gap survived
    being noticed once. tests/conftest.py carries the general tripwire.
    """
    rows: list[dict] = []
    monkeypatch.setattr(
        "src.db.log_action",
        lambda action, **kw: rows.append({"action": action, **kw}),
        raising=True,
    )
    return rows


def test_clean_run_exits_zero(all_steps_ok, capsys, summary_rows):
    assert morning_ingest.main() == 0
    assert all_steps_ok == ["s1", "s2", "s3", "s4", "s5"]
    assert "ALL DONE" in capsys.readouterr().out
    assert [r["action"] for r in summary_rows] == ["morning_ingest"]
    assert summary_rows[0]["status"] == "success"
    assert summary_rows[0]["details"]["failed"] == []


def test_single_failed_step_exits_nonzero(all_steps_ok, monkeypatch):
    """Regresija: līdz 2026-08-01 šis atgrieza None, un `sys.exit(None)` ir 0."""
    monkeypatch.setattr("src.social.fetch_all_twitter", _boom, raising=True)
    assert morning_ingest.main() == 1


def test_every_step_failed_exits_nonzero(monkeypatch):
    monkeypatch.setattr("src.ingest.ingest_all", _boom, raising=True)
    monkeypatch.setattr("src.social.fetch_all_twitter", _boom, raising=True)
    monkeypatch.setattr("src.social.fetch_all_mentions", _boom, raising=True)
    monkeypatch.setattr("src.matcher.link_politicians_to_documents", _boom, raising=True)
    monkeypatch.setattr(subprocess, "run", _boom)
    assert morning_ingest.main() == 1


def test_failed_step_does_not_abort_the_rest(all_steps_ok, monkeypatch):
    """Kļūme 1. solī nedrīkst apēst pārējos četrus — ingests ir daļēji atgūstams."""
    monkeypatch.setattr("src.ingest.ingest_all", _boom, raising=True)
    assert morning_ingest.main() == 1
    assert all_steps_ok == ["s2", "s3", "s4", "s5"]


def test_vestnesis_nonzero_returncode_is_a_failure(all_steps_ok, monkeypatch):
    """Apakšprocess nemet izņēmumu — kļūme atnāk TIKAI kā returncode."""
    monkeypatch.setattr(subprocess, "run", lambda *_a, **_kw: _FakeCompleted(2))
    assert morning_ingest.main() == 1


def test_summary_names_the_failed_steps(all_steps_ok, monkeypatch, capsys):
    monkeypatch.setattr("src.social.fetch_all_mentions", _boom, raising=True)
    morning_ingest.main()
    out = capsys.readouterr().out
    assert "4/5" in out, "kopsavilkumam jānosauc, cik soļu izdevās"
    assert "fetch_all_mentions" in out, "kopsavilkumam jānosauc kritušo soli"
    assert "ALL DONE" not in out, "ALL DONE pēc kļūmes ir tieši tā viltus zaļā gaisma"


def test_failure_is_written_to_the_log_not_only_printed(all_steps_ok, monkeypatch,
                                                        summary_rows):
    """Apstāšanās pa vidu līdz šim neatstāja NEKĀDU pēdu — ne veiksmes, ne kļūmes
    rindu —, tāpēc diena lasījās kā „šodien pieminējumu nebija" (07-22, 07-28,
    07-31). Izejas kodu neviens nesaglabā; šī rinda ir vienīgais, kas paliek."""
    monkeypatch.setattr("src.social.fetch_all_mentions", _boom, raising=True)
    morning_ingest.main()
    assert len(summary_rows) == 1, summary_rows
    row = summary_rows[0]
    assert row["status"] == "error"
    assert row["details"]["failed"] == ["fetch_all_mentions"]
    assert row["details"]["steps_ok"] == 4


def test_entrypoint_propagates_the_exit_code():
    """`main()` atgriež kodu tikai tad, ja `__main__` to tiešām padod tālāk."""
    src = SCRIPT.read_text(encoding="utf-8")
    assert "sys.exit(main())" in src, (
        "bez sys.exit(main()) izejas kods paliek 0 neatkarīgi no tā, ko main() atgriež"
    )
