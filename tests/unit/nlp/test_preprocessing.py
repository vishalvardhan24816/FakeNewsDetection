"""Tests for `fakenews_detector.nlp.preprocessing`.

The two preprocessing functions are deterministic (no I/O, no models)
so we can test them with plain assertions on string inputs and outputs.
We do exercise the real WordNet lemmatizer in `normalize_for_classifier`
- it's small and lazy-loaded once, then cached.
"""

import pytest

from fakenews_detector.nlp import preprocessing
from fakenews_detector.nlp.preprocessing import (
    normalize_for_classifier,
    normalize_for_spellcheck,
)


# ----- normalize_for_classifier -----------------------------------------


class TestNormalizeForClassifier:
    """Aggressive cleanup pipeline used by clickbait + news-title checks."""

    def test_lowercases_input(self):
        assert normalize_for_classifier("HELLO World") == "hello world"

    def test_strips_punctuation(self):
        # The result should contain none of these characters.
        cleaned = normalize_for_classifier("Hi! Are you OK? (yes...)")
        assert "!" not in cleaned
        assert "?" not in cleaned
        assert "(" not in cleaned

    def test_strips_digits(self):
        # Digits go away entirely; surrounding words survive.
        assert normalize_for_classifier("5 things you must know") == (
            "thing you must know"
        )

    def test_lemmatizes_plurals_to_singular(self):
        # "things" -> "thing", "cats" -> "cat".
        assert "thing" in normalize_for_classifier("things").split()
        assert "cat" in normalize_for_classifier("cats").split()

    def test_returns_a_string_not_a_list(self):
        # The TF-IDF vectorizer expects a single space-joined string.
        out = normalize_for_classifier("hello world")
        assert isinstance(out, str)

    def test_handles_empty_string(self):
        assert normalize_for_classifier("") == ""

    def test_handles_only_punctuation(self):
        assert normalize_for_classifier("!!!???...") == ""


# ----- normalize_for_spellcheck -----------------------------------------


class TestNormalizeForSpellcheck:
    """Light cleanup used by the spelling check. Word forms must survive."""

    def test_lowercases_input(self):
        assert normalize_for_spellcheck("HELLO World") == "hello world"

    def test_strips_html_tags(self):
        assert normalize_for_spellcheck("<b>hi</b> world") == "hi world"

    def test_strips_urls(self):
        # Both `http://` and `www.` URLs disappear.
        assert "https" not in normalize_for_spellcheck("see https://example.com here")
        assert "www" not in normalize_for_spellcheck("see www.example.com here")

    def test_does_not_lemmatize(self):
        # Critical: the spell checker needs the original word forms so
        # it can detect typos. "things" must NOT collapse to "thing".
        assert "things" in normalize_for_spellcheck("things").split()

    def test_strips_noisy_punctuation(self):
        out = normalize_for_spellcheck("hello, world!")
        assert "," not in out
        assert "!" not in out


# ----- lazy lemmatizer init ---------------------------------------------


class TestLazyLemmatizer:
    """The lemmatizer is built once on first call and cached after."""

    def test_lemmatizer_is_cached_across_calls(self):
        first = preprocessing._lemmatizer()
        second = preprocessing._lemmatizer()
        # `is`, not `==`: same object identity in memory.
        assert first is second
