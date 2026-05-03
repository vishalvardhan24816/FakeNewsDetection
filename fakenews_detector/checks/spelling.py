"""Step 1 - spelling/grammar gate.

Strategy
--------
1. Detect named entities (people, locations) with a NER pipeline so
   they're not flagged as misspellings.
2. For every other alphabetic token, compare against
   :class:`spellchecker.SpellChecker`'s correction.
3. Pass if (misspelled / total) is below a configurable threshold.
"""

from __future__ import annotations

import logging
from typing import Dict, List

from spellchecker import SpellChecker

from fakenews_detector.checks.base import Check, CheckResult
from fakenews_detector.config import get_settings
from fakenews_detector.models.loaders import get_ner_pipeline
from fakenews_detector.nlp.preprocessing import normalize_for_spellcheck

log = logging.getLogger(__name__)


class SpellingCheck(Check):
    name = "spelling"

    # A handful of casual spellings the open-source SpellChecker doesn't
    # normalize; the original code special-cased these.
    _OWN_CORRECTIONS: Dict[str, str] = {"iam": "i'm", "im": "i'm"}

    def run(self, headline: str) -> CheckResult:
        cleaned = normalize_for_spellcheck(headline)
        tokens = cleaned.split(" ")
        named_entities = self._extract_named_entities(cleaned)

        spell = SpellChecker()
        misspelled: List[str] = []
        corrected_tokens: List[str] = []

        for token in tokens:
            if not (token.isalpha() and token not in named_entities):
                corrected_tokens.append(token)
                continue

            if token in self._OWN_CORRECTIONS:
                misspelled.append(token)
                corrected_tokens.append(self._OWN_CORRECTIONS[token])
                continue

            corrected = spell.correction(token)
            if corrected and corrected != token:
                misspelled.append(token)
                corrected_tokens.append(corrected)
            else:
                corrected_tokens.append(token)

        word_count = max(len(headline.split(" ")), 1)
        ratio = len(misspelled) / word_count
        threshold = get_settings().spelling_max_misspell_ratio
        passed = (len(misspelled) == 0) or (ratio < threshold)

        log.info(
            "spelling: %d misspelled / %d words (ratio=%.2f, threshold=%.2f)",
            len(misspelled),
            word_count,
            ratio,
            threshold,
        )

        return CheckResult(
            name=self.name,
            passed=passed,
            detail=(
                "no spelling issues"
                if not misspelled
                else f"{len(misspelled)} misspelled token(s) "
                f"(ratio {ratio:.2f} vs threshold {threshold:.2f})"
            ),
            metadata={
                "misspelled": sorted(set(misspelled)),
                "corrected": " ".join(corrected_tokens),
                "ratio": ratio,
            },
        )

    @staticmethod
    def _extract_named_entities(cleaned_lowercase_text: str) -> set:
        # The NER model expects properly-cased tokens.
        capitalised = " ".join(t.capitalize() for t in cleaned_lowercase_text.split())
        try:
            ner_results = get_ner_pipeline()(capitalised)
        except Exception:
            log.exception("NER pipeline failed; treating no tokens as named entities")
            return set()
        return {
            ent["word"].lower()
            for ent in ner_results
            if ent.get("entity_group") in {"PER", "LOC"}
        }
