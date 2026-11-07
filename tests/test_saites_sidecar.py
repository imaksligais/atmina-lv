"""P1 site-perf: externalize the saites.html claims+votes payload to a sidecar.

saites.html inlined two large blobs — claimsByPid (~1 MB) and votesPayload
(~10 MB raw) — consumed only by the force-graph detail panel on node/link click.
`_emit_saites_json` writes them to data/saites-data.json; the page lazy-loads
them on first detail open. Keeps tensionsData + contrasByPid inline (graph paint
+ small).
"""

from __future__ import annotations

import json


def test_emit_saites_json_writes_payload(tmp_path):
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

    # Diacritics survive (ensure_ascii=False).
    payload2 = {"claimsByPid": {"7": [{"stance": "Atbalsta ūdeņradi"}]}, "votes": {"meta": [], "byPid": {}}}
    dest2 = _emit_saites_json(payload2, atmina)
    assert "ūdeņradi" in dest2.read_text(encoding="utf-8")


def test_emit_saites_json_custom_basename_writes_votes_file(tmp_path):
    """A custom basename writes <basename>.json — used to split the
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
    loaded = json.loads(dest.read_text(encoding="utf-8"))
    assert loaded["byPid"]["5"] == [[0, "Par"]]


def test_render_links_votes_ledger_omits_presence_registrations(tmp_path, monkeypatch):
    """Kļūme: saites.html «Balsojumi» sadaļa veidoja `balsojumi.html#vote-N` saiti
    katram saites-votes.json ierakstam, arī klātbūtnes reģistrācijai
    (Reģistrējies/Nereģistrējies, 566 mērķi 2026-10-16). Balsojumu saraksts
    klātbūtni apzināti nerāda (src/render/votes.py), tāpēc lasītājs nonāca pie
    «Balsojums nav atrasts arhīvā.». Ledgerī drīkst būt tikai tie balsojumi,
    ko rāda arhīvs — tad katra saite ved uz esošu kartīti."""
    import os
    import tempfile

    import src.render.links as links_mod
    from src.db import get_db, init_db
    from src.saeima.schema import init_saeima_bills, init_saeima_tables

    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    init_saeima_tables(path)
    init_saeima_bills(path)
    db = get_db(path)
    db.executescript("""
        INSERT INTO tracked_politicians (id, name, party, role, relationship_type)
            VALUES (1, 'Testa Deputāts', 'Jaunā Vienotība', 'Saeimas deputāts', 'tracked');
        INSERT INTO saeima_votes (id, motif, vote_date, vote_time, url) VALUES
            (10, 'Grozījumi Valsts valodas likumā', '2026-09-10', '10:00:00', 'u10'),
            (11, 'Deputātu klātbūtnes reģistrācija', '2026-09-10', '09:00:00', 'u11'),
            (12, 'Kvoruma pārbaude', '2026-09-10', '11:00:00', 'u12'),
            (13, 'Civilstāvokļa aktu reģistrācijas likums', '2026-09-10', '12:00:00', 'u13');
        INSERT INTO saeima_individual_votes (vote_id, deputy_name, vote, politician_id) VALUES
            (10, 'Testa Deputāts', 'Par', 1),
            (11, 'Testa Deputāts', 'Reģistrējies', 1),
            (12, 'Testa Deputāts', 'Nereģistrējies', 1),
            (13, 'Testa Deputāts', 'Pret', 1);
    """)
    db.commit()

    captured: dict = {}
    monkeypatch.setattr(
        links_mod, "_render_page", lambda env, tpl, out, ctx: captured.update(ctx)
    )
    try:
        links_mod.render_links(env=None, db=db, atmina_dir=tmp_path, tensions=[])
    finally:
        db.close()

    ledger = json.loads((tmp_path / "data" / "saites-votes.json").read_text(encoding="utf-8"))
    linked_ids = {ledger["meta"][i]["id"] for i, _ in ledger["byPid"]["1"]}
    assert linked_ids == {10, 13}  # prefiksa filtrs, ne '%reģistrācij%'
    assert {m["id"] for m in ledger["meta"]} == {10, 13}
    sidecar = json.loads((tmp_path / "data" / "saites-data.json").read_text(encoding="utf-8"))
    assert sidecar["votesCount"]["1"] == 2
