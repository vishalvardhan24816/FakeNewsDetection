"""Tests for `fakenews_detector.checks.spelling`.

We mock the NER pipeline (loading a real BERT NER model would be slow).
We DO use the real `pyspellchecker` -- it ships a small dictionary,
loads in milliseconds, and gives us realistic typo detection.
"""

from unittest.mock import MagicMock, patch

import pytest

from fakenews_detector.checks.spelling import SpellingCheck


def _patched_ner(entity_words):
    """Patch the NER pipeline to "tag" the given words as PER/LOC entities.

    `entity_words` is a list of lowercase words the NER should claim are
    named entities (so the spell checker skips them).
    """
    fake_ner = MagicMock()
    fake_ner.return_value = [
        {"word": w, "entity_group": "PER"} for w in entity_words
    ]
    return patch(
        "fakenews_detector.checks.spelling.get_ner_pipeline",
        return_value=fake_ner,
    )


class TestSpellingCheck:
    """Real pyspellchecker + mocked NER."""

    def test_clean_headline_passes(self):
        with _patched_ner(entity_words=[]):
            result = SpellingCheck().run("the cat sat on the mat")

        assert result.name == "spelling"
        assert result.passed is True
        assert result.detail == "no spelling issues"
        assert result.metadata["misspelled"] == []

    def test_named_entities_are_skipped(self):
        # Without NER, "Modi" would be flagged as a typo. Tagging it as
        # a PER entity should make the spell checker skip it.
        with _patched_ner(entity_words=["modi"]):
            result = SpellingCheck().run("modi visits the parliament")

        assert result.passed is True
        assert "modi" not in result.metadata["misspelled"]

    def test_obvious_typo_is_detected(self):
        # "heloo" should fail. We'd expect pyspellchecker to suggest
        # "hello" and the check to count it as misspelled.
        with _patched_ner(entity_words=[]):
            result = SpellingCheck().run("heloo")

        assert "heloo" in result.metadata["misspelled"]

    def test_metadata_contains_corrected_text_and_ratio(self):
        with _patched_ner(entity_words=[]):
            result = SpellingCheck().run("the cat sat on the mat")

        assert "corrected" in result.metadata
        assert isinstance(result.metadata["corrected"], str)
        assert "ratio" in result.metadata
        assert 0.0 <= result.metadata["ratio"] <= 1.0
