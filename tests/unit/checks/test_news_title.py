"""Tests for `fakenews_detector.checks.news_title`.

Same shape as the clickbait check (preprocess -> vectorize -> predict),
but the label semantics are inverted: 1 = looks like a news title (PASS),
0 = looks like a regular sentence (FAIL).
"""

from unittest.mock import MagicMock, patch

import pytest

from fakenews_detector.checks.news_title import NewsTitleCheck


def _patched_check(prediction):
    fake_vectorizer = MagicMock()
    fake_vectorizer.transform.return_value = "FAKE_VEC"
    fake_classifier = MagicMock()
    fake_classifier.predict.return_value = [prediction]

    return (
        patch(
            "fakenews_detector.checks.news_title.get_news_title_vectorizer",
            return_value=fake_vectorizer,
        ),
        patch(
            "fakenews_detector.checks.news_title.get_news_title_classifier",
            return_value=fake_classifier,
        ),
    )


class TestNewsTitleCheck:
    """Label 1 = news-title shape -> PASS. Label 0 = normal sentence -> FAIL."""

    def test_passes_when_classifier_predicts_one(self):
        v_patch, c_patch = _patched_check(prediction=1)
        with v_patch, c_patch:
            result = NewsTitleCheck().run(
                "ISRO Launches Chandrayaan-3 Mission to the Moon"
            )

        assert result.name == "news_title"
        assert result.passed is True
        assert "looks like a news title" in result.detail.lower()
        assert result.metadata["prediction"] == 1

    def test_fails_when_classifier_predicts_zero(self):
        v_patch, c_patch = _patched_check(prediction=0)
        with v_patch, c_patch:
            result = NewsTitleCheck().run("i think apples are pretty good honestly")

        assert result.passed is False
        assert "does not look like a news title" in result.detail.lower()
        assert result.metadata["prediction"] == 0
