"""Thin Flask web UI on top of `fakenews_detector`.

This package is intentionally small. The real ML / validation logic
lives in `fakenews_detector`. Everything here is just HTTP plumbing:
a Flask app factory, three routes, and the Jinja templates that
render them.
"""

from webapp.app import create_app

__all__ = ["create_app"]
