"""Nogrieztais ievads — the flag-don't-drop gate (verdikts 40, 2026-09-06).

Some publishers' article bodies arrive with the opening paragraph missing, so
the stored `content` starts mid-narrative with an anaphoric pronoun: «Viņš
uzsvēra…», «Viņa norādīja…». The referent is in the paragraph that never
arrived. Measured 2026-09-06: 56 of 14 737 `platform='web'` documents, up from
32 on 2026-08-23 — the class grows. Three claims extracted from such documents
were read back against the live article: 0 misattributions, so DROPPING these
documents would throw away good corpus for a risk that has not materialised.

Hence a flag, not a filter. The document is stored exactly as before; the run
counts it, names its doc id in the `logs` row, and reports the count against a
denominator in the ingest journal. Nothing is lost and nothing is silent.
"""

from __future__ import annotations

import asyncio

import pytest


class TestCutLedeDetector:
    """The predicate is deliberately narrow: two prefixes, case-sensitive.

    Widening it to every pronoun would flag legitimate openings («Viņu skaits
    pieauga») and turn a 0.4 % signal into noise. The two forms measured are
    the two that actually occur.
    """

    @pytest.mark.parametrize("text", [
        "Viņš uzsvēra, ka budžeta process nav pabeigts.",
        "Viņa norādīja, ka lēmums vēl nav pieņemts.",
    ])
    def test_flags_anaphoric_opening(self, text):
        from src.ingest_rules import _looks_like_cut_lede
        assert _looks_like_cut_lede(text) is True

    @pytest.mark.parametrize("text", [
        "Ministrs sacīja, ka viņš atbalsta priekšlikumu.",
        "Viņu skaits pieauga par 12 %.",
        "Viņas partija balsoja pret.",
        "Viņi vienojās par termiņu.",
        "viņš teica, ka nepiekrīt.",
        "",
    ])
    def test_does_not_flag_ordinary_openings(self, text):
        from src.ingest_rules import _looks_like_cut_lede
        assert _looks_like_cut_lede(text) is False

    def test_leading_whitespace_does_not_hide_the_cut(self):
        from src.ingest_rules import _looks_like_cut_lede
        assert _looks_like_cut_lede("\n  Viņš uzsvēra, ka…") is True

    def test_none_is_not_a_crash(self):
        from src.ingest_rules import _looks_like_cut_lede
        assert _looks_like_cut_lede(None) is False


def _run_source(monkeypatch, items, platform="web"):
    """Drive `_ingest_source` over `items` with every side effect stubbed."""
    import src.ingest as ing

    stored_docs: list[str] = []
    logged: list[dict] = []

    async def fake_scrape(url, tier, fetcher_mode):  # noqa: ARG001
        return items

    def fake_insert_document(text, **kwargs):  # noqa: ARG001
        stored_docs.append(text)
        return 900 + len(stored_docs)

    monkeypatch.setattr(ing, "scrape_source", fake_scrape)
    monkeypatch.setattr(ing, "validate_content", lambda t, u: (True, "ok"))
    monkeypatch.setattr(ing, "match_politicians", lambda t: [])
    monkeypatch.setattr(ing, "_passes_keyword_filter", lambda t: True)
    monkeypatch.setattr(ing, "_detect_language", lambda t: ("lv", 1.0))
    monkeypatch.setattr(ing, "insert_document", fake_insert_document)
    monkeypatch.setattr(ing, "embed_document", lambda t: [])
    monkeypatch.setattr(ing, "insert_chunks", lambda d, c: None)
    monkeypatch.setattr(ing, "_reset_failures", lambda sid: None)
    monkeypatch.setattr(
        ing, "log_action",
        lambda action, **kw: logged.append({"action": action, **kw}),
    )

    source = {"url": "https://example.lv/rss", "name": "Testa avots",
              "tier": 1, "rate_limit_seconds": 0, "platform": platform}
    result = asyncio.run(ing._ingest_source(source, 7, False, {}))
    return result, stored_docs, logged


