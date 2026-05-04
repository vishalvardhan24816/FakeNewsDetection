"""Tests for `fakenews_detector.config`.

We mostly care about `Settings.resolve_llm_provider()` because every
other field is a constant or a direct env-var read. We also assert the
defaults haven't drifted, so a typo'd env var doesn't silently change
behavior.
"""

import os
from unittest.mock import patch

import pytest

from fakenews_detector.config import Settings


# ----- defaults ---------------------------------------------------------


class TestSettingsDefaults:
    """A fresh Settings() should have sensible defaults baked in."""

    def test_default_search_provider_is_ddg(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("SEARCH_PROVIDER", None)
            s = Settings()
            assert s.search_provider == "ddg"

    def test_default_thresholds_are_reasonable(self):
        s = Settings()
        # If anyone changes these, an interview-prep dry run might break.
        # Lock them down.
        assert 0.0 < s.spelling_max_misspell_ratio <= 1.0
        assert s.web_presence_min_results >= 1
        assert s.web_presence_min_similar >= 1
        assert 0.0 <= s.web_presence_similarity_threshold <= 1.0

    def test_default_llm_provider_is_auto(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("LLM_PROVIDER", None)
            s = Settings()
            assert s.llm_provider == "auto"


# ----- resolve_llm_provider --------------------------------------------


class TestResolveLLMProvider:
    """The provider-selection logic. Auto picks Gemini when both are set."""

    def test_auto_picks_gemini_when_only_gemini_key_set(self):
        s = Settings()
        s.llm_provider = "auto"
        s.gemini_api_key = "fake-gem"
        s.anthropic_api_key = ""
        assert s.resolve_llm_provider() == "gemini"

    def test_auto_picks_anthropic_when_only_anthropic_key_set(self):
        s = Settings()
        s.llm_provider = "auto"
        s.gemini_api_key = ""
        s.anthropic_api_key = "fake-anth"
        assert s.resolve_llm_provider() == "anthropic"

    def test_auto_prefers_gemini_when_both_keys_set(self):
        # Documented: Gemini wins because of generous free tier.
        s = Settings()
        s.llm_provider = "auto"
        s.gemini_api_key = "fake-gem"
        s.anthropic_api_key = "fake-anth"
        assert s.resolve_llm_provider() == "gemini"

    def test_auto_returns_none_when_no_keys_set(self):
        s = Settings()
        s.llm_provider = "auto"
        s.gemini_api_key = ""
        s.anthropic_api_key = ""
        assert s.resolve_llm_provider() == "none"

    def test_explicit_provider_overrides_auto_logic(self):
        # Even with only a Gemini key, if the user forced "anthropic"
        # we return "anthropic" and let the call fail downstream with
        # a clear error.
        s = Settings()
        s.llm_provider = "anthropic"
        s.gemini_api_key = "fake-gem"
        s.anthropic_api_key = ""
        assert s.resolve_llm_provider() == "anthropic"


# ----- env var integration ---------------------------------------------


class TestEnvVarOverrides:
    """Confirm the env-var names we document actually take effect."""

    def test_search_provider_env_overrides_default(self):
        with patch.dict(os.environ, {"SEARCH_PROVIDER": "google"}):
            assert Settings().search_provider == "google"

    def test_search_provider_is_lowercased(self):
        with patch.dict(os.environ, {"SEARCH_PROVIDER": "GOOGLE"}):
            assert Settings().search_provider == "google"

    def test_anthropic_model_env_overrides_default(self):
        with patch.dict(os.environ, {"ANTHROPIC_MODEL": "claude-test-model"}):
            assert Settings().anthropic_model == "claude-test-model"

    def test_gemini_api_key_falls_back_through_aliases(self):
        # We accept GOOGLE_GEMINI_API_KEY, GEMINI_API_KEY, GOOGLE_API_KEY
        # in that order. Make sure the fallback chain works.
        with patch.dict(
            os.environ,
            {"GOOGLE_GEMINI_API_KEY": "", "GEMINI_API_KEY": "", "GOOGLE_API_KEY": "z"},
            clear=False,
        ):
            assert Settings().gemini_api_key == "z"
