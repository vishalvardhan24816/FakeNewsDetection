"""Pytest fixtures for the webapp tests.

Provides:

* `client` -- a Flask test client that lets tests call HTTP routes
  without spinning up a real server.
* `_no_response_pad` (autouse) -- forces the /detect "minimum response"
  pad to 0 so tests don't sleep 5 seconds for each POST.
"""

import pytest

from webapp import create_app
from webapp import routes as webapp_routes


@pytest.fixture(autouse=True)
def _no_response_pad():
    """Disable the artificial UX delay during tests.

    The /detect route normally sleeps so the in-flight progress
    animation always plays through. Tests don't care about that and we
    don't want every test waiting 5s.
    """
    original = webapp_routes._MIN_RESPONSE_S
    webapp_routes._MIN_RESPONSE_S = 0.0
    yield
    webapp_routes._MIN_RESPONSE_S = original


@pytest.fixture
def app():
    """A freshly-built Flask app, configured for tests."""
    app = create_app()
    app.config["TESTING"] = True
    return app


@pytest.fixture
def client(app):
    """Flask test client. Use it like `client.get('/')`."""
    return app.test_client()
