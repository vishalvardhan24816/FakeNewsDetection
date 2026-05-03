"""Tiny in-memory job registry + background validation runner.

This replaces the original Flask app's module-level globals
(``headline``, ``index``, ``processes``, ``names``, ``pages``) which
were mutated across requests and were not thread-safe. Each
validation request now creates a self-contained :class:`Job` keyed by
a UUID; the browser polls for its status.

For a personal demo or a single-user deployment this is plenty. For
a real multi-user production setup you'd back this with Redis + RQ
or Celery instead.
"""

from __future__ import annotations

import logging
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Sequence

from fakenews_detector import CheckResult, FakeNewsValidator
from fakenews_detector.checks import (
    ClickbaitCheck,
    NewsTitleCheck,
    SpellingCheck,
    SubjectivityCheck,
    WebPresenceCheck,
)

log = logging.getLogger(__name__)

JOB_PENDING = "pending"
JOB_RUNNING = "running"
JOB_DONE = "done"
JOB_ERROR = "error"

# Mapping of form-friendly check name -> Check class. The order here is
# the canonical pipeline order; routes.py iterates this to read form
# checkboxes in a deterministic sequence.
ALL_CHECKS: Dict[str, type] = {
    "spelling": SpellingCheck,
    "clickbait": ClickbaitCheck,
    "subjectivity": SubjectivityCheck,
    "news_title": NewsTitleCheck,
    "web_presence": WebPresenceCheck,
}


@dataclass
class Job:
    """The full state of one validation request."""

    id: str
    headline: str
    check_names: List[str] = field(default_factory=list)
    status: str = JOB_PENDING
    current_check: Optional[str] = None
    results: List[CheckResult] = field(default_factory=list)
    error: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None

    @property
    def passed_all(self) -> bool:
        return (
            self.status == JOB_DONE
            and bool(self.results)
            and all(r.passed for r in self.results)
        )

    def to_dict(self) -> dict:
        d = asdict(self)
        # `results` contains CheckResult dataclasses; asdict already turned
        # them into plain dicts, but the default JSON encoder doesn't know
        # how to serialise sets etc. so coerce metadata values.
        for r in d["results"]:
            r["metadata"] = {k: _jsonable(v) for k, v in r["metadata"].items()}
        d["passed_all"] = self.passed_all
        return d


def _jsonable(value):
    if isinstance(value, (set, frozenset)):
        return sorted(value)
    return value


class JobRegistry:
    """Thread-safe job store + background runner.

    Holds at most ``max_size`` jobs in memory. Old jobs are evicted
    FIFO to keep the process from leaking memory if the server stays
    up indefinitely.
    """

    def __init__(self, max_size: int = 64) -> None:
        self._jobs: Dict[str, Job] = {}
        self._order: List[str] = []
        self._lock = threading.Lock()
        self._max_size = max_size

    # ----- public API -------------------------------------------------

    def get(self, job_id: str) -> Optional[Job]:
        with self._lock:
            return self._jobs.get(job_id)

    def submit(
        self, headline: str, *, check_names: Optional[Sequence[str]] = None
    ) -> Job:
        """Create a new job and start it on a background thread.

        Parameters
        ----------
        headline:
            The text to validate.
        check_names:
            Subset of :data:`ALL_CHECKS` keys to run, in pipeline order.
            ``None`` (the default) runs all five checks.

        Raises
        ------
        ValueError
            If ``check_names`` is empty or contains an unknown check.
        """
        selected = list(check_names) if check_names is not None else list(ALL_CHECKS)
        if not selected:
            raise ValueError("At least one check must be selected.")
        unknown = [n for n in selected if n not in ALL_CHECKS]
        if unknown:
            raise ValueError(f"Unknown check(s): {unknown}")

        # Always emit checks in the canonical pipeline order, regardless
        # of the order the caller listed them in.
        ordered = [n for n in ALL_CHECKS if n in selected]

        job = Job(
            id=uuid.uuid4().hex,
            headline=headline,
            check_names=ordered,
        )
        with self._lock:
            self._jobs[job.id] = job
            self._order.append(job.id)
            self._evict_if_needed()

        thread = threading.Thread(
            target=self._run_job, args=(job,), name=f"validate-{job.id[:8]}", daemon=True
        )
        thread.start()
        return job

    # ----- internals --------------------------------------------------

    def _evict_if_needed(self) -> None:
        while len(self._order) > self._max_size:
            oldest = self._order.pop(0)
            self._jobs.pop(oldest, None)

    def _run_job(self, job: Job) -> None:
        log.info("Starting job %s for headline=%r", job.id, job.headline)
        with self._lock:
            job.status = JOB_RUNNING
            job.started_at = _utcnow()

        try:
            # We construct a validator restricted to the requested
            # checks and run each one manually so we can publish
            # per-check progress (which the wrapper validate() doesn't
            # expose).
            check_instances = [ALL_CHECKS[name]() for name in job.check_names]
            validator = FakeNewsValidator(
                job.headline,
                checks=check_instances,
                stop_on_first_failure=True,
            )
            for check in validator._checks:
                with self._lock:
                    job.current_check = check.name
                log.info("Job %s running check=%s", job.id, check.name)
                try:
                    result = check.run(job.headline)
                except Exception as exc:
                    log.exception("Check %s crashed in job %s", check.name, job.id)
                    result = CheckResult(
                        name=check.name,
                        passed=False,
                        detail=f"check crashed: {exc!r}",
                    )
                with self._lock:
                    job.results.append(result)
                if not result.passed:
                    log.info("Job %s short-circuiting after fail at %s", job.id, check.name)
                    break
        except Exception as exc:
            log.exception("Job %s failed unexpectedly", job.id)
            with self._lock:
                job.status = JOB_ERROR
                job.error = repr(exc)
                job.finished_at = _utcnow()
                job.current_check = None
            return

        with self._lock:
            job.status = JOB_DONE
            job.finished_at = _utcnow()
            job.current_check = None


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
