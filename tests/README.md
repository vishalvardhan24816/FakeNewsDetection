# Test suite

86 fast, hermetic tests covering the entire project. The whole suite
runs in under 6 seconds because **no real ML model ever loads** during
tests -- every heavy dependency is mocked.

## Quick start

```bash
# 1. install pytest into your venv (one-time)
pip install pytest

# 2. from the project root, run everything
pytest

# Common variations
pytest -v                       # show every test name
pytest tests/unit/checks/       # run a subdirectory
pytest -k clickbait             # run tests whose name matches "clickbait"
pytest --tb=short               # shorter tracebacks on failure
```

## Layout

```
tests/
├── conftest.py                       <- shared fixtures (make_fake_check)
├── unit/
│   ├── test_config.py                <- Settings + resolve_llm_provider
│   ├── test_validator.py             <- FakeNewsValidator orchestration
│   ├── nlp/
│   │   ├── test_preprocessing.py     <- normalize_for_classifier / spellcheck
│   │   └── test_similarity.py        <- cosine + LLM gate dispatcher
│   └── checks/
│       ├── test_base.py              <- CheckResult dataclass + Check base
│       ├── test_spelling.py          <- mocked NER, real pyspellchecker
│       ├── test_clickbait.py         <- mocked classifier + vectorizer
│       ├── test_news_title.py        <- mocked classifier + vectorizer
│       ├── test_subjectivity.py      <- mocked HF model + tokenizer
│       └── test_web_presence.py      <- mocked HTTP + similarity + LLM
└── webapp/
    ├── conftest.py                   <- Flask test client fixture
    ├── test_app_factory.py           <- create_app builds correctly
    └── test_routes.py                <- /, /about, /detect (GET + POST)
```

## Design rules

1. **No real models in tests.** Tests must run in seconds, not minutes.
   Every model loader (`get_clickbait_classifier`, `get_subjectivity_model`,
   `get_sentence_embedder`, etc.) is patched out per-test using
   `unittest.mock.patch`.

2. **No real network calls.** The web-presence tests patch
   `requests.Session.get` and the similarity functions. The LLM gate
   tests patch `_call_gemini` / `_call_anthropic` directly.

3. **Tests should be readable line-by-line.** Each test has a one-line
   docstring saying what behavior it locks down, and tests group into
   classes named after the unit-under-test.

4. **`conftest.py` is auto-loaded.** Anything declared as a fixture
   there is available by name in every test under that folder. The
   shared `make_fake_check` factory is in the root `tests/conftest.py`.

## Why no integration tests against real models?

Two reasons:

1. They'd require ~3 GB of model artifacts on disk (gitignored, see
   the project README).
2. They'd take ~30 seconds per test instead of milliseconds.

The unit tests verify each component in isolation. If you want to do
an end-to-end smoke test with real models, just run
`python run_webapp.py` and submit a headline through the UI.

## Adding a new test

1. Find the right file under `tests/`. If you're testing a new module,
   mirror the source path: `fakenews_detector/foo/bar.py` -> `tests/unit/foo/test_bar.py`.
2. Group tests into classes named `Test<UnitName>`. Each test method
   starts with `test_` and is a single behavior.
3. If you depend on something heavy, mock it. Look at any existing
   test for the patching pattern.
4. Run `pytest <new_file>` to verify it passes locally.
