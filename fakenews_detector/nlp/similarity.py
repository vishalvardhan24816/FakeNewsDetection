"""Sentence similarity helpers used by the web-presence check.

Two layers, used in this order inside `web_presence`:

* ``cosine_similarity_score(a, b)`` -> float in [0, 1]
    Fast numerical similarity. Embeds both sentences with a
    SentenceTransformer model, then takes the cosine of the two vectors.
    Cheap, but can be fooled by sentences that look similar but mean
    different things.

* ``llm_contextual_match(headline, candidate)`` -> bool
    The final gate. Asks an LLM (Gemini or Claude) whether the two
    headlines describe the SAME factual event. Catches near-duplicates
    that differ in a single key fact, e.g. "9 killed" vs "19 killed".
"""

import logging

from sklearn.metrics.pairwise import cosine_similarity

from fakenews_detector.config import get_settings
from fakenews_detector.models.loaders import get_sentence_embedder

log = logging.getLogger(__name__)


# Same noisy-character set the original 2023 code stripped before
# comparing sentences. Notably we KEEP the apostrophe and the dash so
# words like "don't" and "co-founder" stay intact.
_NOISE_CHARS = '!#$%&()*+,."/:;<=>?@[\\]^_`{|}~'
_PUNCT_DROP = str.maketrans("", "", _NOISE_CHARS)


def _clean(sentence):
    """Lowercase + strip noisy punctuation."""
    return sentence.translate(_PUNCT_DROP).lower()


# The prompt sent to the LLM. We list every dimension that has to match
# (actors, action, location, NUMBERS) and give worked examples of
# near-misses that should still resolve to "no". Without explicit
# numbers + examples, the LLM happily said "yes" to pairs like
# "9 killed in Delhi blast" vs "19 killed in Delhi blast" because the
# overall event matched.
_PROMPT_TEMPLATE = """Compare these two news headlines:

  HEADLINE A: {headline}
  HEADLINE B: {candidate}

Do they describe the SAME factual event with the SAME key facts?
ALL of the following must match for the answer to be 'yes':
  - same actors / people / organisations
  - same action or outcome
  - same location
  - same numbers (casualty counts, monetary amounts, dates, ages, etc.)

If any number, name, or material fact differs, answer 'no' even if the
sentences look almost identical. Examples that are 'no':
  - '9 killed in Delhi fire' vs '19 killed in Delhi fire' (different count)
  - 'Modi visits Tokyo' vs 'Modi visits Seoul' (different place)
  - 'Apple raises $1B' vs 'Apple raises $10B' (different amount)

Answer with a single word: yes or no."""

_SYSTEM_PROMPT = (
    "You are a strict fact-comparison classifier for a fake-news "
    "detector. Treat any difference in numbers, names, or places as a "
    "factual mismatch. Reply with only 'yes' or 'no'."
)


def cosine_similarity_score(sentence_a, sentence_b):
    """Return cosine similarity in [0, 1] between two sentences."""
    embedder = get_sentence_embedder()
    vec_a, vec_b = embedder.encode([_clean(sentence_a), _clean(sentence_b)])
    return float(cosine_similarity([vec_a], [vec_b])[0][0])


def llm_contextual_match(headline, candidate):
    """Ask the LLM if `headline` and `candidate` describe the same event.

    Returns True only if the model answers 'yes'. Raises RuntimeError
    if no LLM provider is configured (no API key set).
    """
    settings = get_settings()
    provider = settings.resolve_llm_provider()
    prompt = _PROMPT_TEMPLATE.format(headline=headline, candidate=candidate)
    log.debug("LLM gate provider=%s", provider)

    if provider == "gemini":
        return _call_gemini(prompt, settings)
    if provider == "anthropic":
        return _call_anthropic(prompt, settings)

    raise RuntimeError(
        "No LLM provider configured. Set GOOGLE_GEMINI_API_KEY (recommended, "
        "free tier available) or ANTHROPIC_API_KEY in your .env file. "
        "See .env.example."
    )


def _call_gemini(prompt, settings):
    """Send prompt to Google Gemini, return True if reply starts with 'yes'."""
    # Lazy import: only loads google-genai if Gemini is actually used.
    from google import genai
    from google.genai import types as genai_types

    client = genai.Client(api_key=settings.gemini_api_key)

    # Disable Gemini's "thinking" tokens. We only need a 1-word verdict;
    # without this, Gemini 2.5+ burns its whole output budget on internal
    # reasoning and returns empty text with finish_reason=MAX_TOKENS.
    config = genai_types.GenerateContentConfig(
        system_instruction=_SYSTEM_PROMPT,
        temperature=0.0,
        max_output_tokens=50,
        thinking_config=genai_types.ThinkingConfig(thinking_budget=0),
    )

    response = client.models.generate_content(
        model=settings.gemini_model,
        contents=prompt,
        config=config,
    )
    reply = (response.text or "").strip().lower()
    log.debug("Gemini reply: %r", reply)
    return reply.startswith("yes")


def _call_anthropic(prompt, settings):
    """Send prompt to Anthropic Claude, return True if reply starts with 'yes'."""
    # Lazy import: only loads anthropic if Anthropic is actually used.
    import anthropic

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    message = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=10,
        temperature=0.0,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    reply = message.content[0].text.strip().lower()
    log.debug("Anthropic reply: %r", reply)
    return reply.startswith("yes")
