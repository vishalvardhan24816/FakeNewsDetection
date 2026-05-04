"""Step 5 - web-presence gate.

This is the heaviest check and the final gate. It:

1. Searches a search-engine for the headline. Two backends are wired
   up; pick via the ``SEARCH_PROVIDER`` env var:

   * ``ddg`` (default): DuckDuckGo HTML + ``iar=news``. Stable, no
     API key, no JS required. Trust-filtered against a curated
     allowlist (DDG has no per-source "is this a news domain" API).
     Recommended for the demo.
   * ``google``: Google web search + dynamic ``tbm=nws`` per-domain
     trust check (this is what the original 3-year-old code did).
     For each candidate URL we ask Google "is this domain a news
     source?" by issuing ``q=<domain>&tbm=nws`` and checking the
     response. Google may intermittently serve a JavaScript-shell
     page; in that case we fall back to DDG.

2. Computes sentence-similarity between the headline and each
   trusted candidate's title/snippet (SentenceTransformer + cosine).
3. Picks the closest match and asks the configured LLM
   (Gemini / Anthropic, see ``fakenews_detector.nlp.similarity``)
   for a final yes/no contextual-similarity verdict.

Pluggability: adding a third backend (Bing API, NewsAPI, SerpAPI) is
a single new ``_collect_candidates_<name>`` method + dispatch entry.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
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

# DDG trust allowlist. DDG has no equivalent of Google's tbm=nws
# per-source classifier, so we maintain a curated list of reputable
# news / reference domains. Without this, satire and opinion blogs
# that DDG categorises as 'news' would let fake headlines pass.
_TRUSTED_DOMAINS = frozenset({
    # International wire services / major outlets
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

# Government / education TLD patterns (any subdomain trusted).
_TRUSTED_TLD_PATTERNS = (
    ".gov", ".gov.in", ".gov.uk", ".gov.au", ".gov.ca",
    ".gc.ca", ".int", ".edu", ".ac.uk", ".ac.in",
)

# Headers that nudge Google toward serving a real HTML SERP instead of
# the "please enable JavaScript" shell. The CONSENT cookie skips the
# EU consent interstitial; the Sec-Ch-* headers mimic Chrome.
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

# Domains we never bother sending through the per-domain news-check
# (they're definitely not news sources, but they appear in SERPs).
_GOOGLE_OWN_DOMAINS = (
    "google.com", "gstatic.com", "googleusercontent.com",
    "youtube.com", "blogspot.com",
)


@dataclass
class _Candidate:
    url: str
    title: str
    snippet: str


class WebPresenceCheck(Check):
    name = "web_presence"

    def __init__(self) -> None:
        self._settings = get_settings()
        self._session = requests.Session()
        self._session.headers["User-Agent"] = self._settings.user_agent
        # Memoise the per-domain Google news check so a single validation
        # never queries the same domain twice.
        self._news_domain_cache: Dict[str, bool] = {}

    # ----- public ----------------------------------------------------

    def run(self, headline: str) -> CheckResult:
        candidates = self._collect_candidates(headline)
        log.info("web_presence: %d trustworthy candidates", len(candidates))

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

    # ----- candidate collection (dispatched per provider) -----------

    def _collect_candidates(self, headline: str) -> List[_Candidate]:
        provider = self._settings.search_provider
        log.debug("web_presence search_provider=%s", provider)
        if provider == "google":
            candidates = self._collect_candidates_google(headline)
            if candidates:
                return candidates
            log.warning(
                "Google returned 0 candidates (likely JS-shell page or rate limit); "
                "falling back to DuckDuckGo."
            )
            return self._collect_candidates_ddg(headline)
        return self._collect_candidates_ddg(headline)

    # ----- DuckDuckGo backend ----------------------------------------

    def _collect_candidates_ddg(self, query: str) -> List[_Candidate]:
        # iar=news restricts to DDG's news vertical (analog of Google's
        # tbm=nws), so results are pre-filtered to registered news sources.
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

        candidates: List[_Candidate] = []
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

    # ----- Google backend (original 2023 behavior) -------------------

    def _collect_candidates_google(self, query: str) -> List[_Candidate]:
        """Google web search + dynamic per-domain news classification.

        This mirrors the original 3-year-old design: instead of
        relying on a hardcoded allowlist, we ask Google itself
        "is this domain a registered news source?" by issuing
        ``q=<domain>&tbm=nws`` for each candidate's domain.
        Domains that show up in their own news search are trusted.
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

        if self._is_google_js_shell(response.text):
            log.warning("Google served a JavaScript-shell page; no results parseable.")
            return []

        soup = BeautifulSoup(response.content, "html.parser")
        raw = self._extract_google_organic_results(soup)
        log.debug("Google SERP: %d raw organic results", len(raw))

        candidates: List[_Candidate] = []
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
    def _is_google_js_shell(body: str) -> bool:
        # Google's "please enable JS" page has near-zero classed divs
        # and contains the word "enablejs".
        return "enablejs" in body and body.count("class=") < 20

    @staticmethod
    def _extract_google_organic_results(
        soup: BeautifulSoup,
    ) -> List[Tuple[str, str, str]]:
        """Pull (url, title, snippet) tuples from a generic Google SERP.

        We deliberately don't depend on Google's CSS classes (they
        rotate). Instead: every organic result has an ``<h3>`` title
        inside an ``<a href="http...">``. Snippet is the nearest text
        sibling under the result's container.
        """
        results: List[Tuple[str, str, str]] = []
        seen: set[str] = set()
        for h3 in soup.find_all("h3"):
            link = h3.find_parent("a", href=True)
            if link is None:
                continue
            url = link["href"]
            if not url.startswith("http") or "google.com" in url[:30]:
                continue
            if url in seen:
                continue
            seen.add(url)
            title = h3.get_text(strip=True)
            # Snippet: walk up to a sensible container and grab text from
            # the next sibling div (Google nests these inconsistently).
            snippet = ""
            container = link.find_parent(["div", "li"])
            if container is not None:
                snippet_el = container.find("div", attrs={"data-sncf": True}) or \
                    container.find("span", attrs={"role": "text"})
                if snippet_el is not None:
                    snippet = snippet_el.get_text(" ", strip=True)
            results.append((url, title, snippet))
        return results

    def _domain_appears_in_google_news(self, domain: str) -> bool:
        """Ask Google whether a domain is in its news index.

        This is the original 2023 trust mechanism: hit
        ``q=<domain>&tbm=nws`` and check if the domain shows up in
        the news SERP body. Cached per-validation so we never query
        the same domain twice.
        """
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
            # Google rate-limited / shelled us. Be permissive rather than
            # silently fail - the LLM gate is the real backstop.
            log.debug("news-domain probe shelled for %s; assuming trusted", domain)
            self._news_domain_cache[domain] = True
            return True

        is_news = domain.lower() in body.lower()
        self._news_domain_cache[domain] = is_news
        return is_news

    @staticmethod
    def _resolve_real_url(raw_href: str, url_el) -> str:
        """DDG wraps result links through ``//duckduckgo.com/l/?uddg=...``.
        Extract the real destination URL.
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
        visible = url_el.get_text(strip=True) if url_el else ""
        if visible:
            visible = re.sub(r"\s+", "", visible)
            if not visible.startswith(("http://", "https://")):
                visible = "https://" + visible
            return visible
        return ""

    @staticmethod
    def _domain_is_in_allowlist(domain: str) -> bool:
        """Allowlist check used by the DDG backend."""
        if not domain:
            return False
        if domain in _TRUSTED_DOMAINS:
            return True
        for trusted in _TRUSTED_DOMAINS:
            if domain.endswith("." + trusted):
                return True
        for tld in _TRUSTED_TLD_PATTERNS:
            if domain.endswith(tld):
                return True
        return False

    def _verify_against_candidates(
        self, headline: str, candidates: List[_Candidate]
    ) -> Tuple[bool, Optional[_Candidate], float]:
        threshold = self._settings.web_presence_similarity_threshold
        min_similar = self._settings.web_presence_min_similar

        best_score = 0.0
        best_candidate: Optional[_Candidate] = None
        accepted_scores: List[float] = []

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

        if best_candidate is None or len(accepted_scores) < min_similar:
            return False, best_candidate, 0.0

        cleaned_match = re.sub(r"\s+", " ", best_candidate.title).strip()
        try:
            llm_ok = llm_contextual_match(headline, cleaned_match)
        except Exception:
            log.exception("LLM contextual match failed; treating as fail")
            return False, best_candidate, 0.0

        if not llm_ok:
            return False, best_candidate, 0.0

        agg = sum(accepted_scores) / len(accepted_scores)
        return True, best_candidate, agg
