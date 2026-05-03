"""Thin Flask web UI on top of :mod:`fakenews_detector`.

This package is intentionally small. The ML/validation logic lives in
``fakenews_detector``; everything here is just HTTP plumbing,
templates, and a tiny in-memory job registry so the browser can poll
for real progress while a validation runs in a background thread.
"""

from webapp.app import create_app

__all__ = ["create_app"]
