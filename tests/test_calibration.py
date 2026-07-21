"""Tests for src/calibration.py — language detection helpers and cosine similarity."""

import pytest
from src.calibration import _cosine_similarity, _get_expected_lang


class TestCalibrationCosineSimilarity:
    def test_identical(self):
        v = [1.0, 2.0, 3.0]
        assert _cosine_similarity(v, v) == pytest.approx(1.0)

    def test_orthogonal(self):
        assert _cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)

    def test_opposite(self):
        assert _cosine_similarity([1.0], [-1.0]) == pytest.approx(-1.0)


class TestGetExpectedLang:
    def test_lv_prefix(self):
        assert _get_expected_lang("lv_healthcare.txt") == "lv"

    def test_ru_prefix(self):
        assert _get_expected_lang("ru_nato.txt") == "ru"

    def test_lv_suffix(self):
        assert _get_expected_lang("pair1_lv.txt") == "lv"

    def test_ru_suffix(self):
        assert _get_expected_lang("pair1_ru.txt") == "ru"

    def test_trap_sarcasm_lv(self):
        assert _get_expected_lang("trap_sarcasm1.txt") == "lv"

    def test_trap_sarcasm_ru(self):
        assert _get_expected_lang("trap_sarcasm2.txt") == "ru"

    def test_trap_hypothetical(self):
        assert _get_expected_lang("trap_hypothetical.txt") == "lv"

    def test_unknown_file(self):
        assert _get_expected_lang("random_file.txt") is None
