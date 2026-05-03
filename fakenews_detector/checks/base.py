"""Base abstractions for validation checks."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class CheckResult:
    """Outcome of one validation check.

    Attributes
    ----------
    name:
        Human-readable check name (e.g. ``"clickbait"``).
    passed:
        True if the headline passed this gate (i.e. is "real-news-like").
    detail:
        Short message explaining the verdict, useful for UI / logs.
    metadata:
        Free-form extra info (similarity scores, misspelled words, ...).
    """

    name: str
    passed: bool
    detail: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class Check(ABC):
    """Interface every validation check must implement."""

    #: A short slug. Subclasses must set this.
    name: str = ""

    @abstractmethod
    def run(self, headline: str) -> CheckResult:
        """Run the check against `headline` and return a :class:`CheckResult`."""
