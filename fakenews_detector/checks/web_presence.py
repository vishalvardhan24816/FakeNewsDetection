"""Step 5 - web-presence gate.

This is the heaviest check and the final gate. It:

1. Searches Google for the headline.
2. For each result, fetches the page title and checks the host actually
   shows up under Google News (sanity filter against random blogs).
3. Computes sentence-similarity between the headline and each
   matching title/snippet.
4. Picks the closest match and asks Anthropic Claude for a final
   yes/no contextual-similarity verdict.

.. warning::

    This check scrapes Google's HTML using selectors that were valid in
    2023 (``yuRUbf``, ``VwiC3b``, ...). Google rotates these
    frequently, so this check may need its CSS selectors updated to
    work today. Behavior is preserved as-is for this refactor.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from fakenews_detector.checks.base import Check, CheckResult
from fakenews_detector.config import get_settings
from fakenews_detector.nlp.similarity import (
    cosine_similarity_score,
    llm_contextual_match,
)

log = logging.getLogger(__name__)

# 2023-era Google SERP CSS classes. Likely to need re-identification.
_RESULT_CARD_CLASS = "yuRUbf"
_SNIPPET_CLASSES = ["VwiC3b", "yXK7lf", "lVm3ye", "r025kc", "hJNv6b", "Hdw6tb"]
_SNIPPET_CLASS_MARKER = 'class="VwiC3b yXK7lf lVm3ye r025kc hJNv6b Hdw6tb"'
_GOOGLE_NEWS_DOMAIN_LINK_CLASS = "WlydOe"


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

    # ----- internal helpers ------------------------------------------

    def _collect_candidates(self, headline: str) -> List[_Candidate]:
        soup = self._fetch_serp(headline)
        if soup is None:
            return []

        result_cards = soup.find_all("div", class_=_RESULT_CARD_CLASS)
        snippet_blocks = [
            div
            for div in soup.find_all("div", {"class": _SNIPPET_CLASSES})
            if _SNIPPET_CLASS_MARKER in str(div)
        ]
        log.debug(
            "SERP: %d result cards, %d snippets",
            len(result_cards),
            len(snippet_blocks),
        )

        candidates: List[_Candidate] = []
        for card, snippet_block in zip(result_cards, snippet_blocks):
            link = card.find("a")
            if link is None or not link.get("href"):
                continue
            url = link["href"]

            page_title = self._fetch_page_title(url)
            if page_title is None:
                continue

            domain = urlparse(url).netloc.replace("www.", "")
            if not self._domain_appears_in_google_news(domain):
                continue

            snippet_text = self._extract_snippet_text(snippet_block)
            candidates.append(
                _Candidate(url=url, title=page_title, snippet=snippet_text)
            )

        return candidates

    def _fetch_serp(self, query: str) -> Optional[BeautifulSoup]:
        url = f"https://www.google.com/search?q={query}"
        try:
            response = self._session.get(url, timeout=10)
        except requests.RequestException:
            log.exception("Google SERP request failed for query=%r", query)
            return None
        return BeautifulSoup(response.content, "html.parser")

    def _fetch_page_title(self, url: str) -> Optional[str]:
        try:
            response = self._session.get(
                url, timeout=self._settings.web_presence_request_timeout_s
            )
        except requests.RequestException:
            log.debug("Skipping unreachable URL %s", url)
            return None
        soup = BeautifulSoup(response.content, "html.parser")
        title_tag = soup.find("title")
        return title_tag.text if title_tag else None

    def _domain_appears_in_google_news(self, domain: str) -> bool:
        if not domain:
            return False
        url = f"https://www.google.com/search?q={domain}&tbm=nws"
        try:
            response = self._session.get(url, timeout=10)
        except requests.RequestException:
            log.debug("Google News check failed for %s", domain)
            return False
        soup = BeautifulSoup(response.content, "html.parser")
        link = soup.find("a", class_=_GOOGLE_NEWS_DOMAIN_LINK_CLASS)
        if link is None:
            return False
        link_domain = urlparse(link.get("href", "")).netloc.replace("www.", "")
        return domain in link_domain

    @staticmethod
    def _extract_snippet_text(snippet_block) -> str:
        spans = snippet_block.find_all("span")
        if len(spans) > 2:
            return spans[2].text
        if len(spans) > 1:
            return spans[1].text
        if spans:
            return spans[0].text
        return ""

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
            sim_snippet = cosine_similarity_score(headline, candidate.snippet)
            best_local = max(sim_title, sim_snippet)

            log.debug(
                "candidate %s -> sim_title=%.3f sim_snippet=%.3f",
                candidate.url,
                sim_title,
                sim_snippet,
            )

            if best_local > best_score:
                best_score = best_local
                best_candidate = candidate
            if best_local >= threshold:
                accepted_scores.append(best_local)

        if best_candidate is None or len(accepted_scores) < min_similar:
            return False, best_candidate, 0.0

        # Final LLM gate. Caller can disable by leaving ANTHROPIC_API_KEY blank,
        # but per project decision the LLM gate is required.
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
