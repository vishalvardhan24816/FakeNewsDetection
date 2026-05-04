"""Tests for `fakenews_detector.checks.subjectivity`.

The check loads a Hugging Face transformer + tokenizer, runs the
headline through them, and reads the argmax of the model's logits to
decide subjective (label 0) vs objective (label 1).

We mock the model loader to return a tokenizer that returns a dict
(matching the real tokenizer's interface) and a model that returns a
fake `outputs` object with hand-crafted logits.
"""

from unittest.mock import MagicMock, patch

import pytest
import torch

from fakenews_detector.checks.subjectivity import SubjectivityCheck


def _fake_loader(logits_for_argmax):
    """Build a mocked (model, tokenizer) pair with predetermined logits.

    `logits_for_argmax` should be a list like `[score_subj, score_obj]`.
    Whichever index is bigger is what the model will "predict".
    """
    fake_tokenizer = MagicMock()
    fake_tokenizer.return_value = {"input_ids": "ANY", "attention_mask": "ANY"}

    fake_model = MagicMock()
    # The check reads outputs.logits; argmax across that tensor decides
    # the label.
    fake_outputs = MagicMock()
    fake_outputs.logits = torch.tensor([logits_for_argmax])
    fake_model.return_value = fake_outputs

    return fake_model, fake_tokenizer


class TestSubjectivityCheck:
    """Argmax of model logits decides PASS (objective) vs FAIL (subjective)."""

    def test_passes_when_model_predicts_objective(self):
        # logits[1] > logits[0] -> argmax = 1 = OBJECTIVE_LABEL.
        model, tok = _fake_loader([0.1, 5.0])

        with patch(
            "fakenews_detector.checks.subjectivity.get_subjectivity_model",
            return_value=(model, tok),
        ):
            result = SubjectivityCheck().run("ISRO launches Chandrayaan-3")

        assert result.name == "subjectivity"
        assert result.passed is True
        assert result.detail == "objective"
        assert result.metadata["label"] == 1

    def test_fails_when_model_predicts_subjective(self):
        # logits[0] > logits[1] -> argmax = 0 = SUBJECTIVE_LABEL.
        model, tok = _fake_loader([5.0, 0.1])

        with patch(
            "fakenews_detector.checks.subjectivity.get_subjectivity_model",
            return_value=(model, tok),
        ):
            result = SubjectivityCheck().run("I think Mondays are awful")

        assert result.passed is False
        assert result.detail == "subjective"
        assert result.metadata["label"] == 0
