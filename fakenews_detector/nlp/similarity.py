"""Sentence similarity utilities.

Two layers:

* :func:`cosine_similarity_score` - fast numerical similarity using the
  cached SentenceTransformer.
* :func:`llm_contextual_match` - calls Anthropic Claude for a final
  yes/no contextual-similarity verdict (5th check, last gate).
"""

from __future__ import annotations

import logging
import string
from typing import Optional

import anthropic
from sklearn.metrics.pairwise import cosine_similarity

from fakenews_detector.config import get_settings
from fakenews_detector.models.loaders import get_sentence_embedder

log = logging.getLogger(__name__)

# Same noise-character set the original similarity.py used.
_EXCLUDE = '[!#$%&()*+,."/:;<=>?@\\[\\^_`{|}~]'
_TRANS = str.maketrans("", "", _EXCLUDE)


def _clean(sentence: str) -> str:
    return sentence.translate(_TRANS).lower()


def cosine_similarity_score(sentence_a: str, sentence_b: str) -> float:
    """Cosine similarity in [0, 1] between two sentence embeddings."""
    embedder = get_sentence_embedder()
    embeddings = embedder.encode([_clean(sentence_a), _clean(sentence_b)])
    score = float(cosine_similarity([embeddings[0]], [embeddings[1]])[0][0])
    return score


def llm_contextual_match(
    headline: str, candidate: str, *, client: Optional[anthropic.Anthropic] = None
) -> bool:
    """Ask Claude whether `headline` and `candidate` are contextually similar.

    Returns True iff the LLM answers "yes". Raises if no API key is set,
    so callers know when this gate is unavailable.
    """
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Required for the LLM gate of the "
            "web-presence check. Add it to your .env file."
        )

    if client is None:
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    prompt = (
        f"i have two sentences sentence1 = {headline} sentence2 = {candidate} "
        "based on the exact specific subject matter and and dont consider "
        "specific meaning differences, is the first statement contextually "
        "similar in meaning to the second statement?, just say yes or no"
    )

    log.debug("Sending similarity prompt to %s", settings.anthropic_model)
    message = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=1000,
        temperature=0.0,
        system="Respond only in english.",
        messages=[{"role": "user", "content": prompt}],
    )
    response_text = message.content[0].text.lstrip().lower()
    log.debug("LLM response: %s", response_text)
    return "yes" in response_text
