"""Tests for `fakenews_detector.checks.web_presence`.

The web-presence check is the heaviest one: it does HTTP, sentence
similarity, and an LLM call. We don't want to hit the real network or
load real models, so every external piece is mocked:

* `requests.Session.get` -- returns canned HTML
* `cosine_similarity_score` -- returns canned similarity floats
* `llm_contextual_match`   -- returns True/False directly

The pure helper methods (`_domain_is_in_allowlist`, `_resolve_real_url`,
`_is_google_js_shell`) are tested directly without any patching.
"""

from unittest.mock import MagicMock, patch

import pytest

from fakenews_detector.checks import web_presence as wp
from fakenews_detector.checks.web_presence import WebPresenceCheck


# ----- pure helpers (no patching needed) -------------------------------


class TestDomainAllowlist:
    """`_domain_is_in_allowlist`: exact, subdomain, and TLD matches."""

    def test_exact_match_is_trusted(self):
        assert WebPresenceCheck._domain_is_in_allowlist("reuters.com") is True

    def test_subdomain_of_trusted_root_is_trusted(self):
        # edition.cnn.com ends with ".cnn.com" -> trusted.
        assert WebPresenceCheck._domain_is_in_allowlist("edition.cnn.com") is True

    def test_gov_tld_is_trusted(self):
        assert WebPresenceCheck._domain_is_in_allowlist("isro.gov.in") is True

    def test_random_blog_is_rejected(self):
        assert WebPresenceCheck._domain_is_in_allowlist("randomblog123.net") is False

    def test_empty_string_is_rejected(self):
        assert WebPresenceCheck._domain_is_in_allowlist("") is False


class TestGoogleJsShellDetector:
    """`_is_google_js_shell`: spot the 'please enable JavaScript' page."""

    def test_real_serp_is_not_a_shell(self):
        # A real SERP has tons of class= attributes.
        body = "<html>" + ("<div class='x'></div>" * 100) + "</html>"
        assert WebPresenceCheck._is_google_js_shell(body) is False

    def test_js_shell_is_detected(self):
        # The shell page has the marker AND very few class= attributes.
        body = "<html><script>enablejs();</script><div></div></html>"
        assert WebPresenceCheck._is_google_js_shell(body) is True


class TestResolveRealUrl:
    """`_resolve_real_url`: unwraps DDG redirects, accepts raw URLs."""

    def test_unwraps_ddg_redirect(self):
        href = "//duckduckgo.com/l/?uddg=https%3A//www.bbc.com/news/abc"
        out = WebPresenceCheck._resolve_real_url(href, url_el=None)
        assert out == "https://www.bbc.com/news/abc"

    def test_accepts_a_plain_https_url(self):
        href = "https://www.bbc.com/news/abc"
        out = WebPresenceCheck._resolve_real_url(href, url_el=None)
        assert out == "https://www.bbc.com/news/abc"

    def test_falls_back_to_visible_url_text(self):
        # When `raw_href` is empty we read from the visible URL element.
        fake_el = MagicMock()
        fake_el.get_text.return_value = "www.example.com/path"
        out = WebPresenceCheck._resolve_real_url(raw_href="", url_el=fake_el)
        assert out == "https://www.example.com/path"


# ----- run() happy + sad paths -----------------------------------------


def _make_check_with_settings(min_results=3, min_similar=2, threshold=0.5):
    """Build a WebPresenceCheck with overridden numeric thresholds."""
    chk = WebPresenceCheck()
    chk._settings.web_presence_min_results = min_results
    chk._settings.web_presence_min_similar = min_similar
    chk._settings.web_presence_similarity_threshold = threshold
    return chk


class TestWebPresenceRun:
    """End-to-end `run()` with everything below it mocked."""

    def test_fails_when_too_few_candidates(self):
        chk = _make_check_with_settings(min_results=3)
        with patch.object(chk, "_collect_candidates", return_value=[]):
            result = chk.run("some headline")

        assert result.passed is False
        assert "corroborating" in result.detail

    def test_passes_when_candidates_match_and_llm_agrees(self):
        chk = _make_check_with_settings(min_results=3, min_similar=2, threshold=0.5)
        candidates = [
            wp._Candidate(url=f"https://news.example.com/{i}",
                          title="ISRO launches Chandrayaan-3",
                          snippet="ISRO has launched Chandrayaan-3.")
            for i in range(3)
        ]

        with patch.object(chk, "_collect_candidates", return_value=candidates), \
             patch(
                 "fakenews_detector.checks.web_presence.cosine_similarity_score",
                 return_value=0.95,
             ), \
             patch(
                 "fakenews_detector.checks.web_presence.llm_contextual_match",
                 return_value=True,
             ):
            result = chk.run("ISRO launches Chandrayaan-3")

        assert result.passed is True
        assert "verified against" in result.detail
        assert result.metadata["best_match_url"].startswith("https://news.example.com/")

    def test_fails_when_llm_says_no(self):
        # Cosine says match, but LLM rejects -> overall fail. This is
        # the "9 killed vs 19 killed" guardrail.
        chk = _make_check_with_settings()
        candidates = [
            wp._Candidate(url=f"https://news.example.com/{i}",
                          title="9 killed in Delhi fire",
                          snippet="A blaze in Delhi killed 9 people.")
            for i in range(3)
        ]

        with patch.object(chk, "_collect_candidates", return_value=candidates), \
             patch(
                 "fakenews_detector.checks.web_presence.cosine_similarity_score",
                 return_value=0.97,
             ), \
             patch(
                 "fakenews_detector.checks.web_presence.llm_contextual_match",
                 return_value=False,
             ):
            result = chk.run("19 killed in Delhi fire")

        assert result.passed is False

    def test_llm_exception_is_caught_and_treated_as_fail(self):
        # If the LLM API errors out, we fail closed (don't crash).
        chk = _make_check_with_settings()
        candidates = [
            wp._Candidate(url=f"https://news.example.com/{i}",
                          title="x", snippet="x")
            for i in range(3)
        ]

        with patch.object(chk, "_collect_candidates", return_value=candidates), \
             patch(
                 "fakenews_detector.checks.web_presence.cosine_similarity_score",
                 return_value=0.95,
             ), \
             patch(
                 "fakenews_detector.checks.web_presence.llm_contextual_match",
                 side_effect=RuntimeError("LLM down"),
             ):
            result = chk.run("any headline")

        assert result.passed is False
