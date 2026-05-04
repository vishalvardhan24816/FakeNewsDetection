"""Entry point for the DebunkHub Flask web UI.

Usage
-----
::

    python run_webapp.py            # dev server on http://127.0.0.1:5000

Set ``FLASK_PORT`` and ``FLASK_HOST`` env vars to override.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import sys


def _force_utf8_stdio() -> None:
    """Make stdout/stderr UTF-8 so non-ASCII payloads never crash a
    write on Windows where the default console encoding is cp1252.
    """
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            pass


def _silence_stray_json_decode_print() -> None:
    """Some local Python installs have a stray ``print(s)`` injected at
    line 339 of ``json/decoder.py`` (likely from an old debugging
    session). On Windows, that print explodes with ``UnicodeEncodeError``
    when the JSON contains non-ASCII characters (e.g. the SentencePiece
    word-boundary marker ``\u2581`` in HuggingFace tokenizer JSONs),
    which kills the subjectivity check at model-load time.

    Wrap ``JSONDecoder.decode`` so any prints triggered during a decode
    are dropped into a throwaway buffer instead of touching real stdout.
    """
    original_decode = json.JSONDecoder.decode

    def safe_decode(self, s, *args, **kwargs):  # type: ignore[no-untyped-def]
        with contextlib.redirect_stdout(io.StringIO()):
            return original_decode(self, s, *args, **kwargs)

    json.JSONDecoder.decode = safe_decode  # type: ignore[assignment]


_force_utf8_stdio()
_silence_stray_json_decode_print()

from webapp import create_app  # noqa: E402  (import after stdio fixup)


def main() -> None:
    app = create_app()
    host = os.environ.get("FLASK_HOST", "127.0.0.1")
    port = int(os.environ.get("FLASK_PORT", "5000"))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host=host, port=port, debug=debug, threaded=True)


if __name__ == "__main__":
    main()
