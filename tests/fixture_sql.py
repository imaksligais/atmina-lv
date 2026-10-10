"""Loader for the committed render characterization fixture.

The fixture is a data-only SQL dump built by ``scripts/build_render_fixture.py``
from a fixed subset of the live DB. At 4 091 508 bytes it was 87 % of the whole
``tests/fixtures/`` tree, so since 2026-09-05 it is stored gzipped
(``render_fixture_data.sql.gz``, 837 037 bytes — 20.5 % of the original) and
decompressed in memory here. The DECOMPRESSED text is byte-identical to the
file that was committed before; ``tests/test_render_fixture_gzip.py`` pins its
SHA-256 so a re-gzip cannot silently change fixture content, which would force
a regeneration of the 147 render baselines.

Why gzip rather than "regenerate smaller": BACKLOG.md § Ne-darīt and
``docs/audits/2026-08-22-slop-un-bloat-audits.md`` both name shrinking this
fixture as explicitly NOT-to-do — a smaller fixture is different input, and
different input means every baseline SHA has to be rebuilt. Compression keeps
the input identical.

Precedence: a plain ``.sql`` next to the ``.sql.gz`` WINS. That is deliberate —
``scripts/build_render_fixture.py`` still writes the plain file, so a coverage
re-generation is picked up immediately without anyone having to remember this
module. After such a regeneration, re-gzip and delete the plain file:

    .venv/Scripts/python.exe -c "import gzip,pathlib; p=pathlib.Path('tests/fixtures/render_fixture_data.sql'); pathlib.Path(str(p)+'.gz').write_bytes(gzip.compress(p.read_bytes(),9,mtime=0)); p.unlink()"

and update ``EXPECTED_SHA256`` in ``tests/test_render_fixture_gzip.py``.
"""

from __future__ import annotations

import gzip
from pathlib import Path

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
RENDER_FIXTURE_SQL = FIXTURES_DIR / "render_fixture_data.sql"
RENDER_FIXTURE_SQL_GZ = FIXTURES_DIR / "render_fixture_data.sql.gz"


def load_render_fixture_sql() -> str:
    """Return the render fixture SQL as text (plain file wins over .gz)."""
    if RENDER_FIXTURE_SQL.exists():
        return RENDER_FIXTURE_SQL.read_text(encoding="utf-8")
    if RENDER_FIXTURE_SQL_GZ.exists():
        with gzip.open(RENDER_FIXTURE_SQL_GZ, "rt", encoding="utf-8") as fh:
            return fh.read()
    raise FileNotFoundError(
        f"Neviens no fikstūras failiem neeksistē: {RENDER_FIXTURE_SQL} "
        f"vai {RENDER_FIXTURE_SQL_GZ}. Pārbūvē ar scripts/build_render_fixture.py."
    )
