"""Vārti gzipētajai render fikstūrai (plāna 6.3, 2026-09-05).

``tests/fixtures/render_fixture_data.sql`` bija 4 091 508 baiti — 87 % no visas
``tests/fixtures/`` koka (4,6 MB). Kopš 2026-09-05 tas glabājas kā
``render_fixture_data.sql.gz`` (837 037 baiti, 20,5 %) un tiek atspiests atmiņā
ar ``tests/fixture_sql.py::load_render_fixture_sql``.

**Kāpēc gzip, nevis mazāka fikstūra:** ``BACKLOG.md`` § Ne-darīt un
``docs/audits/2026-08-22-slop-un-bloat-audits.md`` abi nosauc šīs fikstūras
griešanu kā tiešu NEdarīt — mazāka fikstūra ir CITS ievads, un cits ievads
nozīmē 147 render baseline SHA pārbūvi. Kompresija satur to pašu ievadu.

Šis fails ir tie vārti, kas to pierāda: SHA-256 pār ATSPIESTO tekstu. Ja kāds
pārģenerē fikstūru un pārgzipē, šis tests krīt, nevis klusi maina 3 patērētāju
ievadu. Saucējs: 3 patērētāji (``test_render_chars.py``, ``test_rankings.py``,
``test_topics.py``) — tests to pārbauda, nevis pieņem.

Mutācijas pārbaude (kā pārliecināties, ka vārti tiešām krīt): nomaini vienu
baitu ``EXPECTED_SHA256`` — abi pirmie testi kļūst sarkani.
"""

from __future__ import annotations

import gzip
import hashlib
import re
from pathlib import Path

import pytest

from tests.fixture_sql import (
    RENDER_FIXTURE_SQL,
    RENDER_FIXTURE_SQL_GZ,
    load_render_fixture_sql,
)

# Divi slāņi, abi pieķerti:
#  (a) FAILS — sha256 pār atspiestajiem baitiem = tieši tie 4 091 508 baiti, kas
#      bija komitēti kā render_fixture_data.sql (CRLF, jo build_render_fixture.py
#      lieto Path.write_text uz Windows).
#  (b) TEKSTS — ko `executescript()` tiešām saņem. Gan vecais
#      `read_text(encoding="utf-8")`, gan jaunais `gzip.open(..., "rt")` lieto
#      universālās jaunrindas, tāpēc 22 716 CRLF pāri pārtop par LF un teksts ir
#      4 068 792 baiti. Abi ceļi dod IDENTISKU virkni — tas ir šī soļa
#      "byte-equivalent in effect" apgalvojums, un tas te ir mērīts, ne pieņemts.
EXPECTED_SHA256 = "8357923883d6e9d192ac5f4b88101b575538979cb1074b893d07201a9c6e92ae"
EXPECTED_BYTES = 4_091_508
EXPECTED_TEXT_SHA256 = "e5b6a0d4b31c5becb63e3947100e56713f21f5427310e263e6437ebe34db7fb0"
EXPECTED_TEXT_BYTES = 4_068_792
EXPECTED_CRLF_PAIRS = 22_716

TESTS_DIR = Path(__file__).resolve().parent
# Every test module that loads the render fixture. A shrinking denominator here
# means a consumer was renamed or dropped — that is a finding, not a pass.
EXPECTED_CONSUMERS = {
    "test_render_chars.py",
    "test_rankings.py",
    "test_topics.py",
}


def test_gzip_decompresses_to_the_committed_bytes():
    """(a) Fails: atspiestie baiti == vecais komitētais .sql, baitu pa baitam."""
    raw = gzip.decompress(RENDER_FIXTURE_SQL_GZ.read_bytes())
    assert len(raw) == EXPECTED_BYTES, (
        f"fikstūras izmērs mainījies: {len(raw)} != {EXPECTED_BYTES}. "
        "Ja tas ir apzināti, jāpārbūvē arī 147 render baseline SHA."
    )
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_SHA256
    assert raw.count(b"\r\n") == EXPECTED_CRLF_PAIRS


def test_loader_text_matches_the_old_read_text_path():
    """(b) Teksts: ko saņem executescript() — identisks vecajam read_text()."""
    text = load_render_fixture_sql()
    raw = gzip.decompress(RENDER_FIXTURE_SQL_GZ.read_bytes())
    # Tieši tas, ko `Path.read_text(encoding="utf-8")` darīja ar CRLF failu.
    assert text == raw.decode("utf-8").replace("\r\n", "\n")
    assert "\r\n" not in text
    enc = text.encode("utf-8")
    assert len(enc) == EXPECTED_TEXT_BYTES
    assert hashlib.sha256(enc).hexdigest() == EXPECTED_TEXT_SHA256


def test_compressed_form_is_the_one_on_disk():
    """Repo nes .gz, ne 4 MB plaintekstu (tas ir viss šī soļa ieguvums)."""
    assert RENDER_FIXTURE_SQL_GZ.exists(), (
        f"{RENDER_FIXTURE_SQL_GZ} trūkst. Uzmanību: .gitignore:125 ignorē *.gz — "
        "negācijai `!tests/fixtures/*.sql.gz` jāpaliek, citādi svaigs klons "
        "šo failu nesaņem un 3 testu faili krīt ar FileNotFoundError."
    )
    assert RENDER_FIXTURE_SQL_GZ.stat().st_size < EXPECTED_BYTES // 2
    if RENDER_FIXTURE_SQL.exists():
        pytest.fail(
            "Plaintext .sql atgriezies blakus .gz — build_render_fixture.py to "
            "raksta pārģenerējot. Pārgzipē un izdzēs plaintekstu (recepte: "
            "tests/fixture_sql.py docstring), tad atjauno EXPECTED_SHA256."
        )


def test_every_consumer_goes_through_the_loader():
    """Saucējs: 3 patērētāji; neviens nelasa .sql ceļu tieši.

    Bez šī vārta viens palicis ``read_text(...render_fixture_data.sql)`` klusi
    krastu tikai tajā vienā failā, un tikai svaigā klonā.
    """
    found: set[str] = set()
    direct_readers: list[str] = []
    for path in sorted(TESTS_DIR.glob("test_*.py")):
        text = path.read_text(encoding="utf-8")
        if "render_fixture_data" not in text and "load_render_fixture_sql" not in text:
            continue
        if path.name == Path(__file__).name:
            continue
        found.add(path.name)
        if re.search(r'render_fixture_data\.sql["\']', text):
            direct_readers.append(path.name)
    assert not direct_readers, (
        "Šie faili joprojām lasa plaintext .sql ceļu: " + ", ".join(direct_readers)
    )
    assert found == EXPECTED_CONSUMERS, (
        f"patērētāju kopa mainījusies: {sorted(found)} != {sorted(EXPECTED_CONSUMERS)}"
    )
