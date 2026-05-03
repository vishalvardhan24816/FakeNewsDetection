// app.js - shared client-side helpers.
// Bootstrap 5 handles the navbar toggle natively, so this file is
// intentionally tiny. Add anything global here as the UI grows.

(function () {
    "use strict";

    // Auto-focus the headline textarea on the detect page if present.
    const headline = document.getElementById("headline");
    if (headline) {
        headline.focus();
    }
})();
