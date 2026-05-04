"""Thin Flask web UI on top of :mod:`fakenews_detector`.

This package is intentionally small. The ML/validation logic lives in
``fakenews_detector``; everything here is just HTTP plumbing,
templates, and a synchronous request handler that runs the validator
inline and renders the results page.
"""

from webapp.app import create_app

__all__ = ["create_app"]
