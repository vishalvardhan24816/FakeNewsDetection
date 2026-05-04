"""Shared pytest fixtures for the whole test suite.

This file is auto-loaded by pytest -- you do NOT have to import it.
Anything we define here as a `@pytest.fixture` is available by name in
every test under `tests/`.

Design rule: tests should never load the real ML models. They are slow
(seconds each) and require gigabytes of disk artifacts. Every fixture
here returns a small fake stand-in that behaves like the real thing.
"""

import pytest

from fakenews_detector.checks.base import Check, CheckResult


@pytest.fixture
def make_fake_check():
    """Build a Check subclass that returns a pre-decided verdict.

    Usage in a test::

        passing = make_fake_check("spelling", passed=True)
        failing = make_fake_check("clickbait", passed=False, detail="oops")

    Each call returns a *class*, not an instance, because that's what
    `FakeNewsValidator(checks=[...])` expects.
    """

    def _factory(name, passed=True, detail="", metadata=None, raises=None):
        meta = metadata or {}

        class _FakeCheck(Check):
            pass

        _FakeCheck.name = name

        def run(self, headline):
            if raises is not None:
                raise raises
            return CheckResult(
                name=name, passed=passed, detail=detail, metadata=dict(meta)
            )

        _FakeCheck.run = run
        # Give the class a unique __name__ so test failures are readable.
        _FakeCheck.__name__ = f"FakeCheck_{name}"
        return _FakeCheck

    return _factory
