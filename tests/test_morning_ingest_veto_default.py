"""`scripts/morning_ingest.py` noklusējums TypeSafe matcher veto = ēnas režīms.

Operatora lēmums 2026-09-19: ēnas nedēļai vajag 7 SECĪGAS dienas, un mainīgais,
ko ar roku dod katrā rutīnā (`ATMINA_TYPESAFE_VETO=shadow` pirms
`morning_ingest.py`), ir trausls — viena aizmirsta diena atmet skaitīšanu uz
sākumu. Tāpēc skripts pats izpilda `os.environ.setdefault(..., "shadow")`
PIRMS pirmā `src.*` importa (`src/matcher.py` mainīgo nolasa importa brīdī
moduļa līmenī).

Trīs noteikumi, katrs savs tests:
  (a) tīrā vidē (mainīgā nav) pēc skripta ielādes vide nes "shadow";
  (b) iepriekš uzstādīts `enforce` paliek — setdefault nepārraksta (vides
      mainīgais pārspēj noklusējumu, tāpēc `off`/`enforce` joprojām dodams);
  (c) pārējā svīta joprojām strādā ar `off` — `tests/conftest.py` piesprauž to
      pirms jebkura src importa, un `src.matcher.TYPESAFE_VETO_MODE` to rāda.

Skriptu NEpalaiž ar subprocess (tas sāktu īsto ingestu); `runpy.run_path` ar
`run_name != "__main__"` izpilda tikai moduļa līmeni (importi, reconfigure,
setdefault, def-i), ne `main()`. Vidi maina tikai caur `monkeypatch`, lai
svīta nepiesārņojas.

Mutācijas pārbaude (2026-09-19): ar izdzēstu `setdefault` rindu (a) krīt ar
KeyError — vārti ir redzēti sarkani.
"""
from __future__ import annotations

import os
import runpy
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "morning_ingest.py"
VAR = "ATMINA_TYPESAFE_VETO"


def _load_script_module_level() -> None:
    # run_name, kas nav "__main__", tāpēc `if __name__ == "__main__": main()`
    # neizpildās un neviens ingesta solis nesākas.
    runpy.run_path(str(SCRIPT), run_name="not_main")


def test_clean_env_defaults_to_shadow(monkeypatch):
    monkeypatch.delenv(VAR, raising=False)
    assert VAR not in os.environ, "priekšnosacījums: mainīgais izdzēsts"
    _load_script_module_level()
    assert os.environ[VAR] == "shadow", (
        f"scripts/morning_ingest.py noklusējumam jābūt shadow, ir {os.environ.get(VAR)!r}"
    )


def test_preset_value_is_not_overwritten(monkeypatch):
    monkeypatch.setenv(VAR, "enforce")
    _load_script_module_level()
    assert os.environ[VAR] == "enforce", "setdefault nedrīkst pārrakstīt vides mainīgo"


def test_suite_still_runs_with_veto_off():
    # tests/conftest.py piesprauž "off" pirms jebkura src importa; ja kāds
    # tests ielādē skriptu, setdefault to nepārraksta (b), tāpēc matcher
    # svītā paliek deterministisks un maksas API netiek saukts.
    import src.matcher as matcher_mod

    assert os.environ.get(VAR) == "off"
    assert matcher_mod.TYPESAFE_VETO_MODE == "off"