class TestCutLedeIsFlaggedNotDropped:

    ITEMS = [
        {"text": "Viņš uzsvēra, ka budžeta process nav pabeigts un ka valdība "
                 "vēl atgriezīsies pie jautājuma nākamajā nedēļā.",
         "url": "https://diena.lv/a/1"},
        {"text": "Ministrs sacīja, ka priekšlikums tiks skatīts komisijā "
                 "jau šonedēļ, un aicināja partnerus to atbalstīt.",
         "url": "https://diena.lv/a/2"},
        {"text": "Viņa norādīja, ka lēmums vēl nav pieņemts un ka process "
                 "turpināsies pēc ekspertu atzinuma saņemšanas.",
         "url": "https://diena.lv/a/3"},
    ]

    def test_every_document_is_still_stored(self, monkeypatch):
        """The gate must not shrink the corpus — 0 misattributions measured."""
        result, stored, _ = _run_source(monkeypatch, self.ITEMS)
        assert len(stored) == 3, stored
        assert result["documents"] == 3

    def test_run_result_carries_the_count_and_its_denominator(self, monkeypatch):
        result, _, _ = _run_source(monkeypatch, self.ITEMS)
        assert result["cut_lede"] == 2, result
        assert result["web_documents"] == 3, result

    def test_log_row_names_the_flagged_doc_ids(self, monkeypatch):
        """Per-document provenance without a schema migration.

        `documents` has no flag column and adding one for a 0.4 % annotation is
        not worth a migration; the `logs` row already carries this run's
        details, is durable, and is queryable by day.
        """
        _, _, logged = _run_source(monkeypatch, self.ITEMS)
        ingest_rows = [r for r in logged if r["action"] == "ingest"]
        assert len(ingest_rows) == 1, logged
        details = ingest_rows[0]["details"]
        assert details["cut_lede"] == 2, details
        assert details["cut_lede_doc_ids"] == [901, 903], details

    def test_non_web_platform_is_not_counted(self, monkeypatch):
        """The denominator is web articles — a tweet legitimately opens with «Viņš»."""
        result, _, _ = _run_source(monkeypatch, self.ITEMS, platform="twitter")
        assert result["web_documents"] == 0, result
        assert result["cut_lede"] == 0, result


class TestIngestJournalReportsTheDenominator:
    """«N no M web dokiem ar nogrieztu ievadu» — never N alone.

    A count with no denominator cannot distinguish a quiet day from a broken
    detector (CLAUDE.md § A gate that cannot fail is not evidence).
    """

    RESULTS = [
        {"source": "Diena.lv", "tier": 1, "documents": 4, "skipped": 0,
         "status": "success", "cut_lede": 2, "web_documents": 4},
        {"source": "LSM", "tier": 1, "documents": 6, "skipped": 1,
         "status": "success", "cut_lede": 0, "web_documents": 6},
    ]

    def test_batch_header_carries_both_numbers(self, tmp_path):
        from src.ingest_log import append_ingest_batch_summary
        log = tmp_path / "log.md"
        append_ingest_batch_summary(self.RESULTS, log_path=str(log))
        text = log.read_text(encoding="utf-8")
        assert "2 no 10 web dokiem ar nogrieztu ievadu" in text, text

    def test_denominator_is_reported_on_a_clean_run_too(self, tmp_path):
        from src.ingest_log import append_ingest_batch_summary
        log = tmp_path / "log.md"
        clean = [dict(r, cut_lede=0) for r in self.RESULTS]
        append_ingest_batch_summary(clean, log_path=str(log))
        text = log.read_text(encoding="utf-8")
        assert "0 no 10 web dokiem ar nogrieztu ievadu" in text, text

    def test_the_flagging_source_is_named_in_its_own_entry(self, tmp_path):
        from src.ingest_log import append_ingest_batch_summary
        log = tmp_path / "log.md"
        append_ingest_batch_summary(self.RESULTS, log_path=str(log))
        lines = [ln for ln in log.read_text(encoding="utf-8").splitlines()
                 if ln.startswith("- ")]
        diena = [ln for ln in lines if "Diena.lv" in ln]
        lsm = [ln for ln in lines if "LSM" in ln]
        assert diena and "nogriezts ievads: 2/4" in diena[0], diena
        assert lsm and "nogriezts ievads" not in lsm[0], lsm

    def test_legacy_results_without_the_key_do_not_raise(self, tmp_path):
        """Callers predating the counter (scripts, tests) still pass through."""
        from src.ingest_log import append_ingest_batch_summary
        log = tmp_path / "log.md"
        append_ingest_batch_summary(
            [{"source": "Vecais", "tier": 1, "documents": 2, "status": "success"}],
            log_path=str(log),
        )
        assert "Vecais" in log.read_text(encoding="utf-8")
