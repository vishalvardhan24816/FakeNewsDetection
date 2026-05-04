"""HTTP routes for the DebunkHub web UI."""

from __future__ import annotations

import logging
import os
import time

from flask import Blueprint, render_template, request

from fakenews_detector.checks import (
    ClickbaitCheck,
    NewsTitleCheck,
    SpellingCheck,
    SubjectivityCheck,
    WebPresenceCheck,
)
from fakenews_detector.validator import FakeNewsValidator

log = logging.getLogger(__name__)

bp = Blueprint("ui", __name__)

# Minimum wall-clock time (seconds) the /detect POST takes before it
# returns a result page. Real validation can finish in <500ms when a
# cheap check fails fast (typo headline -> spelling check rejects in
# one tokenizer pass). That's *too* fast - the in-flight pipeline
# animation barely flashes and the user wonders if anything actually
# ran. Padding to ~5s lets the animation play through the first few
# steps before the page navigates. Override with DETECT_MIN_RESPONSE_S.
_MIN_RESPONSE_S = float(os.environ.get("DETECT_MIN_RESPONSE_S", "5.0"))

# Lookup table: form field name -> Check class. Order is the canonical
# pipeline order (cheapest first, expensive last) so the validator
# short-circuits early on form-level failures and only spends real
# time on web_presence when needed.
ALL_CHECKS: dict[str, type] = {
    "spelling": SpellingCheck,
    "clickbait": ClickbaitCheck,
    "subjectivity": SubjectivityCheck,
    "news_title": NewsTitleCheck,
    "web_presence": WebPresenceCheck,
}


def _selected_checks_from_form(form) -> list[str]:
    """Read which check checkboxes the user enabled.

    The form always submits a ``checks_submitted=1`` marker so we can
    distinguish "form had no checkbox fields at all" (default to all)
    from "user unticked everything" (return empty -> show error).
    """
    if not form.get("checks_submitted"):
        return list(ALL_CHECKS)
    return [name for name in ALL_CHECKS if form.get(f"check_{name}")]


# ----- pages ------------------------------------------------------------


@bp.get("/")
def index():
    return render_template("index.html")


@bp.get("/about")
def about():
    return render_template("about.html")


@bp.route("/detect", methods=["GET", "POST"])
def detect():
    if request.method == "GET":
        return render_template("detect.html")

    headline = (request.form.get("headline") or "").strip()
    if not headline:
        return render_template(
            "detect.html",
            error="Please enter a headline before submitting.",
            selected_checks=_selected_checks_from_form(request.form),
        )

    selected = _selected_checks_from_form(request.form)
    if not selected:
        return render_template(
            "detect.html",
            error="Please enable at least one check.",
            headline=headline,
            selected_checks=[],
        )

    log.info("Running validator on headline=%r checks=%s", headline, selected)
    check_instances = [ALL_CHECKS[name]() for name in selected]
    validator = FakeNewsValidator(
        headline, checks=check_instances, stop_on_first_failure=True
    )
    started = time.monotonic()
    try:
        report = validator.validate()
    except FileNotFoundError as exc:
        log.exception("Model artifact missing")
        return render_template(
            "detect.html",
            error=f"Setup error: {exc}",
            headline=headline,
            selected_checks=selected,
        )

    # Pad fast responses so the in-flight pipeline animation isn't
    # cut off mid-flow on early failures.
    elapsed = time.monotonic() - started
    if elapsed < _MIN_RESPONSE_S:
        pad = _MIN_RESPONSE_S - elapsed
        log.debug("Padding response by %.2fs (real=%.2fs)", pad, elapsed)
        time.sleep(pad)

    return render_template(
        "results.html", report=report, ran_check_names=selected
    )


# ----- error handlers ---------------------------------------------------


@bp.app_errorhandler(404)
def not_found(_err):
    return render_template("error.html", code=404, message="Page not found"), 404


@bp.app_errorhandler(500)
def server_error(_err):
    return (
        render_template(
            "error.html", code=500, message="Something went wrong on our end."
        ),
        500,
    )
