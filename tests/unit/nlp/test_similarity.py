"""Tests for `fakenews_detector.nlp.similarity`.

We mock both heavy dependencies:

* The SentenceTransformer embedder (`get_sentence_embedder`) -- loading
  it would download a real Hugging Face model.
* The LLM clients (Gemini / Anthropic) -- calling them would make a
  real network request and cost money.

Each test patches the dependency at the *similarity module path*, not
at the original definition path, because Python re-binds names at
import time.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from fakenews_detector.nlp import similarity


# ----- cosine_similarity_score ------------------------------------------


class TestCosineSimilarityScore:
    """`cosine_similarity_score` should return a float in [0, 1]."""

    def test_identical_vectors_score_one(self):
        # Mock embedder returns the same vector for both sentences ->
        # cosine similarity = 1.0.
        fake_embedder = MagicMock()
        fake_embedder.encode.return_value = np.array(
            [[1.0, 0.0, 0.0], [1.0, 0.0, 0.0]]
        )

        with patch.object(similarity, "get_sentence_embedder", return_value=fake_embedder):
            score = similarity.cosine_similarity_score("hello world", "hello world")

        assert score == pytest.approx(1.0)

    def test_orthogonal_vectors_score_zero(self):
        # Perpendicular vectors -> cosine similarity = 0.
        fake_embedder = MagicMock()
        fake_embedder.encode.return_value = np.array(
            [[1.0, 0.0], [0.0, 1.0]]
        )

        with patch.object(similarity, "get_sentence_embedder", return_value=fake_embedder):
            score = similarity.cosine_similarity_score("apple", "banana")

        assert score == pytest.approx(0.0, abs=1e-6)

    def test_returns_a_python_float(self):
        # We must NOT leak a numpy.float64 - downstream code uses Python
        # comparisons that may behave strangely with numpy types.
        fake_embedder = MagicMock()
        fake_embedder.encode.return_value = np.array([[1.0], [1.0]])

        with patch.object(similarity, "get_sentence_embedder", return_value=fake_embedder):
            score = similarity.cosine_similarity_score("a", "b")

        assert type(score) is float


# ----- llm_contextual_match dispatcher ----------------------------------


class TestLLMContextualMatchDispatcher:
    """Picks the right backend based on Settings.resolve_llm_provider()."""

    def test_dispatches_to_gemini_when_provider_is_gemini(self):
        fake_settings = SimpleNamespace(
            resolve_llm_provider=lambda: "gemini",
        )

        with patch.object(similarity, "get_settings", return_value=fake_settings), \
             patch.object(similarity, "_call_gemini", return_value=True) as gemini, \
             patch.object(similarity, "_call_anthropic") as anthropic:
            result = similarity.llm_contextual_match("a", "b")

        assert result is True
        gemini.assert_called_once()
        anthropic.assert_not_called()

    def test_dispatches_to_anthropic_when_provider_is_anthropic(self):
        fake_settings = SimpleNamespace(
            resolve_llm_provider=lambda: "anthropic",
        )

        with patch.object(similarity, "get_settings", return_value=fake_settings), \
             patch.object(similarity, "_call_gemini") as gemini, \
             patch.object(similarity, "_call_anthropic", return_value=False) as anthropic:
            result = similarity.llm_contextual_match("a", "b")

        assert result is False
        anthropic.assert_called_once()
        gemini.assert_not_called()

    def test_raises_runtime_error_when_no_provider_configured(self):
        fake_settings = SimpleNamespace(
            resolve_llm_provider=lambda: "none",
        )

        with patch.object(similarity, "get_settings", return_value=fake_settings):
            with pytest.raises(RuntimeError, match="No LLM provider"):
                similarity.llm_contextual_match("a", "b")

    def test_passes_both_headlines_into_prompt(self):
        # The prompt template must contain both inputs verbatim - this
        # guards against a regression where someone swaps the slot names.
        fake_settings = SimpleNamespace(
            resolve_llm_provider=lambda: "gemini",
        )
        captured = {}

        def fake_gemini(prompt, settings):
            captured["prompt"] = prompt
            return True

        with patch.object(similarity, "get_settings", return_value=fake_settings), \
             patch.object(similarity, "_call_gemini", side_effect=fake_gemini):
            similarity.llm_contextual_match("9 killed in fire", "19 killed in fire")

        assert "9 killed in fire" in captured["prompt"]
        assert "19 killed in fire" in captured["prompt"]
