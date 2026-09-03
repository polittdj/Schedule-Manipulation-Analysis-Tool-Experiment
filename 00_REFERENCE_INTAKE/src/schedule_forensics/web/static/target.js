/* Schedule Forensics — keep the Target-UID form on the current page.
 *
 * The header's "Target UID" form posts to /target, which redirects to its `next_url`. That
 * hidden field shipped hardcoded to "/", so setting a target always bounced the analyst to the
 * dashboard (which doesn't reflect the target) — making it look like nothing changed. This sets
 * `next_url` to the current page, so after Set you stay put and immediately see the effect on
 * the pages that key off the target (analysis, trend, path, evolution, compare, card, WBS).
 * Dependency-free; same-origin only.
 */
"use strict";

(function () {
  var forms = document.querySelectorAll("form.targetform");
  if (!forms.length) return;
  function here() {
    return location.pathname + location.search;
  }
  forms.forEach(function (form) {
    var hidden = form.querySelector("input[name=next_url]");
    if (!hidden) return;
    hidden.value = here();
    form.addEventListener("submit", function () { hidden.value = here(); });
  });
})();
