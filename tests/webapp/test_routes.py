"""Tests for `webapp.routes`.

We exercise every HTTP route via the Flask test client. For POST
/detect we patch `FakeNewsValidator` so the test never loads ML
models or makes network calls.
"""

from unittest.mock import MagicMock, patch

import pytest

from fakenews_detector.checks.base import CheckResult
from fakenews_detector.validator import ValidationReport


def _fake_report(headline, passed_all=True, results=None):
    """Build a ValidationReport mimicking what the real validator returns."""
    report = ValidationReport(headline)
    report.results = results or [
        CheckResult(name="spelling", passed=True, detail="ok"),
        CheckResult(name="clickbait", passed=True, detail="ok"),
    ]
    report.passed_all = passed_all
    report.first_failure = next(
        (r for r in report.results if not r.passed), None
    )
    return report


# ----- GET routes ------------------------------------------------------


class TestGETRoutes:
    """Static-ish pages should render with HTTP 200."""

    def test_index_renders(self, client):
        response = client.get("/")
        assert response.status_code == 200

    def test_about_renders(self, client):
        response = client.get("/about")
        assert response.status_code == 200

    def test_detect_form_renders(self, client):
        response = client.get("/detect")
        assert response.status_code == 200
        # The form must include the headline textarea.
        assert b'name="headline"' in response.data

    def test_unknown_route_returns_custom_404(self, client):
        response = client.get("/this-does-not-exist")
        assert response.status_code == 404
        # We render error.html which says "Page not found".
        assert b"Page not found" in response.data


# ----- POST /detect happy path -----------------------------------------


class TestPostDetect:
    """Submitting a headline runs the validator and renders results."""

    def test_renders_results_on_successful_validation(self, client):
        fake_validator = MagicMock()
        fake_validator.validate.return_value = _fake_report(
            "ISRO launches Chandrayaan-3", passed_all=True
        )

        with patch(
            "webapp.routes.FakeNewsValidator", return_value=fake_validator
        ):
            response = client.post(
                "/detect",
                data={
                    "headline": "ISRO launches Chandrayaan-3",
                    "checks_submitted": "1",
                    "check_spelling": "1",
                    "check_clickbait": "1",
                },
            )

        assert response.status_code == 200
        # Results page renders the headline and the verdict banner.
        assert b"ISRO launches Chandrayaan-3" in response.data
        assert b"Looks real" in response.data

    def test_renders_failure_verdict_when_a_check_fails(self, client):
        fake_validator = MagicMock()
        fake_validator.validate.return_value = _fake_report(
            "blah",
            passed_all=False,
            results=[
                CheckResult(name="spelling", passed=False, detail="too many typos"),
            ],
        )

        with patch(
            "webapp.routes.FakeNewsValidator", return_value=fake_validator
        ):
            response = client.post(
                "/detect",
                data={
                    "headline": "blah",
                    "checks_submitted": "1",
                    "check_spelling": "1",
                },
            )

        assert response.status_code == 200
        assert b"Looks fake" in response.data or b"unverified" in response.data


# ----- POST /detect error paths ----------------------------------------


class TestPostDetectErrors:
    """Validation should never crash the page; errors render inline."""

    def test_empty_headline_renders_form_with_error(self, client):
        response = client.post(
            "/detect",
            data={"headline": "   ", "checks_submitted": "1", "check_spelling": "1"},
        )
        assert response.status_code == 200
        # The form re-renders with an alert.
        assert b"Please enter a headline" in response.data

    def test_missing_model_artifact_renders_setup_error(self, client):
        # Simulate a setup error -- a model .pkl is missing on disk.
        fake_validator = MagicMock()
        fake_validator.validate.side_effect = FileNotFoundError(
            "missing artifacts/classifiers/clickbait_classifier.pkl"
        )

        with patch(
            "webapp.routes.FakeNewsValidator", return_value=fake_validator
        ):
            response = client.post(
                "/detect",
                data={
                    "headline": "anything",
                    "checks_submitted": "1",
                    "check_spelling": "1",
                },
            )

        assert response.status_code == 200
        assert b"Setup error" in response.data


# ----- _selected_checks_from_form helper -------------------------------


class TestSelectedChecksHelper:
    """The form helper that decides which checks to run."""

    def test_form_without_marker_defaults_to_all_checks(self):
        from webapp.routes import ALL_CHECKS, _selected_checks_from_form

        # No `checks_submitted` marker = "this isn't from our form, so
        # default to running everything".
        result = _selected_checks_from_form({})
        assert result == list(ALL_CHECKS)

    def test_only_ticked_checks_are_returned(self):
        from webapp.routes import _selected_checks_from_form

        form = {
            "checks_submitted": "1",
            "check_spelling": "1",
            "check_clickbait": "1",
            # other checks omitted = unticked
        }
        result = _selected_checks_from_form(form)
        assert result == ["spelling", "clickbait"]

    def test_marker_with_no_ticked_boxes_returns_empty(self):
        from webapp.routes import _selected_checks_from_form

        # User unticked every box. Helper returns empty so the route
        # can show an error.
        result = _selected_checks_from_form({"checks_submitted": "1"})
        assert result == []
