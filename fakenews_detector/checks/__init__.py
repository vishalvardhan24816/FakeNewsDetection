"""The 5 individual validation checks.

Each check is a class that inherits from :class:`Check` and implements
``run(headline) -> CheckResult``. The orchestrator
(:class:`fakenews_detector.validator.FakeNewsValidator`) runs them in
sequence and short-circuits on the first failure.
"""

from fakenews_detector.checks.base import Check, CheckResult
from fakenews_detector.checks.clickbait import ClickbaitCheck
from fakenews_detector.checks.news_title import NewsTitleCheck
from fakenews_detector.checks.spelling import SpellingCheck
from fakenews_detector.checks.subjectivity import SubjectivityCheck
from fakenews_detector.checks.web_presence import WebPresenceCheck

__all__ = [
    "Check",
    "CheckResult",
    "SpellingCheck",
    "ClickbaitCheck",
    "SubjectivityCheck",
    "NewsTitleCheck",
    "WebPresenceCheck",
]
