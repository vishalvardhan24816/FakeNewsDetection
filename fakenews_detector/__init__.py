"""Fake News Detector.

A 5-step rule-based validator for news headlines:

    1. Spelling check        (NER + spellchecker)
    2. Clickbait check       (custom-trained classifier)
    3. Subjectivity check    (transformer)
    4. Is-news-title check   (custom-trained classifier)
    5. Web presence check    (Google + sentence similarity + Anthropic)

Public API
----------

    >>> from fakenews_detector import FakeNewsValidator
    >>> report = FakeNewsValidator("Modi visits ISRO headquarters").validate()
    >>> report.passed_all
    True
    >>> for r in report.results:
    ...     print(r.name, r.passed, r.detail)
"""

from fakenews_detector.checks.base import CheckResult
from fakenews_detector.validator import FakeNewsValidator, ValidationReport

__all__ = ["FakeNewsValidator", "ValidationReport", "CheckResult"]
__version__ = "1.0.0"
