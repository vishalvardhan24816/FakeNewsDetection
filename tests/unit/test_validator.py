"""Tests for `fakenews_detector.validator`.

The validator is just an orchestrator over Check classes. We test it
with `make_fake_check` (defined in tests/conftest.py) so we don't need
to load any real models -- each fake check returns a hardcoded verdict.
"""

import pytest

from fakenews_detector.checks.base import CheckResult
from fakenews_detector.validator import FakeNewsValidator, ValidationReport


# ----- ValidationReport ------------------------------------------------


class TestValidationReport:
    """The dumb data container the validator fills in."""

    def test_initial_state(self):
        r = ValidationReport("some headline")
        assert r.headline == "some headline"
        assert r.results == []
        assert r.passed_all is False
        assert r.first_failure is None

    def test_str_includes_verdict_and_each_check(self):
        r = ValidationReport("hi")
        r.results = [
            CheckResult(name="a", passed=True, detail="ok"),
            CheckResult(name="b", passed=False, detail="bad"),
        ]
        text = str(r)
        assert "Verdict" in text
        assert "Headline" in text
        assert "[PASS] a" in text
        assert "[FAIL] b" in text


# ----- FakeNewsValidator orchestration ---------------------------------


class TestFakeNewsValidatorHappyPath:
    """All checks pass -> overall passed_all=True."""

    def test_runs_every_check_when_all_pass(self, make_fake_check):
        validator = FakeNewsValidator(
            "headline",
            checks=[
                make_fake_check("one", passed=True),
                make_fake_check("two", passed=True),
                make_fake_check("three", passed=True),
            ],
        )
        report = validator.validate()

        assert report.passed_all is True
        assert report.first_failure is None
        assert len(report.results) == 3
        assert [r.name for r in report.results] == ["one", "two", "three"]


class TestFakeNewsValidatorEarlyStop:
    """Default behavior: stop at the first failing check."""

    def test_stops_at_first_failure(self, make_fake_check):
        validator = FakeNewsValidator(
            "headline",
            checks=[
                make_fake_check("one", passed=True),
                make_fake_check("two", passed=False, detail="bad"),
                make_fake_check("three", passed=True),  # never runs
            ],
        )
        report = validator.validate()

        assert report.passed_all is False
        assert report.first_failure is not None
        assert report.first_failure.name == "two"
        assert report.first_failure.detail == "bad"
        # "three" should NOT have been executed.
        assert [r.name for r in report.results] == ["one", "two"]

    def test_continues_when_stop_on_first_failure_is_disabled(self, make_fake_check):
        validator = FakeNewsValidator(
            "headline",
            checks=[
                make_fake_check("one", passed=True),
                make_fake_check("two", passed=False),
                make_fake_check("three", passed=True),
                make_fake_check("four", passed=False),
            ],
            stop_on_first_failure=False,
        )
        report = validator.validate()

        # Every check runs even after a failure.
        assert [r.name for r in report.results] == ["one", "two", "three", "four"]
        # first_failure still tracks the earliest fail.
        assert report.first_failure.name == "two"


class TestFakeNewsValidatorErrorHandling:
    """A buggy check shouldn't take down the whole validation pipeline."""

    def test_check_that_crashes_is_recorded_as_failure(self, make_fake_check):
        validator = FakeNewsValidator(
            "headline",
            checks=[
                make_fake_check("crashy", raises=RuntimeError("kaboom")),
            ],
        )
        report = validator.validate()

        assert report.passed_all is False
        assert len(report.results) == 1
        assert report.results[0].passed is False
        assert "kaboom" in report.results[0].detail

    def test_file_not_found_propagates(self, make_fake_check):
        # Missing model = setup problem, not a content problem. We let
        # the caller see and handle it (e.g. show a setup error in UI).
        validator = FakeNewsValidator(
            "headline",
            checks=[
                make_fake_check(
                    "missing_model", raises=FileNotFoundError("no model.pkl")
                ),
            ],
        )
        with pytest.raises(FileNotFoundError):
            validator.validate()


class TestFakeNewsValidatorDefaults:
    """If you don't pass `checks=...`, you get the standard 5-check pipeline."""

    def test_default_pipeline_has_five_checks(self):
        validator = FakeNewsValidator("headline")
        # We don't run them (would load real models). We just assert the
        # default wiring is what the README and webapp expect.
        names = [c.name for c in validator.checks]
        assert names == [
            "spelling",
            "clickbait",
            "subjectivity",
            "news_title",
            "web_presence",
        ]
