"""Sentence similarity utilities.

Two layers:

* :func:`cosine_similarity_score` - fast numerical similarity using the
  cached SentenceTransformer.
* :func:`llm_contextual_match` - asks an LLM for a final yes/no
  contextual-similarity verdict (5th check, last gate). Provider is
  auto-selected from settings; supports Gemini and Anthropic out of the
  box. Adding a third provider is a single ``elif`` away.
"""

from __future__ import annotations

import logging
from typing import Optional

from sklearn.metrics.pairwise import cosine_similarity

from fakenews_detector.config import Settings, get_settings
from fakenews_detector.models.loaders import get_sentence_embedder

log = logging.getLogger(__name__)

_EXCLUDE = '[!#$%&()*+,."/:;<=>?@\\[\\^_`{|}~]'
_TRANS = str.maketrans("", "", _EXCLUDE)

# Strict factual-match prompt. Earlier versions only said "same actors,
# same action, same place" - the LLM happily said "yes" to pairs like
# "9 killed in Delhi blast" vs "19 killed in Delhi blast" because the
# overall event (Delhi blast) matched. For fake-news detection we MUST
# treat changed numbers/names as different facts, so the prompt now
# enumerates every dimension that has to match and gives a worked
# example of a near-miss that should resolve to "no".
_PROMPT_TEMPLATE = (
    "Compare these two news headlines:\n\n"
    "  HEADLINE A: {headline}\n"
    "  HEADLINE B: {candidate}\n\n"
    "Do they describe the SAME factual event with the SAME key facts? "
    "They should be strictly identical and contextually similar as well"
    "Answer with a single word: yes or no."
)
_SYSTEM_PROMPT = (
    "You are a strict fact-comparison classifier for a fake-news "
    "detector. Treat any difference in numbers, names, or places as "
    "a factual mismatch. Reply with only 'yes' or 'no'."
)


def _clean(sentence: str) -> str:
    return sentence.translate(_TRANS).lower()


def cosine_similarity_score(sentence_a: str, sentence_b: str) -> float:
    """Cosine similarity in [0, 1] between two sentence embeddings."""
    embedder = get_sentence_embedder()
    embeddings = embedder.encode([_clean(sentence_a), _clean(sentence_b)])
    score = float(cosine_similarity([embeddings[0]], [embeddings[1]])[0][0])
    return score


def llm_contextual_match(
    headline: str,
    candidate: str,
    *,
    settings: Optional[Settings] = None,
) -> bool:
    """Ask an LLM whether ``headline`` and ``candidate`` are contextually similar.

    Returns True iff the LLM answers "yes". Raises :class:`RuntimeError`
    if no provider is configured / no key is set.
    """
    settings = settings or get_settings()
    provider = settings.resolve_llm_provider()
    prompt = _PROMPT_TEMPLATE.format(headline=headline, candidate=candidate)

    log.debug("LLM gate provider=%s", provider)
    if provider == "gemini":
        return _call_gemini(prompt, settings)
    if provider == "anthropic":
        return _call_anthropic(prompt, settings)
    if provider == "none":
        raise RuntimeError(
            "No LLM provider configured. Set GOOGLE_GEMINI_API_KEY (recommended, "
            "free tier available) or ANTHROPIC_API_KEY in your .env file. "
            "See .env.example."
        )
    raise RuntimeError(f"Unknown LLM_PROVIDER={provider!r}")


def _call_gemini(prompt: str, settings: Settings) -> bool:
    if not settings.gemini_api_key:
        raise RuntimeError("Gemini selected but no Gemini API key is set.")

    # Lazy import so users on the Anthropic path don't need google-genai installed.
    try:
        from google import genai
        from google.genai import types as genai_types
    except ImportError as exc:
        raise RuntimeError(
            "google-genai is not installed. Run: pip install google-genai"
        ) from exc

    client = genai.Client(api_key=settings.gemini_api_key)
    # Disable "thinking" tokens - we want a 1-word verdict, not reasoning.
    # Without this, Gemini 2.5/3 will burn the whole output budget on
    # internal thoughts and return empty content with finish_reason=MAX_TOKENS.
    config_kwargs = dict(
        system_instruction=_SYSTEM_PROMPT,
        temperature=0.0,
        max_output_tokens=50,
    )
    thinking_cfg_cls = getattr(genai_types, "ThinkingConfig", None)
    if thinking_cfg_cls is not None:
        config_kwargs["thinking_config"] = thinking_cfg_cls(thinking_budget=0)

    response = client.models.generate_content(
        model=settings.gemini_model,
        contents=prompt,
        config=genai_types.GenerateContentConfig(**config_kwargs),
    )
    text = (response.text or "").strip().lower()
    log.debug("Gemini reply: %r", text)
    return text.startswith("yes")


def _call_anthropic(prompt: str, settings: Settings) -> bool:
    if not settings.anthropic_api_key:
        raise RuntimeError("Anthropic selected but no Anthropic API key is set.")

    try:
        import anthropic
    except ImportError as exc:
        raise RuntimeError(
            "anthropic is not installed. Run: pip install anthropic"
        ) from exc

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    message = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=10,
        temperature=0.0,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    text = message.content[0].text.strip().lower()
    log.debug("Anthropic reply: %r", text)
    return text.startswith("yes")
