"""Check 5 - Web presence (the heaviest check, runs last).

The idea: if a headline is true, real news outlets should be reporting
on the same event. We:

1. Search a search engine for the headline.
   - DuckDuckGo (default, no API key, very stable).
   - Google (matches the original 2023 design - dynamic per-domain
     news verification using `tbm=nws`).
2. Filter the results to "trusted" sources.
   - DDG path: a curated allowlist of well-known outlets.
   - Google path: ask Google itself "is this domain a news source?"
     by querying `q=<domain>&tbm=nws` and checking the response.
3. Compute sentence similarity (cosine) between our headline and each
   candidate title/snippet using a SentenceTransformer.
4. Take the closest match and ask the LLM (Gemini or Claude): "Do
   these two headlines describe the same factual event?"

Pass = at least 3 trusted hits, at least 2 of them similar enough,
AND the LLM agrees they describe the same event.
"""

import logging
import re
from urllib.parse import parse_qs, unquote, urlparse

import requests
from bs4 import BeautifulSoup

from fakenews_detector.checks.base import Check, CheckResult
from fakenews_detector.config import get_settings
from fakenews_detector.nlp.similarity import (
    cosine_similarity_score,
    llm_contextual_match,
)

log = logging.getLogger(__name__)

_DDG_HTML_ENDPOINT = "https://html.duckduckgo.com/html/"
_GOOGLE_SEARCH_ENDPOINT = "https://www.google.com/search"


# ----- DuckDuckGo trust allowlist ------------------------------------
# DDG has no per-source "is this a news site?" API, so we maintain a
# curated list of reputable news / reference domains. Without this,
# satire sites that DDG categorises as 'news' would let fake headlines
# pass the web-presence gate.
_TRUSTED_DOMAINS = frozenset({
    # Major international wire services / outlets
    "reuters.com", "apnews.com", "bbc.com", "bbc.co.uk", "cnn.com",
    "nytimes.com", "washingtonpost.com", "theguardian.com",
    "bloomberg.com", "ft.com", "wsj.com", "economist.com", "npr.org",
    "aljazeera.com", "dw.com", "france24.com", "cbsnews.com",
    "abcnews.go.com", "nbcnews.com", "foxnews.com", "usatoday.com",
    "time.com", "newsweek.com", "axios.com", "politico.com",
    # Indian outlets
    "ndtv.com", "thehindu.com", "indianexpress.com",
    "timesofindia.indiatimes.com", "hindustantimes.com",
    "indiatoday.in", "news18.com", "livemint.com",
    "business-standard.com", "moneycontrol.com", "thequint.com",
    "scroll.in", "thewire.in", "firstpost.com", "deccanherald.com",
    "tribuneindia.com", "republicworld.com",
    # Tech / science journalism
    "techcrunch.com", "theverge.com", "wired.com", "arstechnica.com",
    "engadget.com", "scientificamerican.com", "nature.com",
    "scitechdaily.com", "extremetech.com",
    # Reference
    "wikipedia.org",
})

# Government / education TLDs - any subdomain is trusted.
_TRUSTED_TLD_PATTERNS = (
    ".gov", ".gov.in", ".gov.uk", ".gov.au", ".gov.ca",
    ".gc.ca", ".int", ".edu", ".ac.uk", ".ac.in",
)

# Headers that nudge Google into serving real HTML instead of the
# "please enable JavaScript" shell page.
_GOOGLE_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Cookie": "CONSENT=YES+cb",
    "Sec-Ch-Ua": '"Chromium";v="120", "Not(A:Brand";v="24", "Google Chrome";v="120"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}

# Domains we never bother sending through the per-domain news check
# (they show up in Google SERPs but are obviously not news sources).
_GOOGLE_OWN_DOMAINS = (
    "google.com", "gstatic.com", "googleusercontent.com",
    "youtube.com", "blogspot.com",
)


class _Candidate:
    """One search result we'll compare the headline against."""
    def __init__(self, url, title, snippet):
        self.url = url
        self.title = title
        self.snippet = snippet


