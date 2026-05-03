// progress.js - poll the job status endpoint and update the UI in
// real time. Replaces the original fake CSS-only progress bar.

(function () {
    "use strict";

    const root = document.getElementById("progress-root");
    if (!root) {
        return;
    }

    const TOTAL_CHECKS = parseInt(root.dataset.totalChecks, 10) || 5;
    const POLL_INTERVAL_MS = 750;

    const statusUrl = root.dataset.statusUrl;
    const resultsUrl = root.dataset.resultsUrl;

    const progressBar = document.getElementById("progress-bar");
    const checkList = document.getElementById("check-list");

    function updateBar(completedCount, running) {
        // Each completed check fills 1/N of the bar; the in-flight one
        // contributes a half-step so the user sees motion.
        const completedPct = (completedCount / TOTAL_CHECKS) * 100;
        const runningPct = running ? (0.5 / TOTAL_CHECKS) * 100 : 0;
        const pct = Math.min(100, completedPct + runningPct);
        progressBar.style.width = pct.toFixed(1) + "%";
        progressBar.textContent = Math.round(pct) + "%";
        progressBar.setAttribute("aria-valuenow", String(Math.round(pct)));
    }

    function setRowState(row, state, badgeText) {
        const icon = row.querySelector(".status-icon");
        const badge = row.querySelector(".status-badge");
        icon.className = "me-2 status-icon";
        badge.className = "badge status-badge";

        if (state === "pending") {
            icon.classList.add("fas", "fa-circle", "text-muted");
            badge.classList.add("bg-secondary");
        } else if (state === "running") {
            icon.classList.add("fas", "fa-circle-notch", "fa-spin", "text-primary");
            badge.classList.add("bg-primary");
        } else if (state === "passed") {
            icon.classList.add("fas", "fa-check-circle", "text-success");
            badge.classList.add("bg-success");
        } else if (state === "failed") {
            icon.classList.add("fas", "fa-times-circle", "text-danger");
            badge.classList.add("bg-danger");
        }
        badge.textContent = badgeText;
    }

    function applyJobState(job) {
        const completedNames = new Set(job.results.map((r) => r.name));
        const resultsByName = Object.fromEntries(
            job.results.map((r) => [r.name, r])
        );
        const rows = checkList.querySelectorAll("li[data-check]");

        rows.forEach((row) => {
            const name = row.dataset.check;
            if (completedNames.has(name)) {
                const r = resultsByName[name];
                setRowState(row, r.passed ? "passed" : "failed", r.passed ? "pass" : "fail");
            } else if (job.current_check === name) {
                setRowState(row, "running", "running");
            } else {
                setRowState(row, "pending", "pending");
            }
        });

        updateBar(job.results.length, job.status === "running");
    }

    function poll() {
        fetch(statusUrl, { headers: { Accept: "application/json" } })
            .then((res) => {
                if (!res.ok) {
                    throw new Error("HTTP " + res.status);
                }
                return res.json();
            })
            .then((job) => {
                applyJobState(job);
                if (job.status === "done" || job.status === "error") {
                    // Brief pause so the user sees the final tick, then
                    // navigate to the full results page.
                    setTimeout(() => {
                        window.location.href = resultsUrl;
                    }, 600);
                    return;
                }
                setTimeout(poll, POLL_INTERVAL_MS);
            })
            .catch((err) => {
                console.error("Progress poll failed", err);
                setTimeout(poll, POLL_INTERVAL_MS * 2);
            });
    }

    poll();
})();
