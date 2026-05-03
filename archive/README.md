# Archive

This folder contains the original 3-year-old code from before the
refactor. It's preserved here for reference but is **not** imported by
the active `fakenews_detector` package.

## What lives here

| File / dir                    | Original purpose                                     |
| ----------------------------- | ---------------------------------------------------- |
| `prog.py`                     | Original Flask web app (entry point)                 |
| `titletest.py`                | Original 5-step `checkTitle` orchestrator            |
| `clickbait.py`                | Original clickbait check (now in `checks/clickbait`) |
| `clickbait_model.py`          | Original training script (now `training/train_clickbait`) |
| `isnewstitle.py`              | Original news-title check                            |
| `subjectivemodel.py`          | Original subjectivity check                          |
| `similarity.py`               | Original sentence-similarity helper                  |
| `right.py`                    | Original Anthropic-based contextual match            |
| `chatbot.py`, `questionanswer.py` | FAQ chatbot                                      |
| `newsfeed.py`                 | Google News feed wrapper                             |
| `urlsecurity.py`              | SSL / whois / domain-age URL safety check            |
| `contactmail.py`, `sendmessage.py` | "Email/DM the source" notification feature      |
| `countrycodes.py`             | ISO country lookup table for the news feed           |
| `templates/`, `static/`       | Flask UI assets                                      |
| `main.py`                     | 350+ lines of commented-out one-off scratch scripts  |

## Mapping to the new package

| Old                                           | New                                              |
| --------------------------------------------- | ------------------------------------------------ |
| `titletest.checkTitle`                        | `fakenews_detector.FakeNewsValidator`            |
| `titletest.checkTitle.spelling_mistakes`      | `fakenews_detector.checks.SpellingCheck`         |
| `titletest.checkTitle.classify_clickbait`     | `fakenews_detector.checks.ClickbaitCheck`        |
| `titletest.checkTitle.subjective_test`        | `fakenews_detector.checks.SubjectivityCheck`     |
| `titletest.checkTitle.is_newstitle`           | `fakenews_detector.checks.NewsTitleCheck`        |
| `titletest.checkTitle.present_on_google`      | `fakenews_detector.checks.WebPresenceCheck`      |
| `right.check_similarity6`                     | `fakenews_detector.nlp.similarity.llm_contextual_match` |
| `similarity.calculate_sentence_similarity`    | `fakenews_detector.nlp.similarity.cosine_similarity_score` |
| Duplicated preprocessing in clickbait/isnewstitle | `fakenews_detector.nlp.preprocessing`        |
| `clickbait_model.py` (training)               | `training/train_clickbait.py`                    |

## Important notes

- **Hardcoded credentials have been removed** from these archived
  files (Anthropic key, HuggingFace token, Gmail SMTP password,
  Instagram/Twitter/Facebook account passwords). They were replaced
  with `os.environ.get(...)` lookups before this folder was committed
  to git, so no secrets exist anywhere in the repo's history.
- The old code uses heavy global state, reloads ML models on every
  call, has bare `except:` blocks, and prints instead of logging. The
  new package fixes all of that.
- The Google search scrape selectors here (and in the new
  `WebPresenceCheck`) are 2023-vintage and may need updating to work
  against today's Google HTML.
