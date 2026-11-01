import textwrap

from src.outlets import OUTLET_FACT_FIELDS, host_to_outlet, load_outlets


def _write_yaml(tmp_path):
    p = tmp_path / "sources.yaml"
    p.write_text(textwrap.dedent("""
        sources:
          - url: "https://www.lsm.lv/rss/?lang=lv&catid=20"
            name: "LSM.lv Latvija"
            outlet: lsm
          - url: "https://www.lsm.lv/rss/?lang=lv&catid=22"
            name: "LSM.lv Ekonomika"
            outlet: lsm
          - url: "https://www.instagram.com"
            name: "Instagram"
        outlets:
          - short_name: lsm
            name: "LSM"
            type: public_tv
            language: lv
            hosts: ["www.lsm.lv", "lsm.lv"]
            website: "https://www.lsm.lv"
            x_feeds: ["ltvzinas", "@ltvpanorama", ""]
            description: "Public broadcaster."
            volume_label: "dokumenti"
            facts:
              - field: owner
                value: "Valsts"
                source_url: "https://example.org/lsm-owner"
                as_of: "2026-06-01"
              - field: funding_model
                value: "Valsts budžets"
                source_url: ""
                as_of: "2026-06-01"
          - short_name: nra
            name: "Neatkarīgā"
            type: print
            language: lv
            hosts: ["nra.lv"]
            facts: []
          - short_name: mystery
            name: "Nezināmais"
            type: podcast
            language: lv
            hosts: ["mystery.lv"]
            facts: []
          - short_name: notype
            name: "Bez tipa"
            language: lv
            hosts: ["notype.lv"]
            facts: []
    """), encoding="utf-8")
    return p


def test_load_outlets_groups_feeds_and_normalizes_hosts(tmp_path):
    outlets = load_outlets(_write_yaml(tmp_path))
    by = {o["short_name"]: o for o in outlets}
    assert set(by) == {"lsm", "nra", "mystery", "notype"}
    # hosts normalized (www. stripped) + de-duplicated to one
    assert by["lsm"]["hosts"] == ["lsm.lv"]
    # feed urls grouped under the outlet
    assert len(by["lsm"]["feed_urls"]) == 2
    # slug derived
    assert by["lsm"]["slug"] == "lsm"


def test_load_outlets_drops_unsourced_facts(tmp_path):
    by = {o["short_name"]: o for o in load_outlets(_write_yaml(tmp_path))}
    fields = [f["field"] for f in by["lsm"]["facts"]]
    # owner has a source_url -> kept; funding_model has empty source_url -> dropped
    assert fields == ["owner"]
    assert all(f["field"] in OUTLET_FACT_FIELDS for f in by["lsm"]["facts"])


def test_host_to_outlet_map(tmp_path):
    outlets = load_outlets(_write_yaml(tmp_path))
    m = host_to_outlet(outlets)
    assert m["lsm.lv"] == "lsm"
    assert m["nra.lv"] == "nra"


def test_load_outlets_exposes_x_feeds(tmp_path):
    by = {o["short_name"]: o for o in load_outlets(_write_yaml(tmp_path))}
    # '@' nostrippots, tukšais izmests, secība saglabāta
    assert by["lsm"]["x_feeds"] == ["ltvzinas", "ltvpanorama"]
    # outlets bez x_feeds -> tukšs saraksts (ne KeyError)
    assert by["nra"]["x_feeds"] == []


def test_load_outlets_type_label(tmp_path):
    by = {o["short_name"]: o for o in load_outlets(_write_yaml(tmp_path))}
    # known codes -> LV public labels
    assert by["lsm"]["type_label"] == "sabiedriskais medijs"   # public_tv
    assert by["nra"]["type_label"] == "drukātā prese"          # print
    # unknown type -> passthrough of the raw code
    assert by["mystery"]["type_label"] == "podcast"
    # missing type -> empty string (never None)
    assert by["notype"]["type_label"] == ""


def test_load_outlets_volume_label(tmp_path):
    by = {o["short_name"]: o for o in load_outlets(_write_yaml(tmp_path))}
    # set value passes through ...
    assert by["lsm"]["volume_label"] == "dokumenti"
    # ... default is "raksti" when absent
    assert by["nra"]["volume_label"] == "raksti"
