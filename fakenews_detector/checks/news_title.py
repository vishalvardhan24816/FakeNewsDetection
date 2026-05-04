"""Check 4 - Is-it-a-news-title-shape classifier.

A short opinion sentence ("I think X is great") may already have passed
the subjectivity check after preprocessing strips opinion words, but
it still doesn't *look* like a real news title. We trained a separate
classifier for this:

* Label 1 -> looks like a news title  (PASS)
* Label 0 -> looks like a normal sentence/paragraph (FAIL)

Same shape as the clickbait check: preprocess -> vectorize -> predict.
"""

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

    def run(self, headline):
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
