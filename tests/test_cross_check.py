"""Tests for src/cross_check.py — cosine similarity and report formatting."""

import pytest
from src.cross_check import _cosine_similarity, print_cross_check_report


class TestCosineSimilarity:
    def test_identical_vectors(self):
        v = [1.0, 2.0, 3.0]
        assert _cosine_similarity(v, v) == pytest.approx(1.0)

    def test_orthogonal_vectors(self):
        a = [1.0, 0.0]
        b = [0.0, 1.0]
        assert _cosine_similarity(a, b) == pytest.approx(0.0)

    def test_opposite_vectors(self):
        a = [1.0, 0.0]
        b = [-1.0, 0.0]
        assert _cosine_similarity(a, b) == pytest.approx(-1.0)

    def test_zero_vector_returns_zero(self):
        a = [0.0, 0.0, 0.0]
        b = [1.0, 2.0, 3.0]
        assert _cosine_similarity(a, b) == 0.0

    def test_similar_vectors(self):
        a = [1.0, 2.0, 3.0]
        b = [1.1, 2.1, 3.1]
        sim = _cosine_similarity(a, b)
        assert sim > 0.99  # very similar

    def test_different_vectors(self):
        a = [1.0, 0.0, 0.0]
        b = [0.0, 0.0, 1.0]
        assert _cosine_similarity(a, b) == pytest.approx(0.0)


class TestPrintCrossCheckReport:
    def test_empty_results(self, capsys):
        print_cross_check_report([])
        out = capsys.readouterr().out
        assert "Nav atrasti" in out

    def test_with_results(self, capsys):
        results = [{
            "politician_name": "Jānis Tests",
            "politician_id": 1,
            "party": "TestPartija",
            "topic": "NATO",
            "claim_1_id": 10,
            "claim_1_stance": "Atbalsta NATO finansējumu",
            "claim_1_date": "2026-01-15",
            "claim_1_source": "https://example.com/1",
            "claim_2_id": 20,
            "claim_2_stance": "Pret NATO finansējuma palielināšanu",
            "claim_2_date": "2026-03-20",
            "claim_2_source": "https://example.com/2",
            "similarity": 0.912,
        }]
        print_cross_check_report(results)
        out = capsys.readouterr().out
        assert "Jānis Tests" in out
        assert "NATO" in out
        assert "0.912" in out
        assert "1 potenciāli" in out

    def test_truncates_long_stances(self, capsys):
        results = [{
            "politician_name": "Test",
            "politician_id": 1,
            "party": "TP",
            "topic": "x",
            "claim_1_id": 1,
            "claim_1_stance": "A" * 200,
            "claim_1_date": "2026-01-01",
            "claim_1_source": "",
            "claim_2_id": 2,
            "claim_2_stance": "B" * 200,
            "claim_2_date": "2026-02-01",
            "claim_2_source": "",
            "similarity": 0.5,
        }]
        print_cross_check_report(results)
        out = capsys.readouterr().out
        # Stances are truncated to 120 chars
        assert "A" * 121 not in out
