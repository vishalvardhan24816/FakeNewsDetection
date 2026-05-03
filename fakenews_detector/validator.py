"""Top-level orchestrator.

Run all 5 checks in order on a single headline. By default, validation
short-circuits on the first failure (matching the behavior of the
original system); pass ``stop_on_first_failure=False`` to run every
check unconditionally and inspect the full report.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional, Sequence

from fakenews_detector.checks import (
    Check,
    CheckResult,
    ClickbaitCheck,
    NewsTitleCheck,
    SpellingCheck,
    SubjectivityCheck,
    WebPresenceCheck,
)

log = logging.getLogger(__name__)


@dataclass
class ValidationReport:
    """Aggregate result of running the validator on one headline."""

    headline: str
    results: List[CheckResult] = field(default_factory=list)

    @property
    def passed_all(self) -> bool:
        return bool(self.results) and all(r.passed for r in self.results)

    @property
    def first_failure(self) -> Optional[CheckResult]:
        return next((r for r in self.results if not r.passed), None)

    def __str__(self) -> str:
        verdict = "REAL" if self.passed_all else "FAKE / UNVERIFIED"
        lines = [f"Verdict: {verdict}", f"Headline: {self.headline!r}", "Checks:"]
        for r in self.results:
            tick = "PASS" if r.passed else "FAIL"
            lines.append(f"  [{tick}] {r.name}: {r.detail}")
        return "\n".join(lines)


_DEFAULT_PIPELINE: Sequence[type[Check]] = (
    SpellingCheck,
    ClickbaitCheck,
    SubjectivityCheck,
    NewsTitleCheck,
    WebPresenceCheck,
)


class FakeNewsValidator:
    """Run the 5-step validation pipeline on a headline.

    Parameters
    ----------
    headline:
        The text to evaluate.
    checks:
        Optional override of the check pipeline (list of ``Check``
        subclasses or instances). Defaults to the standard 5-step suite.
    stop_on_first_failure:
        If True (default), validation stops as soon as a check fails.
        Set to False to always run every check.
    """

    def __init__(
        self,
        headline: str,
        *,
        checks: Optional[Sequence] = None,
        stop_on_first_failure: bool = True,
    ) -> None:
        self.headline = headline
        self._stop_on_first_failure = stop_on_first_failure
        self._checks = [
            check_cls() if isinstance(check_cls, type) else check_cls
            for check_cls in (checks if checks is not None else _DEFAULT_PIPELINE)
        ]

    def validate(self) -> ValidationReport:
        report = ValidationReport(headline=self.headline)
        for check in self._checks:
            log.info("Running check: %s", check.name)
            try:
                result = check.run(self.headline)
            except FileNotFoundError:
                # Missing model file is a setup error, not a check failure -
                # surface it loudly.
                raise
            except Exception as exc:
                log.exception("Check %r crashed; recording as failure", check.name)
                result = CheckResult(
                    name=check.name,
                    passed=False,
                    detail=f"check crashed: {exc!r}",
                )
            report.results.append(result)
            if not result.passed and self._stop_on_first_failure:
                log.info(
                    "Short-circuiting after first failure at %r", check.name
                )
                break
        return report
