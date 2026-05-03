"""Shared text preprocessing pipeline.

Both the clickbait classifier and the is-news-title classifier originally
duplicated this exact logic in two files. It now lives here once.
"""

from __future__ import annotations

import re
import string
from functools import lru_cache
from typing import Iterable, List

import nltk

_PUNCT = set(string.punctuation)
_DIGITS = set(string.digits)


@lru_cache(maxsize=1)
def _lemmatizer() -> "nltk.stem.WordNetLemmatizer":
    """Lazy-load the WordNet lemmatizer (and its data) once."""
    try:
        nltk.data.find("corpora/wordnet")
    except LookupError:
        nltk.download("wordnet", quiet=True)
    try:
        nltk.data.find("corpora/omw-1.4")
    except LookupError:
        nltk.download("omw-1.4", quiet=True)
    return nltk.stem.WordNetLemmatizer()


def tokenize(text: str) -> List[str]:
    """Whitespace tokenization (matches the original pipeline)."""
    return text.split()


def lowercase(tokens: Iterable[str]) -> List[str]:
    return [t.lower() for t in tokens]


def strip_punctuation(tokens: Iterable[str]) -> List[str]:
    return ["".join(c for c in t if c not in _PUNCT) for t in tokens]


def strip_digits(tokens: Iterable[str]) -> List[str]:
    cleaned = ["".join(c for c in t if c not in _DIGITS) for t in tokens]
    return [t for t in cleaned if t]


def strip_spaces(tokens: Iterable[str]) -> List[str]:
    return [t.strip() for t in tokens]


def lemmatize(tokens: Iterable[str]) -> List[str]:
    lem = _lemmatizer()
    return [lem.lemmatize(t) for t in tokens]


def normalize_for_classifier(text: str) -> str:
    """Full preprocessing pipeline used by the classifier-based checks.

    Returns a single space-joined string ready to be vectorized.
    """
    tokens = tokenize(text)
    tokens = lowercase(tokens)
    tokens = strip_spaces(tokens)
    tokens = strip_digits(tokens)
    tokens = strip_punctuation(tokens)
    tokens = lemmatize(tokens)
    return " ".join(tokens)


# ---------- helpers used by the spelling check ----------

_HTML_TAG_RE = re.compile(r"<.*?>")
_URL_RE = re.compile(r"https?://\S+|www\.\S+")
_NOISE_CHARS_RE = re.compile(r'[:!#$%&()*+,.\-"/:;<=>?@\[\]^_`{|}~]')


def normalize_for_spellcheck(text: str) -> str:
    """Lowercase + strip HTML/URLs/noise punctuation. Used by spelling check."""
    text = text.lower()
    text = _HTML_TAG_RE.sub("", text)
    text = _URL_RE.sub("", text)
    text = _NOISE_CHARS_RE.sub("", text)
    return text
