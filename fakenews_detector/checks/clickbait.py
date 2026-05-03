"""Step 2 - clickbait gate.

Vectorize the (preprocessed) headline with the trained TF-IDF and feed
it into the trained classifier (`mlmodels/impclickbait.pkl`). A
prediction of 0 means "not clickbait" -> the check passes.
"""

from __future__ import annotations

import logging

import pandas as pd

from fakenews_detector.checks.base import Check, CheckResult
from fakenews_detector.models.loaders import (
    get_clickbait_classifier,
    get_clickbait_vectorizer,
)
from fakenews_detector.nlp.preprocessing import normalize_for_classifier

log = logging.getLogger(__name__)


class ClickbaitCheck(Check):
    name = "clickbait"

    def run(self, headline: str) -> CheckResult:
        normalized = normalize_for_classifier(headline)
        vector = get_clickbait_vectorizer().transform(pd.Series({1: normalized}))
        prediction = int(get_clickbait_classifier().predict(vector)[0])

        passed = prediction == 0
        log.info("clickbait classifier prediction=%d (passed=%s)", prediction, passed)

        return CheckResult(
            name=self.name,
            passed=passed,
            detail="not clickbait" if passed else "looks like a clickbait title",
            metadata={"prediction": prediction},
        )
