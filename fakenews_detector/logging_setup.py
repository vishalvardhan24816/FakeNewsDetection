"""Project-wide logging configuration.

Call :func:`configure_logging` once at process start (e.g. in the script
that uses the validator). Library code itself just calls
``logging.getLogger(__name__)``.
"""

from __future__ import annotations

import logging


def configure_logging(level: int = logging.INFO) -> None:
    """Configure the root logger with a sensible default format.

    Idempotent: calling it twice will not stack handlers.
    """
    root = logging.getLogger()
    if getattr(root, "_fakenews_configured", False):
        root.setLevel(level)
        return

    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s %(levelname)-7s %(name)s :: %(message)s",
            datefmt="%H:%M:%S",
        )
    )
    root.addHandler(handler)
    root.setLevel(level)
    root._fakenews_configured = True  # type: ignore[attr-defined]
