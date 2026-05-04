"""Entry point for the DebunkHub Flask web UI.

Run it like this::

    python run_webapp.py            # http://127.0.0.1:5000

Override host/port via env vars: FLASK_HOST, FLASK_PORT.
"""

import os

# Importing the webapp transitively triggers the model loaders, which
# in turn read JSON tokenizer files. The patch above MUST be applied
# before that import, so it lives at the very top of this file.
from webapp import create_app  # noqa: E402


def main():
    app = create_app()
    host = os.environ.get("FLASK_HOST", "127.0.0.1")
    port = int(os.environ.get("FLASK_PORT", "5000"))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    main()
