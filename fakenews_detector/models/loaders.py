"""Cached, lazy model loaders.

In the original codebase, every call to ``spelling_mistakes`` reloaded a
~1.3 GB BERT model from disk. Each loader here is wrapped in
``lru_cache`` so the heavy I/O happens at most once per process.

All loaders raise :class:`FileNotFoundError` with a helpful message if
the artifact is missing on disk - models are deliberately gitignored
and must be obtained out-of-band (see README).
"""

from __future__ import annotations

import logging
import pickle
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib

from fakenews_detector.config import get_settings

log = logging.getLogger(__name__)


def _require(path: Path, kind: str) -> Path:
    if not path.exists():
        raise FileNotFoundError(
            f"Could not find {kind} at {path}. "
            f"This artifact is intentionally not tracked in git. "
            f"See README.md for setup instructions."
        )
    return path


# ----- HuggingFace transformer pipelines ----------------------------------


@lru_cache(maxsize=1)
def get_ner_pipeline():
    """NER pipeline used by the spelling check to skip person/location names."""
    from transformers import (
        AutoModelForTokenClassification,
        AutoTokenizer,
        pipeline,
    )

    model_dir = _require(get_settings().ner_model_dir, "NER model directory")
    log.info("Loading NER model from %s (one-time)", model_dir)
    model = AutoModelForTokenClassification.from_pretrained(str(model_dir))
    tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
    return pipeline(
        "ner", model=model, tokenizer=tokenizer, grouped_entities=True
    )


@lru_cache(maxsize=1)
def get_subjectivity_model():
    """Tuple of (model, tokenizer) used by the subjectivity check."""
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    model_dir = _require(
        get_settings().subjectivity_model_dir,
        "Subjectivity model directory",
    )
    log.info("Loading subjectivity model from %s (one-time)", model_dir)
    model = AutoModelForSequenceClassification.from_pretrained(str(model_dir))
    tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
    return model, tokenizer


@lru_cache(maxsize=1)
def get_sentence_embedder():
    """SentenceTransformer used by the web-presence similarity check."""
    from sentence_transformers import SentenceTransformer

    model_dir = _require(
        get_settings().sentence_embedding_model_dir,
        "Sentence-embedding model directory",
    )
    log.info("Loading sentence-transformer from %s (one-time)", model_dir)
    return SentenceTransformer(str(model_dir))


# ----- Custom pickled classifiers ----------------------------------------


@lru_cache(maxsize=1)
def get_clickbait_classifier() -> Any:
    path = _require(get_settings().clickbait_model_path, "clickbait model")
    log.info("Loading clickbait classifier from %s", path)
    with open(path, "rb") as f:
        return joblib.load(f)


@lru_cache(maxsize=1)
def get_clickbait_vectorizer() -> Any:
    path = _require(
        get_settings().clickbait_vectorizer_path, "clickbait vectorizer"
    )
    log.info("Loading clickbait vectorizer from %s", path)
    with open(path, "rb") as f:
        return pickle.load(f)


@lru_cache(maxsize=1)
def get_news_title_classifier() -> Any:
    path = _require(get_settings().news_title_model_path, "news-title model")
    log.info("Loading news-title classifier from %s", path)
    with open(path, "rb") as f:
        return joblib.load(f)


@lru_cache(maxsize=1)
def get_news_title_vectorizer() -> Any:
    path = _require(
        get_settings().news_title_vectorizer_path, "news-title vectorizer"
    )
    log.info("Loading news-title vectorizer from %s", path)
    with open(path, "rb") as f:
        return pickle.load(f)