class WebPresenceCheck(Check):
    name = "web_presence"

    def __init__(self):
        self._settings = get_settings()
        self._session = requests.Session()
        self._session.headers["User-Agent"] = self._settings.user_agent
        # Cache the per-domain "is this a news source?" answer so we
        # don't ask Google about the same domain twice in one validation.
        self._news_domain_cache = {}

    # ----- public entry point -------------------------------------------

    def run(self, headline):
        candidates = self._collect_candidates(headline)
        log.info("web_presence: %d trustworthy candidates", len(candidates))

        # Not enough corroborating sources -> definitely fail.
        if len(candidates) < self._settings.web_presence_min_results:
            return CheckResult(
                name=self.name,
                passed=False,
                detail=(
                    f"only {len(candidates)} corroborating results "
                    f"(need {self._settings.web_presence_min_results})"
                ),
                metadata={"candidates": [c.url for c in candidates]},
            )

        passed, best, agg_sim = self._verify_against_candidates(headline, candidates)

        return CheckResult(
            name=self.name,
            passed=passed,
            detail=(
                f"verified against {best.url}" if passed and best
                else "no matching corroboration"
            ),
            metadata={
                "best_match_url": best.url if best else None,
                "best_match_title": best.title if best else None,
                "aggregate_similarity": agg_sim,
                "candidates_considered": len(candidates),
            },
        )

    # ----- step 1: collect candidates -----------------------------------

    def _collect_candidates(self, headline):
        """Pick the search backend based on settings, with a fallback."""
        provider = self._settings.search_provider
        log.debug("web_presence search_provider=%s", provider)

        if provider == "google":
            candidates = self._collect_candidates_google(headline)
            if candidates:
                return candidates
            # If Google served us the JS-shell page or rate-limited,
            # silently fall back to DDG so the demo never breaks.
            log.warning(
                "Google returned 0 candidates; falling back to DuckDuckGo."
            )
            return self._collect_candidates_ddg(headline)

        return self._collect_candidates_ddg(headline)

    def _collect_candidates_ddg(self, query):
        """DuckDuckGo HTML endpoint + the news vertical (`iar=news`)."""
        try:
            response = self._session.get(
                _DDG_HTML_ENDPOINT,
                params={"q": query, "iar": "news"},
                timeout=10,
            )
        except requests.RequestException:
            log.exception("DDG SERP request failed for query=%r", query)
            return []
        if response.status_code != 200:
            log.warning("DDG SERP status=%d", response.status_code)
            return []

        soup = BeautifulSoup(response.content, "html.parser")
        result_blocks = soup.find_all("div", class_="result")
        log.debug("DDG SERP: %d raw result blocks", len(result_blocks))

        candidates = []
        for block in result_blocks:
            title_el = block.find("a", class_="result__a")
            snippet_el = block.find("a", class_="result__snippet")
            url_el = block.find("a", class_="result__url")
            if title_el is None or url_el is None:
                continue

            url = self._resolve_real_url(title_el.get("href", ""), url_el)
            if not url:
                continue

            domain = urlparse(url).netloc.lower().replace("www.", "")
            if not self._domain_is_in_allowlist(domain):
                log.debug("ddg: rejecting untrusted domain %s", domain)
                continue

            title = title_el.get_text(strip=True)
            snippet = snippet_el.get_text(strip=True) if snippet_el else ""
            candidates.append(_Candidate(url=url, title=title, snippet=snippet))
        return candidates

    def _collect_candidates_google(self, query):
        """Google web search + per-domain `tbm=nws` news verification.

        This is the original 2023 design: instead of an allowlist, we
        ask Google itself whether each result's domain is in its news
        index by re-querying `q=<domain>&tbm=nws`.
        """
        try:
            response = self._session.get(
                _GOOGLE_SEARCH_ENDPOINT,
                params={"q": query, "hl": "en"},
                headers=_GOOGLE_HEADERS,
                timeout=10,
            )
        except requests.RequestException:
            log.exception("Google SERP request failed for query=%r", query)
            return []
        if response.status_code != 200:
            log.warning("Google SERP status=%d", response.status_code)
            return []

        # Google sometimes serves a "please enable JS" page. Detect it
        # by the presence of the word "enablejs" + very few CSS classes.
        if self._is_google_js_shell(response.text):
            log.warning("Google served a JavaScript-shell page; no results.")
            return []

        soup = BeautifulSoup(response.content, "html.parser")
        raw = self._extract_google_organic_results(soup)
        log.debug("Google SERP: %d raw organic results", len(raw))

        candidates = []
        for url, title, snippet in raw:
            domain = urlparse(url).netloc.lower().replace("www.", "")
            if not domain or domain.endswith(_GOOGLE_OWN_DOMAINS):
                continue
            if not self._domain_appears_in_google_news(domain):
                log.debug("google: domain not in news index, rejecting %s", domain)
                continue
            candidates.append(_Candidate(url=url, title=title, snippet=snippet))
        return candidates

    @staticmethod
    def _is_google_js_shell(body):
        """True if Google sent the 'please enable JavaScript' page."""
        return "enablejs" in body and body.count("class=") < 20

    @staticmethod
    def _extract_google_organic_results(soup):
        """Pull (url, title, snippet) tuples from a generic Google SERP.

        Google rotates its CSS class names often, so we don't depend on
        them. Instead: every organic result has an `<h3>` title sitting
        inside an `<a href="http...">`. We walk those.
        """
        results = []
        seen = set()
        for h3 in soup.find_all("h3"):
            link = h3.find_parent("a", href=True)
            if link is None:
                continue
            url = link["href"]
            # Skip Google's own internal links.
            if not url.startswith("http") or "google.com" in url[:30]:
                continue
            if url in seen:
                continue
            seen.add(url)

            title = h3.get_text(strip=True)
            snippet = ""
            container = link.find_parent(["div", "li"])
            if container is not None:
                snippet_el = (
                    container.find("div", attrs={"data-sncf": True})
                    or container.find("span", attrs={"role": "text"})
                )
                if snippet_el is not None:
                    snippet = snippet_el.get_text(" ", strip=True)
            results.append((url, title, snippet))
        return results

    def _domain_appears_in_google_news(self, domain):
        """Ask Google: is this domain a known news source?"""
        if domain in self._news_domain_cache:
            return self._news_domain_cache[domain]

        try:
            response = self._session.get(
                _GOOGLE_SEARCH_ENDPOINT,
                params={"q": domain, "tbm": "nws", "hl": "en"},
                headers=_GOOGLE_HEADERS,
                timeout=self._settings.web_presence_request_timeout_s,
            )
        except requests.RequestException:
            log.warning("news-domain probe failed for %s", domain)
            self._news_domain_cache[domain] = False
            return False

        if response.status_code != 200:
            self._news_domain_cache[domain] = False
            return False

        body = response.text
        if self._is_google_js_shell(body):
            # Google rate-limited us. Be permissive (the LLM gate is
            # the real safety net) rather than silently rejecting.
            log.debug("news-domain probe shelled for %s; assuming trusted", domain)
            self._news_domain_cache[domain] = True
            return True

        is_news = domain.lower() in body.lower()
        self._news_domain_cache[domain] = is_news
        return is_news

    @staticmethod
    def _resolve_real_url(raw_href, url_el):
        """DDG wraps result links through `//duckduckgo.com/l/?uddg=...`.

        Pull the real destination URL out of the redirect.
        """
        if raw_href:
            href = raw_href
            if href.startswith("//"):
                href = "https:" + href
            parsed = urlparse(href)
            if parsed.netloc.endswith("duckduckgo.com"):
                qs = parse_qs(parsed.query)
                if "uddg" in qs and qs["uddg"]:
                    return unquote(qs["uddg"][0])
            if parsed.scheme in ("http", "https") and parsed.netloc:
                return href

        # Fallback: use the visible URL text (e.g. "www.isro.gov.in/...").
        visible = url_el.get_text(strip=True) if url_el else ""
        if visible:
            visible = re.sub(r"\s+", "", visible)
            if not visible.startswith(("http://", "https://")):
                visible = "https://" + visible
            return visible
        return ""

    @staticmethod
    def _domain_is_in_allowlist(domain):
        """Curated trust check used by the DDG backend."""
        if not domain:
            return False
        if domain in _TRUSTED_DOMAINS:
            return True
        # Subdomains of a trusted root, e.g. "edition.cnn.com".
        for trusted in _TRUSTED_DOMAINS:
            if domain.endswith("." + trusted):
                return True
        # .gov / .edu / .int etc.
        for tld in _TRUSTED_TLD_PATTERNS:
            if domain.endswith(tld):
                return True
        return False

    # ----- step 2-4: similarity + LLM gate ------------------------------

    def _verify_against_candidates(self, headline, candidates):
        """Score each candidate, then ask the LLM about the best match."""
        threshold = self._settings.web_presence_similarity_threshold
        min_similar = self._settings.web_presence_min_similar

        best_score = 0.0
        best_candidate = None
        accepted_scores = []

        # Step 2 + 3: score each candidate and find the closest match.
        for candidate in candidates:
            sim_title = cosine_similarity_score(headline, candidate.title)
            sim_snippet = (
                cosine_similarity_score(headline, candidate.snippet)
                if candidate.snippet
                else 0.0
            )
            best_local = max(sim_title, sim_snippet)
            log.debug(
                "candidate %s -> sim_title=%.3f sim_snippet=%.3f",
                candidate.url, sim_title, sim_snippet,
            )

            if best_local > best_score:
                best_score = best_local
                best_candidate = candidate
            if best_local >= threshold:
                accepted_scores.append(best_local)

        # Not enough similar candidates -> fail.
        if best_candidate is None or len(accepted_scores) < min_similar:
            return False, best_candidate, 0.0

        # Step 4: final yes/no from the LLM. This catches near-duplicate
        # strings that actually differ in a key fact (e.g. "9 killed"
        # vs "19 killed" - very high cosine, but different events).
        cleaned_match = re.sub(r"\s+", " ", best_candidate.title).strip()
        try:
            llm_ok = llm_contextual_match(headline, cleaned_match)
        except Exception:
            log.exception("LLM contextual match failed; treating as fail")
            return False, best_candidate, 0.0

        if not llm_ok:
            return False, best_candidate, 0.0

        agg = best_score
        return True, best_candidate, agg
