"""HTTP routes for the DebunkHub web UI."""

from __future__ import annotations

import logging

from flask import (
    Blueprint,
    abort,
    current_app,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)

from webapp.jobs import JOB_DONE, JOB_ERROR

log = logging.getLogger(__name__)

bp = Blueprint("ui", __name__)


# ----- pages -------------------------------------------------------------


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
        )

    job = current_app.config["JOB_REGISTRY"].submit(headline)
    log.info("Submitted job %s", job.id)
    return redirect(url_for("ui.progress", job_id=job.id))


@bp.get("/progress/<job_id>")
def progress(job_id: str):
    job = current_app.config["JOB_REGISTRY"].get(job_id)
    if job is None:
        abort(404)
    return render_template("progress.html", job=job)


@bp.get("/results/<job_id>")
def results(job_id: str):
    job = current_app.config["JOB_REGISTRY"].get(job_id)
    if job is None:
        abort(404)
    if job.status not in (JOB_DONE, JOB_ERROR):
        # Not finished yet - send them back to the progress page.
        return redirect(url_for("ui.progress", job_id=job.id))
    return render_template("results.html", job=job)


# ----- JSON endpoints (used by the progress page) ------------------------


@bp.get("/api/jobs/<job_id>")
def api_job_status(job_id: str):
    job = current_app.config["JOB_REGISTRY"].get(job_id)
    if job is None:
        return jsonify({"error": "not_found"}), 404
    return jsonify(job.to_dict())


# ----- error handlers ----------------------------------------------------


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
