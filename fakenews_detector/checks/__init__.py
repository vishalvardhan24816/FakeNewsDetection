"""The 5 individual validation checks.

Every check is a small class with one method, `run(headline)`, that
returns a `CheckResult`. The orchestrator (`FakeNewsValidator`) runs
them one after another and stops at the first failure.
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
