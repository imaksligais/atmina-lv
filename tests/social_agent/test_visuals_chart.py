import os
import tempfile
from pathlib import Path

import pytest

pytest.importorskip("matplotlib")  # render_chart needs matplotlib; skip cleanly if absent

from src.social_agent.visuals import render_chart  # noqa: E402


def test_render_chart_produces_png(tmp_path):
    out = tmp_path / "chart.png"
    result = render_chart(
        {
            "leaderboard": [
                {"name": "A", "count": 5},
                {"name": "B", "count": 3},
                {"name": "C", "count": 1},
            ]
        },
        out_path=out,
    )
    assert result == out
    assert out.exists()
    assert out.stat().st_size > 1000  # non-trivial PNG


def test_render_chart_rejects_empty_leaderboard(tmp_path):
    import pytest
    with pytest.raises(ValueError):
        render_chart({"leaderboard": []}, out_path=tmp_path / "x.png")
