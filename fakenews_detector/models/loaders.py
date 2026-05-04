"""Loaders for the heavy ML models.

Each ML model takes 1-3 seconds and 100s of MB of RAM to load. We
only ever want to do that once per process, not on every request,
so we cache each loaded model in a module-level `_CACHE` dict.

If a model file is missing on disk, we raise FileNotFoundError with
a helpful message - models are gitignored and have to be downloaded
separately (see README).

Public functions, one per check / model:

    get_ner_pipeline()              # used by the spelling check
    get_subjectivity_model()        # used by the subjectivity check
    get_sentence_embedder()         # used by the web-presence check
    get_clickbait_classifier()      # used by the clickbait check
    get_clickbait_vectorizer()      #     "
    get_news_title_classifier()     # used by the news-title check
    get_news_title_vectorizer()     #     "
"""

import logging

import joblib

from fakenews_detector.config import get_settings

log = logging.getLogger(__name__)


# Cache: name -> the loaded model. Empty at startup; filled on first use.
_CACHE = {}


def _require_exists(path, kind):
    """Raise a friendly error if a model file/dir is missing on disk."""
    if not path.exists():
        raise FileNotFoundError(
            f"Could not find {kind} at {path}. "
            f"This file is gitignored - see README.md for setup instructions."
        )
    return path


def _load_pickle_once(cache_key, path, kind):
    """Load a pickled model from disk on first call, cache it, then reuse."""
    if cache_key in _CACHE:
        return _CACHE[cache_key]
    _require_exists(path, kind)
    log.info("Loading %s from %s", kind, path)
    _CACHE[cache_key] = joblib.load(path)
    return _CACHE[cache_key]


# ---------- Hugging Face transformer models ----------


def get_ner_pipeline():
    """NER pipeline used by the spelling check to skip names of people/places."""
    if "ner" in _CACHE:
        return _CACHE["ner"]

    from transformers import (
        AutoModelForTokenClassification,
        AutoTokenizer,
        pipeline,
    )

    model_dir = _require_exists(get_settings().ner_model_dir, "NER model")
    log.info("Loading NER model from %s (one-time)", model_dir)
    model = AutoModelForTokenClassification.from_pretrained(str(model_dir))
    tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
    # dbmdz dl model
    _CACHE["ner"] = pipeline(
        "ner", model=model, tokenizer=tokenizer, grouped_entities=True
    )
    return _CACHE["ner"]


def get_subjectivity_model():
    """(model, tokenizer) pair used by the subjectivity check."""
    if "subjectivity" in _CACHE:
        return _CACHE["subjectivity"]

    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    model_dir = _require_exists(
        get_settings().subjectivity_model_dir, "subjectivity model"
    )
    log.info("Loading subjectivity model from %s (one-time)", model_dir)
    model = AutoModelForSequenceClassification.from_pretrained(str(model_dir))
    tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
    _CACHE["subjectivity"] = (model, tokenizer)
    return _CACHE["subjectivity"]


def get_sentence_embedder():
    """Sentence embedder used by the web-presence similarity check."""
    if "embedder" in _CACHE:
        return _CACHE["embedder"]

    from sentence_transformers import SentenceTransformer

    model_dir = _require_exists(
        get_settings().sentence_embedder_dir, "sentence embedder"
    )
    log.info("Loading sentence embedder from %s (one-time)", model_dir)
    _CACHE["embedder"] = SentenceTransformer(str(model_dir))
    return _CACHE["embedder"]


# ---------- Custom-trained sklearn classifiers (.pkl files) ----------


def get_clickbait_classifier():
    return _load_pickle_once(
        "clickbait_classifier",
        get_settings().clickbait_classifier_path,
        "clickbait classifier",
    )


def get_clickbait_vectorizer():
    return _load_pickle_once(
        "clickbait_vectorizer",
        get_settings().clickbait_vectorizer_path,
        "clickbait vectorizer",
    )


def get_news_title_classifier():
    return _load_pickle_once(
        "news_title_classifier",
        get_settings().news_title_classifier_path,
        "news-title classifier",
    )


def get_news_title_vectorizer():
    return _load_pickle_once(
        "news_title_vectorizer",
        get_settings().news_title_vectorizer_path,
        "news-title vectorizer",
    )
