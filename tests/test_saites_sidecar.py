"""P1 site-perf: externalize the saites.html claims+votes payload to a sidecar.

saites.html inlined two large blobs — claimsByPid (~1 MB) and votesPayload
(~10 MB raw) — consumed only by the force-graph detail panel on node/link click.
`_emit_saites_json` writes them to data/saites-data.json (+ .br/.gz, served by
the same htaccess *.json rewrite as balsojumi-matrica.json); the page lazy-loads
them on first detail open. Keeps tensionsData + contrasByPid inline (graph paint
+ small).
"""

from __future__ import annotations

import json


def test_emit_saites_json_writes_payload_and_compressed_variants(tmp_path):
    from src.render.links import _emit_saites_json

    atmina = tmp_path / "atmina"
    atmina.mkdir()
    payload = {
        "claimsByPid": {"5": [{"topic": "NATO", "stance": "Par", "date": "2026-05-01"}]},
        "votes": {
            "meta": [{"id": 1, "motif": "Likumprojekts", "date": "2026-05-01"}],
            "byPid": {"5": [[0, "Par"]]},
        },
    }

    dest = _emit_saites_json(payload, atmina)

    assert dest == atmina / "data" / "saites-data.json"
    assert dest.exists()
    loaded = json.loads(dest.read_text(encoding="utf-8"))
    assert loaded["claimsByPid"]["5"][0]["topic"] == "NATO"
    assert loaded["votes"]["meta"][0]["id"] == 1
    assert loaded["votes"]["byPid"]["5"] == [[0, "Par"]]

    # Pre-compressed siblings for the htaccess *.json .br/.gz rewrite.
    br = atmina / "data" / "saites-data.json.br"
    gz = atmina / "data" / "saites-data.json.gz"
    assert br.exists() and br.stat().st_size > 0
    assert gz.exists() and gz.stat().st_size > 0
    # Diacritics survive (ensure_ascii=False).
    payload2 = {"claimsByPid": {"7": [{"stance": "Atbalsta ūdeņradi"}]}, "votes": {"meta": [], "byPid": {}}}
    dest2 = _emit_saites_json(payload2, atmina)
    assert "ūdeņradi" in dest2.read_text(encoding="utf-8")


def test_emit_saites_json_custom_basename_writes_votes_file(tmp_path):
    """A custom basename writes <basename>.json (+ .br/.gz) — used to split the
    heavy vote ledger into data/saites-votes.json off the common detail path."""
    from src.render.links import _emit_saites_json

    atmina = tmp_path / "atmina"
    atmina.mkdir()
    dest = _emit_saites_json(
        {"meta": [{"id": 1}], "byPid": {"5": [[0, "Par"]]}},
        atmina,
        basename="saites-votes",
    )
    assert dest == atmina / "data" / "saites-votes.json"
    assert dest.exists()
    assert (atmina / "data" / "saites-votes.json.br").exists()
    assert (atmina / "data" / "saites-votes.json.gz").exists()
    loaded = json.loads(dest.read_text(encoding="utf-8"))
    assert loaded["byPid"]["5"] == [[0, "Par"]]
