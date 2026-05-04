"""Flask application factory.

`create_app()` builds and returns a fully-wired Flask app object.
That's the only thing this file exports; `run_webapp.py` calls it
once at startup and then asks Flask to start serving HTTP.
"""

import logging
import os

from flask import Flask

from fakenews_detector.logging_setup import configure_logging
from webapp.routes import ALL_CHECKS, register_routes

# Brand name shown in the page title, header, and footer.
BRAND_NAME = "DebunkHub"

# (title, subtitle) shown next to each check in the UI.
CHECK_LABELS = {
    "spelling":     ("Spelling",         "NER-aware spell check"),
    "clickbait":    ("Clickbait",        "Trained classifier"),
    "subjectivity": ("Subjectivity",     "Transformer model"),
    "news_title":   ("News-title shape", "Trained classifier"),
    "web_presence": ("Web presence",     "Search + LLM gate"),
}

log = logging.getLogger(__name__)


def create_app():
    """Build the Flask app and register routes."""
    configure_logging()

    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config["SECRET_KEY"] = os.environ.get(
        "FLASK_SECRET_KEY", "dev-only-not-secret"
    )

    # Attach all the URL routes defined in webapp/routes.py.
    register_routes(app)

    # Variables injected into every Jinja template, so we don't have
    # to pass them on every render_template() call.
    @app.context_processor
    def inject_globals():
        return {
            "brand": BRAND_NAME,
            "all_check_names": list(ALL_CHECKS),
            "check_labels": CHECK_LABELS,
        }

    log.info("Flask app initialised")
    return app
