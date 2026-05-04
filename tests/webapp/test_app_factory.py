"""Tests for `webapp.app.create_app`.

We don't test Flask itself -- we just verify our factory wires the
routes, the config, and the template-context globals correctly.
"""

import pytest
from flask import Flask

from webapp import create_app
from webapp.app import BRAND_NAME, CHECK_LABELS


class TestCreateApp:
    """`create_app()` returns a fully-wired Flask instance."""

    def test_returns_a_flask_app(self):
        app = create_app()
        assert isinstance(app, Flask)

    def test_secret_key_is_set(self):
        # Flask refuses to run without a secret key. The factory should
        # always populate one (from env or the dev fallback).
        app = create_app()
        assert app.config["SECRET_KEY"]

    def test_all_user_facing_routes_are_registered(self):
        app = create_app()
        rules = {r.rule for r in app.url_map.iter_rules()}
        assert "/" in rules
        assert "/about" in rules
        assert "/detect" in rules


class TestTemplateGlobals:
    """The context processor injects `brand`, `all_check_names`, `check_labels`."""

    def test_brand_is_injected(self, client):
        response = client.get("/")
        assert response.status_code == 200
        # The base template renders `{{ brand }}` in the page title and footer.
        assert BRAND_NAME.encode() in response.data

    def test_check_labels_cover_every_pipeline_check(self):
        # Every check the validator runs should have a friendly UI label.
        # Otherwise the results page would show a raw snake_case name.
        from webapp.routes import ALL_CHECKS

        for check_name in ALL_CHECKS:
            assert check_name in CHECK_LABELS, (
                f"Check {check_name!r} has no friendly label in CHECK_LABELS"
            )
