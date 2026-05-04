"""Text preprocessing helpers used across the validation checks.

Two functions live here:

* ``normalize_for_classifier`` -- clean text the way a TF-IDF + Naive
  Bayes classifier wants it (lowercase, strip junk, lemmatize words to
  their root form). Used by the clickbait and news-title checks AND by
  the training script, so training and inference stay in lockstep.

* ``normalize_for_spellcheck`` -- light cleanup for the spell checker.
  We deliberately do NOT lemmatize here -- the spell checker needs the
  original word forms to know what's a typo.
"""

import re
import string

import nltk

# WordNet is the dictionary the lemmatizer uses. Built lazily on first
# use so just importing this module stays cheap.
_LEMMATIZER = None


def _lemmatizer():
    """Return the shared WordNetLemmatizer, downloading data on first use."""
    global _LEMMATIZER
    if _LEMMATIZER is None:
        nltk.download("wordnet", quiet=True)
        nltk.download("omw-1.4", quiet=True)
        _LEMMATIZER = nltk.stem.WordNetLemmatizer()
    return _LEMMATIZER


# ---------- Pipeline used by clickbait + news-title classifiers ----------

# One translation table that drops every digit and every punctuation
# char in a single pass. Cleaner than chaining list comprehensions.
_DROP_CHARS = str.maketrans("", "", string.punctuation + string.digits)


def normalize_for_classifier(text):
    """Lowercase, strip punctuation/digits, lemmatize. Returns a string.

    Example:
        "You won't BELIEVE this!! 5 things..."
            -> "you wont believe this thing"
    """
    cleaned = text.lower().translate(_DROP_CHARS)
    lemmas = [_lemmatizer().lemmatize(word) for word in cleaned.split()]
    return " ".join(lemmas)


# ---------- Pipeline used by the spelling check ----------

_HTML_TAG_RE = re.compile(r"<.*?>")
_URL_RE = re.compile(r"https?://\S+|www\.\S+")
_NOISE_CHARS_RE = re.compile(r'[:!#$%&()*+,.\-"/:;<=>?@\[\]^_`{|}~]')


def normalize_for_spellcheck(text):
    """Lowercase + strip HTML tags, URLs, and noisy punctuation.

    Word forms are preserved (no lemmatizing) -- the spell checker
    needs to see the actual word the user typed.
    """
    text = text.lower()
    text = _HTML_TAG_RE.sub("", text)
    text = _URL_RE.sub("", text)
    text = _NOISE_CHARS_RE.sub("", text)
    return text
