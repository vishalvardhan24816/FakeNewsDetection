# Fake News Detector

A 5-step rule-based validator for news headlines. Instead of training a
single end-to-end "is this fake" model, it runs five independent gates
in sequence and only marks a headline as **real** if it passes all
five.

This repository is a refactor of an older (2023) college project. The
original code lives untouched in [`archive/`](archive/) for reference;
the active package is [`fakenews_detector/`](fakenews_detector/).

## The 5 checks

| # | Check               | Module                                          | What it does                                                                                |
| - | ------------------- | ----------------------------------------------- | ------------------------------------------------------------------------------------------- |
| 1 | Spelling            | `fakenews_detector.checks.SpellingCheck`        | NER-aware spell-checker; fails if too many misspellings                                     |
| 2 | Clickbait           | `fakenews_detector.checks.ClickbaitCheck`       | Custom-trained TF-IDF + classifier predicts clickbait vs. not                               |
| 3 | Subjectivity        | `fakenews_detector.checks.SubjectivityCheck`    | Transformer (`lighteternal`) predicts subjective vs. objective                              |
| 4 | Is news title       | `fakenews_detector.checks.NewsTitleCheck`       | Custom classifier predicts news-title vs. statement                                         |
| 5 | Web presence        | `fakenews_detector.checks.WebPresenceCheck`     | Google search + sentence similarity + Anthropic Claude as the final contextual-match gate   |

If any check fails, validation short-circuits and the headline is
flagged as fake / unverified.

## Quick start

### 1. Install

```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure

Copy `.env.example` to `.env` and fill in at minimum:

```env
ANTHROPIC_API_KEY=sk-ant-...
```

The Anthropic key is required because check #5 uses Claude as the
final contextual-similarity gate.

### 3. Obtain the model artifacts

The model files are intentionally **not** tracked in git (they're
multiple GB total). You need them on disk before the validator can
run. The expected layout is:

```text
basenlimean/         # sentence-transformers model snapshot (~440 MB)
dbmbz/               # NER model snapshot (~1.3 GB)
lighteternal/        # subjectivity model snapshot (~1.1 GB)
mlmodels/
    impclickbait.pkl
    wewill.pkl
vectorizers/
    vectorizer.pkl
    wevec.pkl
```

You can either:

- **Restore them from your original local copy** (most common - they
  already exist alongside the project, just not in git), or
- **Re-train the custom classifiers** by running the training script:

  ```powershell
  python -m training.train_clickbait
  ```

  (Only the clickbait model has a training script in this repo. The
  other `.pkl` files were trained against datasets and scripts that
  weren't migrated.)

### 4. Use it

```python
from fakenews_detector import FakeNewsValidator
from fakenews_detector.logging_setup import configure_logging

configure_logging()

report = FakeNewsValidator("ISRO successfully lands Chandrayaan-3").validate()

print(report)            # human-readable summary
print(report.passed_all) # True / False
for r in report.results:
    print(r.name, r.passed, r.detail, r.metadata)
```

By default validation stops at the first failed check. Pass
`stop_on_first_failure=False` to always run every check:

```python
FakeNewsValidator(headline, stop_on_first_failure=False).validate()
```

You can also override which checks run (e.g. skip the slow
web-presence step):

```python
from fakenews_detector.checks import (
    SpellingCheck, ClickbaitCheck, SubjectivityCheck, NewsTitleCheck
)

FakeNewsValidator(headline, checks=[
    SpellingCheck(), ClickbaitCheck(),
    SubjectivityCheck(), NewsTitleCheck(),
]).validate()
```

## Project layout

```text
fakenews_detector/
    __init__.py            # public API
    config.py              # Settings dataclass + .env loading
    logging_setup.py
    validator.py           # FakeNewsValidator + ValidationReport
    checks/
        base.py            # Check ABC, CheckResult dataclass
        spelling.py
        clickbait.py
        subjectivity.py
        news_title.py
        web_presence.py
    nlp/
        preprocessing.py   # shared tokenize/clean/lemmatize (deduped)
        similarity.py      # cosine + Anthropic verifier
    models/
        loaders.py         # cached singleton model loaders

training/
    train_clickbait.py     # rebuild mlmodels/clickbaitmodel.pkl

archive/                   # original 3-year-old code (preserved, not used)
datasets/                  # CSVs used by the training scripts
mlmodels/                  # trained .pkl artifacts (gitignored)
vectorizers/               # fitted vectorizers (gitignored)
basenlimean/, dbmbz/, lighteternal/   # HF model snapshots (gitignored)

.env.example, .gitignore, requirements.txt, pyproject.toml
```

## Known limitations

- **Google scrape selectors are stale.** The web-presence check uses
  CSS class names (`yuRUbf`, `VwiC3b`, ...) that were valid in 2023.
  Google rotates these often, so this check may need its selectors
  re-identified to actually return matches today. The fallback path
  reports "no corroborating results" rather than crashing.
- **Heavyweight first call.** First call to each check loads its
  model into memory; subsequent calls reuse it (this is a big
  improvement over the original, which reloaded models on every
  request).
- **Anthropic API required for check #5.** No local-only fallback by
  design.

## What changed in the refactor

See [`archive/README.md`](archive/README.md) for the old → new
mapping. Highlights:

- Single 230-line `checkTitle` god-class → 5 small `Check` subclasses
- Duplicated preprocessing in `clickbait.py` and `isnewstitle.py`
  → one shared `nlp.preprocessing` module
- Models reloaded on every call → cached singletons
- Hardcoded API keys / passwords → `.env` (and scrubbed from history)
- Globals + bare `except:` + `print` → typed dataclasses + targeted
  exceptions + structured `logging`
- Flask UI / chatbot / OCR / URL-security / social-DM features moved
  to `archive/` (out of scope for this refactor)
