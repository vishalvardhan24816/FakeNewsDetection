"""Check 2 - Clickbait classifier.

We trained a small classifier (Naive Bayes / Random Forest) on a
labelled dataset of clickbait vs. real news headlines. At runtime:

1. Run the headline through the same preprocessing the model saw at
   training time (lowercase + strip punctuation + lemmatize).
2. Turn it into a TF-IDF vector using the saved vectorizer.
3. Ask the classifier to predict: 0 = real news, 1 = clickbait.

We pass when the prediction is 0.
"""

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

    def run(self, headline):
        normalized = normalize_for_classifier(headline)
        # The vectorizer expects a pandas Series (that's how it was
        # trained), so we wrap our single string in one.
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
