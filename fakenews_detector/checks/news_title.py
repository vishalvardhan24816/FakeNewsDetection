"""Step 4 - is-news-title gate.

A custom-trained classifier decides whether the input looks like an
actual news title vs. a normal sentence/paragraph. Prediction != 0
means "yes, this is a news title", so the check passes.
"""

from __future__ import annotations

import logging

import pandas as pd

from fakenews_detector.checks.base import Check, CheckResult
from fakenews_detector.models.loaders import (
    get_news_title_classifier,
    get_news_title_vectorizer,
)
from fakenews_detector.nlp.preprocessing import normalize_for_classifier

log = logging.getLogger(__name__)


class NewsTitleCheck(Check):
    name = "news_title"

    def run(self, headline: str) -> CheckResult:
        normalized = normalize_for_classifier(headline)
        vector = get_news_title_vectorizer().transform(pd.Series({1: normalized}))
        prediction = int(get_news_title_classifier().predict(vector)[0])

        passed = prediction != 0
        log.info("news-title classifier prediction=%d (passed=%s)", prediction, passed)

        return CheckResult(
            name=self.name,
            passed=passed,
            detail=(
                "looks like a news title"
                if passed
                else "does not look like a news title"
            ),
            metadata={"prediction": prediction},
        )
