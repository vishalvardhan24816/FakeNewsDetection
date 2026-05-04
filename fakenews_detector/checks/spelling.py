"""Check 1 - Spelling.

A real news headline shouldn't have many typos. We:

1. Run a Named-Entity-Recognition (NER) model first to find names of
   people and places. We DON'T spell-check those, because words like
   "Modi" or "Tokyo" aren't in the dictionary.
2. For every other alphabetic word, ask the spell checker if it has a
   correction. If the corrected word differs from the original, count
   it as a misspelling.
3. Pass if (misspelled / total words) is below the configured threshold.
"""

import logging

from spellchecker import SpellChecker

from fakenews_detector.checks.base import Check, CheckResult
from fakenews_detector.config import get_settings
from fakenews_detector.models.loaders import get_ner_pipeline
from fakenews_detector.nlp.preprocessing import normalize_for_spellcheck

log = logging.getLogger(__name__)


class SpellingCheck(Check):
    name = "spelling"

    # Common informal spellings the open-source SpellChecker doesn't fix
    # well on its own. The original code special-cased these too.
    _OWN_CORRECTIONS = {"iam": "i'm", "im": "i'm"}

    def run(self, headline):
        cleaned = normalize_for_spellcheck(headline)
        tokens = cleaned.split(" ")
        named_entities = self._extract_named_entities(cleaned)

        spell = SpellChecker()
        misspelled = []
        corrected_tokens = []

        for token in tokens:
            # Skip non-alphabetic tokens and any word the NER model said
            # is a person or location.
            if (token.isalpha() and token in named_entities):
                corrected_tokens.append(token)
                continue

            # Hand-rolled fixes for cases the library misses.
            if token in self._OWN_CORRECTIONS:
                misspelled.append(token)
                corrected_tokens.append(self._OWN_CORRECTIONS[token])
                continue

            # Ask the spell checker for a correction. If it differs from
            # the original word, that means the original was a typo.
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
            len(misspelled), word_count, ratio, threshold,
        )

        if not misspelled:
            detail = "no spelling issues"
        else:
            detail = (
                f"{len(misspelled)} misspelled token(s) "
                f"(ratio {ratio:.2f} vs threshold {threshold:.2f})"
            )

        return CheckResult(
            name=self.name,
            passed=passed,
            detail=detail,
            metadata={
                "misspelled": sorted(set(misspelled)),
                "corrected": " ".join(corrected_tokens),
                "ratio": ratio,
            },
        )

    @staticmethod
    def _extract_named_entities(cleaned_lowercase_text):
        """Run NER and return the set of words tagged as a Person or Location."""
        # The NER model expects properly-cased tokens, so capitalize each word first.
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
