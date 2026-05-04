"""Fake News Detector.

A 5-step rule-based validator for news headlines:

    1. Spelling          (NER-aware spell check)
    2. Clickbait         (custom-trained classifier)
    3. Subjectivity      (Hugging Face transformer)
    4. News-title shape  (custom-trained classifier)
    5. Web presence      (search + sentence similarity + LLM)

Quick usage::

    from fakenews_detector import FakeNewsValidator
    report = FakeNewsValidator("Some headline").validate()
    if report.passed_all:
        print("Looks real")
"""

from fakenews_detector.validator import FakeNewsValidator, ValidationReport

__all__ = ["FakeNewsValidator", "ValidationReport"]
