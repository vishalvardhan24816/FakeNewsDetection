"""Train the clickbait classifier used by :class:`ClickbaitCheck`.

Inputs
------
* ``datasets/clickbait_data.csv`` - two columns: ``headline``,
  ``clickbait`` (0/1).

Outputs
-------
* ``mlmodels/clickbaitmodel.pkl`` - the trained MultinomialNB model.

Run
---
    python -m training.train_clickbait
"""

from __future__ import annotations

import logging
from pathlib import Path

import joblib
import nltk
import pandas as pd
from nltk.corpus import stopwords
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import MultinomialNB

from fakenews_detector.config import PROJECT_ROOT
from fakenews_detector.logging_setup import configure_logging
from fakenews_detector.nlp.preprocessing import (
    lemmatize,
    lowercase,
    strip_digits,
    strip_punctuation,
    strip_spaces,
    tokenize,
)

log = logging.getLogger(__name__)

DATASET_PATH = PROJECT_ROOT / "datasets" / "clickbait_data.csv"
MODEL_OUT_PATH = PROJECT_ROOT / "mlmodels" / "clickbaitmodel.pkl"


def _ensure_stopwords() -> set:
    try:
        nltk.data.find("corpora/stopwords")
    except LookupError:
        nltk.download("stopwords", quiet=True)
    return set(stopwords.words("english"))


def _preprocess_series(series: pd.Series, stop: set) -> pd.Series:
    """Apply the full preprocessing pipeline used at inference time, plus
    stopword removal which the inference path skips."""
    return (
        series.apply(tokenize)
        .apply(lowercase)
        .apply(lambda toks: [t for t in toks if t not in stop])
        .apply(strip_punctuation)
        .apply(strip_digits)
        .apply(strip_spaces)
        .apply(lemmatize)
        .apply(lambda toks: " ".join(toks))
    )


def main(
    dataset_path: Path = DATASET_PATH,
    model_out_path: Path = MODEL_OUT_PATH,
) -> None:
    configure_logging()
    log.info("Loading dataset from %s", dataset_path)
    df = pd.read_csv(dataset_path)

    stop = _ensure_stopwords()

    log.info("Preprocessing %d examples", len(df))
    train_x, test_x, train_y, test_y = train_test_split(
        df["headline"],
        df["clickbait"],
        test_size=0.25,
        random_state=22,
        stratify=df["clickbait"],
    )

    train_x = _preprocess_series(train_x, stop)
    test_x = _preprocess_series(test_x, stop)

    log.info("Fitting TF-IDF vectorizer")
    tfidf = TfidfVectorizer()
    train_vec = tfidf.fit_transform(train_x)
    test_vec = tfidf.transform(test_x)

    log.info("Training MultinomialNB")
    clf = MultinomialNB()
    clf.fit(train_vec.toarray(), train_y)

    pred = clf.predict(test_vec.toarray())
    f1 = f1_score(test_y, pred)
    acc = accuracy_score(test_y, pred)
    log.info("F1=%.4f  Accuracy=%.4f (%.2f%%)", f1, acc, acc * 100)

    model_out_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(clf, model_out_path)
    log.info("Saved model to %s", model_out_path)


if __name__ == "__main__":
    main()
