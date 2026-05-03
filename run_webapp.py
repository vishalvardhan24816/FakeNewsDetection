"""Entry point for the DebunkHub Flask web UI.

Usage
-----
::

    python run_webapp.py            # dev server on http://127.0.0.1:5000

Set ``FLASK_PORT`` and ``FLASK_HOST`` env vars to override.
"""

from __future__ import annotations

import os

from webapp import create_app


def main() -> None:
    app = create_app()
    host = os.environ.get("FLASK_HOST", "127.0.0.1")
    port = int(os.environ.get("FLASK_PORT", "5000"))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host=host, port=port, debug=debug, threaded=True)


if __name__ == "__main__":
    main()
