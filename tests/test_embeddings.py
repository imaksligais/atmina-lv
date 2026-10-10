"""Tests for src/embeddings.py — lemmatization (lightweight, no model download)."""

from src.embeddings import lemmatize


class TestLemmatize:
    def test_latvian_noun(self):
        result = lemmatize("politiķiem", lang="lv")
        # simplemma should reduce to base form
        assert isinstance(result, str)
        assert len(result) > 0

    def test_latvian_verb(self):
        result = lemmatize("strādāju", lang="lv")
        assert isinstance(result, str)

    def test_multiple_words(self):
        result = lemmatize("politiķi strādā kopā", lang="lv")
        words = result.split()
        assert len(words) == 3

    def test_empty_string(self):
        result = lemmatize("", lang="lv")
        assert result == ""

    def test_russian_lang(self):
        result = lemmatize("работает", lang="ru")
        assert isinstance(result, str)

    def test_preserves_word_count(self):
        text = "viens divi trīs četri pieci"
        result = lemmatize(text, lang="lv")
        assert len(result.split()) == 5

    def test_single_word(self):
        result = lemmatize("Latvija", lang="lv")
        assert isinstance(result, str)
        assert len(result) > 0
