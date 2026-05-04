"""Centralised configuration.

Reads values from a `.env` file (if present) and from the process
environment. All paths default to locations under the project root.
Override anything by setting the corresponding env var or by passing
`Settings()` arguments explicitly.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

# Load .env once on import. Silent no-op if the file is missing.
load_dotenv()

PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
ARTIFACTS_ROOT: Path = PROJECT_ROOT / "artifacts"
HF_MODELS_ROOT: Path = ARTIFACTS_ROOT / "hf_models"
CLASSIFIERS_ROOT: Path = ARTIFACTS_ROOT / "classifiers"
VECTORIZERS_ROOT: Path = ARTIFACTS_ROOT / "vectorizers"


@dataclass(frozen=True)
class Settings:
    """All tunable knobs for the validator in one place."""

    # ----- Local model directories (Hugging Face snapshots on disk) -----
    ner_model_dir: Path = HF_MODELS_ROOT / "dbmbz"
    subjectivity_model_dir: Path = HF_MODELS_ROOT / "lighteternal"
    sentence_embedding_model_dir: Path = HF_MODELS_ROOT / "basenlimean"

    # ----- Custom-trained classifiers / vectorizers -----
    clickbait_model_path: Path = CLASSIFIERS_ROOT / "impclickbait.pkl"
    clickbait_vectorizer_path: Path = VECTORIZERS_ROOT / "vectorizer.pkl"
    news_title_model_path: Path = CLASSIFIERS_ROOT / "wewill.pkl"
    news_title_vectorizer_path: Path = VECTORIZERS_ROOT / "wevec.pkl"

    # ----- 5th-check thresholds -----
    spelling_max_misspell_ratio: float = 0.5
    web_presence_min_results: int = 3
    web_presence_min_similar: int = 2
    web_presence_similarity_threshold: float = 0.50
    web_presence_request_timeout_s: int = 4

    # SERP backend for the web-presence check. "ddg" uses DuckDuckGo's
    # news vertical (no API key, reliable). "google" uses Google's web
    # search via direct HTML scraping (matches original 3-year-old
    # behavior, but Google may serve a JS-shell page depending on IP /
    # headers, in which case the check returns 0 candidates). Set
    # SEARCH_PROVIDER=google in .env to use Google.
    search_provider: str = field(
        default_factory=lambda: os.environ.get("SEARCH_PROVIDER", "ddg").lower()
    )

    # ----- LLM verifier (provider-agnostic) -----
    # The web-presence check needs an LLM as a final yes/no gate. We support
    # either Google Gemini or Anthropic Claude. Provider is auto-detected
    # from whichever API key is set, but can be forced via LLM_PROVIDER.
    gemini_api_key: str = field(
        default_factory=lambda: os.environ.get("GOOGLE_GEMINI_API_KEY", "")
        or os.environ.get("GEMINI_API_KEY", "")
        or os.environ.get("GOOGLE_API_KEY", "")
    )
    gemini_model: str = field(
        default_factory=lambda: os.environ.get("GEMINI_MODEL", "gemini-3-flash-preview")
    )
    anthropic_api_key: str = field(
        default_factory=lambda: os.environ.get("ANTHROPIC_API_KEY", "")
    )
    anthropic_model: str = field(
        default_factory=lambda: os.environ.get(
            "ANTHROPIC_MODEL", "claude-3-5-haiku-20241022"
        )
    )
    # "auto" picks gemini > anthropic > error. Explicit values:
    # "gemini" | "anthropic" | "none" (none = always fail the LLM gate).
    llm_provider: str = field(
        default_factory=lambda: os.environ.get("LLM_PROVIDER", "auto").lower()
    )

    def resolve_llm_provider(self) -> str:
        """Return the provider that will actually be used for the LLM gate."""
        if self.llm_provider == "auto":
            if self.gemini_api_key:
                return "gemini"
            if self.anthropic_api_key:
                return "anthropic"
            return "none"
        return self.llm_provider

    # ----- HTTP -----
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide singleton Settings object."""
    return Settings()
