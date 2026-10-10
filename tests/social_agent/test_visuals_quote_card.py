import os
from pathlib import Path

import pytest

from src.social_agent.visuals import render_quote_card


pytestmark = pytest.mark.skipif(
    os.environ.get("SKIP_PLAYWRIGHT") == "1",
    reason="Playwright not available in this environment",
)


def test_render_quote_card_produces_png(tmp_path):
    out = tmp_path / "card.png"
    result = render_quote_card(
        {
            "politician_name": "Arturs Kariņš",
            "topic": "budžets",
            "old_quote": "Nekad neatbalstīšu nodokļu celšanu",
            "old_date": "2026-03-01",
            "new_quote": "Šis budžets ir vienīgais risinājums",
            "new_date": "2026-04-15",
        },
        out_path=out,
    )
    assert result == out
    assert out.exists()
    assert out.stat().st_size > 5000
