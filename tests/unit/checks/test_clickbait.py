"""Tests for `fakenews_detector.checks.clickbait`.

We mock both the classifier and the vectorizer so the test never
touches a real `.pkl` file or trains anything. The exact same shape of
test applies to news_title.py because the two checks share an identical
flow (preprocess -> vectorize -> predict).
"""

from unittest.mock import MagicMock, patch

import pytest

from fakenews_detector.checks.clickbait import ClickbaitCheck


def _patched_check(prediction):
    """Build patches for vectorizer + classifier returning `prediction`."""
    fake_vectorizer = MagicMock()
    fake_vectorizer.transform.return_value = "FAKE_VEC"

    fake_classifier = MagicMock()
    fake_classifier.predict.return_value = [prediction]

    return (
        patch(
            "fakenews_detector.checks.clickbait.get_clickbait_vectorizer",
            return_value=fake_vectorizer,
        ),
        patch(
            "fakenews_detector.checks.clickbait.get_clickbait_classifier",
            return_value=fake_classifier,
        ),
        fake_vectorizer,
        fake_classifier,
    )


class TestClickbaitCheck:
    """Maps classifier output 0 -> pass, 1 -> fail."""

    def test_passes_when_classifier_predicts_zero(self):
        v_patch, c_patch, _vec, _clf = _patched_check(prediction=0)
        with v_patch, c_patch:
            result = ClickbaitCheck().run("ISRO launches Chandrayaan-3")

        assert result.name == "clickbait"
        assert result.passed is True
        assert "not clickbait" in result.detail.lower()
        assert result.metadata["prediction"] == 0

    def test_fails_when_classifier_predicts_one(self):
        v_patch, c_patch, _vec, _clf = _patched_check(prediction=1)
        with v_patch, c_patch:
            result = ClickbaitCheck().run("You won't BELIEVE what happens next!")

        assert result.passed is False
        assert "clickbait" in result.detail.lower()
        assert result.metadata["prediction"] == 1

    def test_runs_preprocessing_before_vectorizing(self):
        # The vectorizer should receive a Pandas Series whose value is
        # the *normalized* (lowercase + lemmatized) headline, not the raw
        # input. We assert against a substring to keep it stable.
        v_patch, c_patch, vec, _clf = _patched_check(prediction=0)
        with v_patch, c_patch:
            ClickbaitCheck().run("Cats Are RUNNING Fast!!!")

        # `transform` was called with a pandas Series; pull the value out.
        call_arg = vec.transform.call_args.args[0]
        normalized_value = list(call_arg.values)[0]
        assert normalized_value == normalized_value.lower()
        # Lemmatized: "cats" -> "cat"
        assert "cat" in normalized_value.split()
