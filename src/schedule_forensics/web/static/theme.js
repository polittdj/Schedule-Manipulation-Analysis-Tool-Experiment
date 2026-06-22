/* Schedule Forensics — light/dark theme switch (fully local; preference in localStorage).
 *
 * Loaded synchronously in <head> so the saved theme applies before first paint (no flash
 * of the wrong theme). Dark is the default; "light" is opted into via the header toggle.
 * Also stamps the header target-UID form with the current path so setting a target
 * returns you to the page you were on.
 */
"use strict";

(function () {
  var KEY = "sf-theme";
  var saved = null;
  try { saved = localStorage.getItem(KEY); } catch (e) { /* storage may be unavailable */ }
  // A10: a saved choice always wins; on a FIRST visit (no saved preference) follow the OS color
  // scheme instead of hardcoding dark, so the tool respects prefers-color-scheme.
  var prefersLight =
    window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches;
  if (saved === "light" || (!saved && prefersLight)) {
    document.documentElement.setAttribute("data-theme", "light");
  }

  // Page scale (operator: "rescale the whole page"). Applied in <head> before first paint so a
  // saved zoom doesn't reflow-flash. CSS `zoom` scales text AND layout together — the layout is
  // px-based, so this is the reliable whole-page rescale (a root font-size would miss the px rules).
  var SCALE_KEY = "sf-scale";
  try {
    var savedScale = localStorage.getItem(SCALE_KEY);
    if (savedScale) document.documentElement.style.zoom = savedScale;
  } catch (e) { /* storage may be unavailable */ }

  function mode() {
    return document.documentElement.getAttribute("data-theme") === "light" ? "light" : "dark";
  }

  function label(btn) {
    var light = mode() === "light";
    btn.textContent = light ? "☾ Dark mode" : "☀ Light mode";
    btn.setAttribute("aria-pressed", light ? "true" : "false"); // A10: announce toggle state
  }

  document.addEventListener("DOMContentLoaded", function () {
    var btn = document.getElementById("themeToggle");
    if (btn) {
      label(btn);
      btn.addEventListener("click", function () {
        var next = mode() === "light" ? "dark" : "light";
        document.documentElement.setAttribute("data-theme", next);
        try { localStorage.setItem(KEY, next); } catch (e) { /* keep the in-page switch */ }
        label(btn);
      });
    }
    // page-scale selector: reflect the saved zoom, apply + persist on change
    var scaleSel = document.getElementById("uiScale");
    if (scaleSel) {
      var cur = "1";
      try { cur = localStorage.getItem(SCALE_KEY) || "1"; } catch (e) { /* default 100% */ }
      scaleSel.value = cur;
      scaleSel.addEventListener("change", function () {
        document.documentElement.style.zoom = scaleSel.value;
        try { localStorage.setItem(SCALE_KEY, scaleSel.value); } catch (e) { /* in-page only */ }
      });
    }

    // the target form returns to the page it was submitted from
    var back = document.querySelector(".targetform input[name=next_url]");
    if (back) back.value = location.pathname + location.search;
  });
})();
