"""Shared types used by every check.

There are two things here:

* `CheckResult` - a small "struct" describing the outcome of one check
  (did it pass? what was the message? any extra info?).

* `Check` - a tiny base class. Every check (Spelling, Clickbait, ...)
  inherits from it and implements `run(headline)`. It's not an ABC
  on purpose - just a plain class with one method to override.
"""

from dataclasses import dataclass, field


@dataclass
class CheckResult:
    """One check's verdict.

    name:
        Short label, e.g. "spelling".
    passed:
        True if the headline cleared this check.
    detail:
        Human-readable message, shown on the results page.
    metadata:
        Free-form extras (similarity scores, predicted labels, etc.).
    """
    name: str
    passed: bool
    detail: str = ""
    metadata: dict = field(default_factory=dict) # empty object of dict class


class Check:
    """Base class for every validation check.

    Subclasses set the `name` class attribute and implement `run()`.
    """

    name = ""

    def run(self, headline):
        """Run this check on `headline` and return a CheckResult."""
        raise NotImplementedError("Each Check subclass must implement run()")
