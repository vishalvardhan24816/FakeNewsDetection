"""Check 3 - Subjectivity (transformer-based).

Real news headlines sound neutral and factual.
Opinions, personal statements, and rants do not.

We feed the headline to a small Hugging Face transformer model that was
already fine-tuned to label sentences as either:

    label 0  ->  subjective  (opinion / emotional)
    label 1  ->  objective   (neutral / factual)

The check passes when the model says "objective".
"""

import logging

import torch

from fakenews_detector.checks.base import Check, CheckResult
from fakenews_detector.models.loaders import get_subjectivity_model

log = logging.getLogger(__name__)


# These two numbers come from the trained model itself. We give them
# names here so the rest of the code reads in plain English.
SUBJECTIVE_LABEL = 0
OBJECTIVE_LABEL = 1


class SubjectivityCheck(Check):
    name = "subjectivity"

    def run(self, headline):
        # Step 1: Get the model and its tokenizer.
        # The first call loads them from disk (~1s); every later call
        # returns the cached copy.
        model, tokenizer = get_subjectivity_model()

        # Step 2: Turn the headline string into numbers the model can
        # understand. This step is called "tokenization".
        #   return_tensors="pt" -> give us PyTorch tensors back
        #   truncation=True     -> cut off if longer than the model's max
        #   padding=True        -> pad shorter inputs to a fixed length
        model_inputs = tokenizer(
            headline,
            padding=True,
            truncation=True,
            return_tensors="pt",
        )

        # Step 3: Ask the model for its prediction.
        # We're only doing inference (not training), so torch.no_grad()
        # tells PyTorch "don't track gradients" -- saves memory + is faster.
        with torch.no_grad():
            outputs = model(**model_inputs)

        # Step 4: The model returns one score per possible label.
        # Higher score = more confident in that label.
        # `outputs.logits` looks like [[score_for_subjective, score_for_objective]].
        # We pick whichever label has the highest score using argmax.
        scores = outputs.logits
        predicted_label = int(torch.argmax(scores).item())

        # Step 5: Convert the model's verdict into a pass/fail result.
        passed = predicted_label == OBJECTIVE_LABEL
        verdict = "objective" if passed else "subjective"

        log.info("subjectivity label=%d (%s)", predicted_label, verdict)

        return CheckResult(
            name=self.name,
            passed=passed,
            detail=verdict,
            metadata={"label": predicted_label},
        )
