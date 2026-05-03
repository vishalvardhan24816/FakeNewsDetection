"""Step 3 - subjectivity gate.

A transformer (the `lighteternal` model) classifies the headline as
subjective (label 0) or objective (label 1). News titles are expected
to be objective.
"""

from __future__ import annotations

import logging

import torch

from fakenews_detector.checks.base import Check, CheckResult
from fakenews_detector.models.loaders import get_subjectivity_model

log = logging.getLogger(__name__)


class SubjectivityCheck(Check):
    name = "subjectivity"

    def run(self, headline: str) -> CheckResult:
        model, tokenizer = get_subjectivity_model()
        inputs = tokenizer(
            headline, padding=True, truncation=True, return_tensors="pt"
        )

        with torch.no_grad():
            outputs = model(**inputs)
        label = int(torch.argmax(outputs.logits).item())

        is_objective = label != 0
        log.info("subjectivity label=%d (objective=%s)", label, is_objective)

        return CheckResult(
            name=self.name,
            passed=is_objective,
            detail="objective" if is_objective else "subjective",
            metadata={"label": label},
        )
