"""Project configuration.

Reads everything from environment variables (loaded from `.env` if present)
and from a few hard-coded defaults. There's only one Settings instance
per process, exposed via :func:`get_settings`.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load the .env file at the project root the first time this module is
# imported. If there's no .env, this is a no-op.
load_dotenv()


# Project root = the folder that contains the `fakenews_detector/` package.
# We compute it from this file's path so it works regardless of where you
# `cd` from before running the app.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS_ROOT = PROJECT_ROOT / "artifacts"
HF_MODELS_ROOT = ARTIFACTS_ROOT / "hf_models"
CLASSIFIERS_ROOT = ARTIFACTS_ROOT / "classifiers"
VECTORIZERS_ROOT = ARTIFACTS_ROOT / "vectorizers"


class Settings:
    """All tunable knobs in one place. Built once at startup."""

    def __init__(self):
        # ----- Where each ML model lives on disk -----
        # These are downloaded artifacts; see README for how to obtain them.
        self.ner_model_dir = HF_MODELS_ROOT / "ner"
        self.subjectivity_model_dir = HF_MODELS_ROOT / "subjectivity"
        self.sentence_embedder_dir = HF_MODELS_ROOT / "sentence_embedder"

        self.clickbait_classifier_path = CLASSIFIERS_ROOT / "clickbait_classifier.pkl"
        self.clickbait_vectorizer_path = VECTORIZERS_ROOT / "clickbait_vectorizer.pkl"
        self.news_title_classifier_path = CLASSIFIERS_ROOT / "news_title_classifier.pkl"
        self.news_title_vectorizer_path = VECTORIZERS_ROOT / "news_title_vectorizer.pkl"

        # ----- Thresholds for the rule-based parts of each check -----
        # Spelling check: fail if more than this fraction of words are misspelled.
        self.spelling_max_misspell_ratio = 0.5
        # Web-presence check: how many trusted search hits we need.
        self.web_presence_min_results = 3
        # ...and how many of them must clear the cosine-similarity bar.
        self.web_presence_min_similar = 2
        self.web_presence_similarity_threshold = 0.50
        self.web_presence_request_timeout_s = 4

        # ----- Which search engine the web-presence check uses -----
        # "ddg"    -> DuckDuckGo (default, no API key, very stable)
        # "google" -> Google web search + per-domain news verification
        #             (matches the original 2023 design; may get rate-limited)
        self.search_provider = os.environ.get("SEARCH_PROVIDER", "ddg").lower()

        # ----- LLM (used as the final yes/no gate inside web_presence) -----
        # We support either Google Gemini OR Anthropic Claude. Whichever
        # API key is set wins; if both are set, Gemini is preferred.
        # You can force a specific provider via LLM_PROVIDER=gemini|anthropic.
        self.gemini_api_key = (
            os.environ.get("GOOGLE_GEMINI_API_KEY", "")
            or os.environ.get("GEMINI_API_KEY", "")
            or os.environ.get("GOOGLE_API_KEY", "")
        )
        self.gemini_model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
        self.anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        self.anthropic_model = os.environ.get(
            "ANTHROPIC_MODEL", "claude-3-5-haiku-20241022"
        )
        self.llm_provider = os.environ.get("LLM_PROVIDER", "auto").lower()

        # ----- HTTP -----
        # User-agent header used when scraping search engines.
        self.user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )

    def resolve_llm_provider(self):
        """Decide which LLM provider will actually be used.

        Returns one of: "gemini", "anthropic", or "none".
        """
        if self.llm_provider == "auto":
            if self.gemini_api_key:
                return "gemini"
            if self.anthropic_api_key:
                return "anthropic"
            return "none"
        return self.llm_provider



# Build the one Settings object right here at import time. Every other
# file just calls `get_settings()` to reach it.
SETTINGS = Settings()


def get_settings():
    """Return the shared Settings instance."""
    return SETTINGS
