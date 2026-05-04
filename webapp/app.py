"""Flask app factory."""

from __future__ import annotations

import logging
import os

from flask import Flask

from fakenews_detector.logging_setup import configure_logging
from webapp.routes import ALL_CHECKS, bp

# (label, hint) for each check. Used by the results page to print
# friendly check names.
CHECK_LABELS: dict[str, tuple[str, str]] = {
    "spelling": ("Spelling", "NER-aware spell check"),
    "clickbait": ("Clickbait", "Trained classifier"),
    "subjectivity": ("Subjectivity", "Transformer model"),
    "news_title": ("News-title shape", "Trained classifier"),
    "web_presence": ("Web presence", "Search + LLM gate"),
}

log = logging.getLogger(__name__)


def create_app(*, testing: bool = False) -> Flask:
    """Build the Flask application."""
    configure_logging()

    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config["TESTING"] = testing
    app.config["BRAND_NAME"] = "DebunkHub"
    app.config["SECRET_KEY"] = os.environ.get(
        "FLASK_SECRET_KEY", "dev-only-not-secret"
    )

    app.register_blueprint(bp)

    @app.context_processor
    def inject_brand():
        return {
            "brand": app.config["BRAND_NAME"],
            "all_check_names": list(ALL_CHECKS),
            "check_labels": CHECK_LABELS,
        }

    log.info("DebunkHub Flask app initialised (testing=%s)", testing)
    return app
