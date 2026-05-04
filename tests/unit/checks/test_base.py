"""Tests for `fakenews_detector.checks.base`.

Just the shared types: `CheckResult` (the verdict struct) and `Check`
(the tiny base class every check inherits from).
"""

import pytest

from fakenews_detector.checks.base import Check, CheckResult


# ----- CheckResult ------------------------------------------------------


class TestCheckResult:
    """The `CheckResult` dataclass: required + optional fields."""

    def test_required_fields(self):
        r = CheckResult(name="x", passed=True)
        assert r.name == "x"
        assert r.passed is True
        # Optional fields default to empty.
        assert r.detail == ""
        assert r.metadata == {}

    def test_optional_fields(self):
        r = CheckResult(
            name="x", passed=False, detail="oops", metadata={"score": 0.4}
        )
        assert r.detail == "oops"
        assert r.metadata == {"score": 0.4}

    def test_metadata_default_is_independent_per_instance(self):
        # Classic dataclass gotcha: a mutable default like `{}` would be
        # shared across all instances. `default_factory=dict` avoids it.
        a = CheckResult(name="a", passed=True)
        b = CheckResult(name="b", passed=True)
        a.metadata["k"] = 1
        assert "k" not in b.metadata


# ----- Check ------------------------------------------------------------


class TestCheckBase:
    """Subclasses MUST implement `run()` -- otherwise NotImplementedError."""

    def test_default_run_raises_not_implemented(self):
        check = Check()
        with pytest.raises(NotImplementedError):
            check.run("any headline")

    def test_subclass_overriding_run_works(self):
        class MyCheck(Check):
            name = "demo"

            def run(self, headline):
                return CheckResult(name=self.name, passed=True, detail=headline)

        out = MyCheck().run("hi")
        assert out.name == "demo"
        assert out.detail == "hi"
