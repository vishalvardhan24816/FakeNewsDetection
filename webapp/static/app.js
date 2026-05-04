// app.js - shared client-side helpers.

(function () {
    "use strict";

    // Auto-focus the headline textarea on the detect page if present.
    const headline = document.getElementById("headline");
    if (headline) {
        headline.focus();
    }

    const setCheckEnabled = (name, enabled) => {
        const el = document.getElementById("check_" + name);
        if (el) {
            el.value = enabled ? "1" : "";
        }
    };
    document.querySelectorAll("[data-skips]").forEach((shortcut) => {
        const skips = (shortcut.getAttribute("data-skips") || "")
            .split(/\s+/)
            .filter(Boolean);
        shortcut.addEventListener("change", () => {
            const skip = shortcut.checked;
            skips.forEach((name) => setCheckEnabled(name, !skip));
        });
    });

    // ---- In-flight per-check progress UX -------------------------------
    // The /detect POST is synchronous on the server side. While the
    // browser tab is waiting for the response, we play a scripted
    // reveal of the validation pipeline so the user understands what's
    // happening. Timings are rough estimates of typical per-check
    // latency; accuracy doesn't matter since the page navigates away
    // the moment the real response arrives.
    //
    // Steps that are toggled off (hidden input value === "") are
    // marked "skipped" up front and not animated.
    const detectForm = document.getElementById("detectForm");
    const progressEl = document.getElementById("checkProgress");

    if (detectForm && progressEl) {
        // (check name, expected duration ms, optional sub-step labels
        // that rotate while this step is "running"). web_presence is
        // capped at the bottom because the LLM call is the slowest
        // and most variable - we let it sit on the final substep until
        // the page navigates.
        // Per-step animation durations (ms). Tuned to fit the first 4
        // checks inside the backend's ~5s minimum response time so the
        // user always sees the full pre-web-presence pipeline play out
        // even when validation fails fast.
        const PIPELINE = [
            { check: "spelling",     duration: 1100 },
            { check: "clickbait",    duration: 600  },
            { check: "subjectivity", duration: 1300 },
            { check: "news_title",   duration: 600  },
            {
                check: "web_presence",
                substeps: [
                    { at: 0,    text: "Searching trusted news sources\u2026" },
                    { at: 3500, text: "Computing semantic similarity\u2026" },
                    { at: 7000, text: "Asking the LLM to confirm the match\u2026" },
                ],
            },
        ];

        const isCheckEnabled = (name) => {
            const el = document.getElementById("check_" + name);
            return el && el.value === "1";
        };

        const runPipelineAnimation = () => {
            progressEl.hidden = false;

            // Mark disabled checks as "skipped" up front.
            PIPELINE.forEach((step) => {
                const row = progressEl.querySelector(
                    `.progress-step[data-check="${step.check}"]`
                );
                if (!row) return;
                if (!isCheckEnabled(step.check)) {
                    row.classList.add("is-skipped");
                }
            });

            const runSteps = PIPELINE.filter((s) => isCheckEnabled(s.check));
            let i = 0;

            const advance = () => {
                if (i >= runSteps.length) return;
                const step = runSteps[i];
                const row = progressEl.querySelector(
                    `.progress-step[data-check="${step.check}"]`
                );
                if (!row) {
                    i += 1;
                    advance();
                    return;
                }

                row.classList.add("is-running");

                // Rotate sub-step labels (only web_presence has these).
                if (step.substeps) {
                    const subEl = row.querySelector("[data-substep]");
                    step.substeps.forEach((sub) => {
                        setTimeout(() => {
                            if (row.classList.contains("is-running") && subEl) {
                                subEl.textContent = sub.text;
                            }
                        }, sub.at);
                    });
                }

                // Don't auto-complete the LAST step - keep it spinning
                // until the page navigates. The real backend may take
                // longer than our estimate and we'd rather under-promise.
                const isLast = i === runSteps.length - 1;
                if (!isLast) {
                    setTimeout(() => {
                        row.classList.remove("is-running");
                        row.classList.add("is-done");
                        i += 1;
                        advance();
                    }, step.duration);
                }
            };

            advance();
        };

        detectForm.addEventListener("submit", () => {
            detectForm.classList.add("is-verifying");
            const btn = detectForm.querySelector("button[type='submit']");
            if (btn) {
                btn.disabled = true;
                btn.innerHTML =
                    '<span class="spinner-border spinner-border-sm me-2" ' +
                    'role="status" aria-hidden="true"></span>' +
                    "Verifying\u2026";
            }
            runPipelineAnimation();
            // Smooth-scroll the progress block into view on small screens.
            setTimeout(() => {
                progressEl.scrollIntoView({ behavior: "smooth", block: "nearest" });
            }, 50);
        });
    }
})();
