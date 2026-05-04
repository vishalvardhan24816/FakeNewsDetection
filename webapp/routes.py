"""HTTP routes for the DebunkHub web UI.

Synchronous design (matches the original 3-year-old code):

    GET  /detect    -> render the form
    POST /detect    -> run the validator inline, render the results

There's no background worker, no polling, no job IDs. The browser tab
just blocks while Flask runs the checks. Simple, fewer moving parts,
easier to explain.

We attach all routes by calling ``register_routes(app)`` from
``webapp/app.py``. One function, one place where URLs map to handlers.
"""

import logging
import os
import time

from flask import render_template, request

from fakenews_detector.checks import (
    ClickbaitCheck,
    NewsTitleCheck,
    SpellingCheck,
    SubjectivityCheck,
    WebPresenceCheck,
)
from fakenews_detector.validator import FakeNewsValidator

log = logging.getLogger(__name__)


# Form field name -> Check class. Order matters: cheap checks first so
# the validator can short-circuit before the expensive web search.
ALL_CHECKS = {
    "spelling": SpellingCheck,
    "clickbait": ClickbaitCheck,
    "subjectivity": SubjectivityCheck,
    "news_title": NewsTitleCheck,
    "web_presence": WebPresenceCheck,
}


# Minimum response time for /detect (seconds). Real validation can
# finish in well under a second when an early check fails fast - that
# would make the in-flight pipeline animation barely flash and confuse
# the user. We pad fast responses so the animation always plays through
# at least the first few steps. Set DETECT_MIN_RESPONSE_S=0 to disable.
_MIN_RESPONSE_S = float(os.environ.get("DETECT_MIN_RESPONSE_S", "5.0"))


def _selected_checks_from_form(form):
    """Read which checks the user enabled.

    The form always submits a hidden ``checks_submitted=1`` marker so we
    can tell "form had no checkboxes at all" (default to all checks)
    apart from "user unticked everything" (return empty -> error).
    """
    if not form.get("checks_submitted"):
        return list(ALL_CHECKS)
    return [name for name in ALL_CHECKS if form.get(f"check_{name}")]


def register_routes(app):
    """Attach every URL route + error handler to the Flask app."""

    # ----- pages -------------------------------------------------------

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/about")
    def about():
        return render_template("about.html")

    @app.route("/detect", methods=["GET", "POST"])
    def detect():
        # GET = show the form.
        if request.method == "GET":
            return render_template("detect.html")

        # POST = run validation.
        headline = (request.form.get("headline") or "").strip()
        if not headline:
            return render_template(
                "detect.html",
                error="Please enter a headline before submitting.",
                selected_checks=_selected_checks_from_form(request.form),
            )

        selected = _selected_checks_from_form(request.form)


        log.info("Running validator on headline=%r checks=%s", headline, selected)
        check_classes = [ALL_CHECKS[name] for name in selected]
        validator = FakeNewsValidator(
            headline, checks=check_classes, stop_on_first_failure=True
        )

        started = time.monotonic()
        try:
            report = validator.validate()
        except FileNotFoundError as exc:
            # Missing model artifact -> tell the user, don't crash.
            log.exception("Model artifact missing")
            return render_template(
                "detect.html",
                error=f"Setup error: {exc}",
                headline=headline,
                selected_checks=selected,
            )

        # If validation finished too fast, sleep the difference so the
        # in-flight progress animation has time to play through.
        elapsed = time.monotonic() - started
        if elapsed < _MIN_RESPONSE_S:
            time.sleep(_MIN_RESPONSE_S - elapsed)

        return render_template(
            "results.html", report=report, ran_check_names=selected
        )

    # ----- error handlers ---------------------------------------------

    @app.errorhandler(404)
    def not_found(_err):
        return render_template("error.html", code=404, message="Page not found"), 404

    @app.errorhandler(500)
    def server_error(_err):
        return (
            render_template(
                "error.html", code=500, message="Something went wrong on our end."
            ),
            500,
        )
