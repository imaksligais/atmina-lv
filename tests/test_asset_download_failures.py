"""CDN asset downloads must fail LOUD, not write silent stubs.

BACKLOG § Mazie koda parādi (b): `_download_chart_js()` wrote a
non-functional stub when the CDN was unreachable. Under additive deploy that
stub ships and stays broken on the live site with no reclaim path and no
detector — the same silent-success class as `save_analysis` drops. A render
that cannot fetch its assets must stop, not degrade quietly.
"""

import pytest

from src.render import _common


class _Boom(Exception):
    pass


@pytest.fixture
def _cdn_down(monkeypatch):
    import httpx

    def _raise(*a, **k):
        raise _Boom("CDN unreachable")

    monkeypatch.setattr(httpx, "get", _raise)


def test_chart_js_download_failure_raises_and_writes_nothing(tmp_path, _cdn_down):
    dest = tmp_path / "chart.min.js"
    with pytest.raises(RuntimeError, match="chart"):
        _common._download_chart_js(dest)
    assert not dest.exists(), "a stub on disk IS the silent failure"


def test_annotation_plugin_download_failure_raises_and_writes_nothing(
    tmp_path, _cdn_down
):
    dest = tmp_path / "chartjs-plugin-annotation.min.js"
    with pytest.raises(RuntimeError, match="annotation"):
        _common._download_annotation_plugin(dest)
    assert not dest.exists()
