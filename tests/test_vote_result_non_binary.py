"""`saeima_votes.result` vārdnīca nav binārā — UI lasītāji to nedrīkst pieņemt.

Konteksts: korpusā līdz 2026-08-18 `result` bija {`Pieņemts`, `Noraidīts`, NULL}.
Operatora verdikts 2026-08-18 (BACKLOG § Saeima) paplašināja vārdnīcu ar burtisko
avota etiķeti `Nod. kom.` (nodots komisijām; rindas 1435, 905, 956, 6192) —
apzināti NEkartējot to uz `Pieņemts`.

Abas publiskās virsmas, kas rāda `result`, līdz tam bija binārs if/else, kur
"viss, kas nav Pieņemts" krita uz `badge-red`. Sarkana nozīmīte uz `Nod. kom.`
apgalvotu noraidījumu, kāda nav — tas ir tieši tā klase, kas jau vienreiz
uzrakstīja "None" sarkanā (labots 2026-08-17). Šie testi piesien trešo zaru.

Virsmas: `templates/index.html.j2` (SSR jaunāko balsojumu tabula) — šeit; un
`assets/bmv1.js` saraksta kartītes iznākums (`resultDotClass()`) — izpildīts
node vidē `tests/test_balsojumi_readability.py::test_unknown_result_never_renders_a_red_badge`.
Agrākais `resultBadgeClass()` grep tests (Matricas detaļu panelis) izņemts
2026-10-16 kopā ar Matricu; aizstājēja pārklājums pierādīts ar mutāciju
(`resultDotClass` neitrālais zars → "is-fail" → readability tests krīt).
"""

from pathlib import Path

import pytest
from jinja2 import Environment

_INDEX = Path("templates/index.html.j2")


def _result_cell_source() -> str:
    """Izvelk īsto `result` <td> no index.html.j2 — testam jālasa tas, ko raksta."""
    for line in _INDEX.read_text(encoding="utf-8").splitlines():
        if "v.result" in line and "badge-green" in line:
            return line.strip()
    pytest.fail("index.html.j2 vairs nesatur v.result nozīmītes rindu — vai virsma pārcelta?")


def _render_cell(result_value):
    env = Environment(autoescape=True)
    return env.from_string(_result_cell_source()).render(v={"result": result_value})


def test_pienemts_is_green():
    html = _render_cell("Pieņemts")
    assert "badge-green" in html
    assert "Pieņemts" in html


def test_noraidits_is_red():
    html = _render_cell("Noraidīts")
    assert "badge-red" in html


def test_nod_kom_renders_literally_and_neutrally():
    html = _render_cell("Nod. kom.")
    assert "Nod. kom." in html, "etiķeti rāda burtiski, ne pārtulkotu"
    assert "badge-muted" in html
    assert "badge-red" not in html, "nezināma etiķete nav noraidījums"
    assert "badge-green" not in html


def test_null_result_stays_muted_dash():
    html = _render_cell(None)
    assert "badge-muted" in html
    assert "badge-red" not in html
