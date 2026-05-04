"""Logging configuration.

Call `configure_logging()` once at startup. After that, any file can do::

    import logging
    log = logging.getLogger(__name__)
    log.info("hello")

...and the message will print to the terminal in a friendly format.
"""

import logging


def configure_logging(level=logging.INFO):
    """Tell Python's logging module to print to the terminal.

    `logging.basicConfig` does three things in one call: make the output written to terminal, attaches a formatter, and sets
    the level. It's a no-op if the root logger already has handlers,
    so calling this twice is safe.
    """
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-7s %(name)s :: %(message)s",
        datefmt="%H:%M:%S",
    )
