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


@dataclass(frozen=True)
class Settings:
    """All tunable knobs for the validator in one place."""

    # ----- Local model directories (Hugging Face snapshots on disk) -----
    ner_model_dir: Path = PROJECT_ROOT / "dbmbz"
    subjectivity_model_dir: Path = PROJECT_ROOT / "lighteternal"
    sentence_embedding_model_dir: Path = PROJECT_ROOT / "basenlimean"

    # ----- Custom-trained classifiers / vectorizers -----
    clickbait_model_path: Path = PROJECT_ROOT / "mlmodels" / "impclickbait.pkl"
    clickbait_vectorizer_path: Path = PROJECT_ROOT / "vectorizers" / "vectorizer.pkl"
    news_title_model_path: Path = PROJECT_ROOT / "mlmodels" / "wewill.pkl"
    news_title_vectorizer_path: Path = PROJECT_ROOT / "vectorizers" / "wevec.pkl"

    # ----- 5th-check thresholds -----
    spelling_max_misspell_ratio: float = 0.5
    web_presence_min_results: int = 3
    web_presence_min_similar: int = 2
    web_presence_similarity_threshold: float = 0.50
    web_presence_request_timeout_s: int = 4

    # ----- LLM verifier (Anthropic) -----
    anthropic_api_key: str = field(
        default_factory=lambda: os.environ.get("ANTHROPIC_API_KEY", "")
    )
    anthropic_model: str = field(
        default_factory=lambda: os.environ.get(
            "ANTHROPIC_MODEL", "claude-3-opus-20240229"
        )
    )

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
