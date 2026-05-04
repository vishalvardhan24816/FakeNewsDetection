"""Runs the 5 checks on a headline and returns a report.

Use it like this::

    from fakenews_detector import FakeNewsValidator

    report = FakeNewsValidator("Some headline").validate()
    print(report)            # human-readable summary
    if report.passed_all:
        print("Looks real")
"""

import logging

from fakenews_detector.checks import (
    CheckResult,
    ClickbaitCheck,
    NewsTitleCheck,
    SpellingCheck,
    SubjectivityCheck,
    WebPresenceCheck,
)

log = logging.getLogger(__name__)


# The 5 checks in the order we run them. Cheap ones first so we can
# short-circuit before the expensive web search.
DEFAULT_PIPELINE = [
    SpellingCheck,
    ClickbaitCheck,
    SubjectivityCheck,
    NewsTitleCheck,
    WebPresenceCheck,
]


class ValidationReport:
    """Holds the result of validating one headline."""

    def __init__(self, headline):
        self.headline = headline
        self.results = []         # list of CheckResult, in the order they ran
        self.passed_all = False   # set to True after validate() if every check passed
        self.first_failure = None # the first failing CheckResult, or None

    def __str__(self):
        verdict = "REAL" if self.passed_all else "FAKE / UNVERIFIED"
        lines = [f"Verdict: {verdict}", 
        f"Headline: {self.headline!r}",
         "Checks:"]
        for r in self.results:
            tick = "PASS" if r.passed else "FAIL"
            lines.append(f"  [{tick}] {r.name}: {r.detail}")
        return "\n".join(lines)



class FakeNewsValidator:
    """Runs the 5-step validation pipeline on one headline."""

    def __init__(self, headline, checks=None, stop_on_first_failure=True):
        """
        headline:
            Text to evaluate.
        checks:
            List of Check classes. Defaults to the 5 standard checks.
        stop_on_first_failure:
            Stop at the first FAIL (default True). Set to False to
            always run every check.
        """
        self.headline = headline
        self.stop_on_first_failure = stop_on_first_failure

        check_classes = checks if checks is not None else DEFAULT_PIPELINE
        # Build one instance of each check.
        self.checks = [cls() for cls in check_classes]

    def validate(self):
        """Run each check in order and return a ValidationReport."""
        report = ValidationReport(self.headline)

        for check in self.checks:
            log.info("Running check: %s", check.name)

            try:
                result = check.run(self.headline)
            except FileNotFoundError:
                # Missing model file = setup problem, not a content
                # problem. Let the caller see and handle it.
                raise
            except Exception as exc:
                # Any other crash inside a check counts as a fail so
                # one buggy check can't take down the whole pipeline.
                log.exception("Check %r crashed", check.name)
                result = CheckResult(
                    name=check.name,
                    passed=False,
                    detail=f"check crashed: {exc!r}",
                )

            report.results.append(result)

            # Remember the first failure so the UI can highlight it.
            if not result.passed and report.first_failure is None:
                report.first_failure = result

            # Optionally stop early on the first failure (default).
            if not result.passed and self.stop_on_first_failure:
                log.info("Stopping after failure at %r", check.name)
                break

        # Final verdict
        report.passed_all = (report.first_failure is None)
        return report
