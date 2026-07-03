/* Schedule Forensics — light/dark theme switch (fully local; preference in localStorage).
 *
 * Loaded synchronously in <head> so the saved theme applies before first paint (no flash
 * of the wrong theme). LIGHT is the default; "dark" is opted into via the header toggle.
 * Also stamps the header target-UID form with the current path so setting a target
 * returns you to the page you were on.
 */
"use strict";

(function () {
  var KEY = "sf-theme";
  var MODES = ["light", "dark", "jarvis"]; // cycle order; jarvis = the HUD skin (hud.css)
  var saved = null;
  try { saved = localStorage.getItem(KEY); } catch (e) { /* storage may be unavailable */ }
  // Light is the default: apply it on a first visit and whenever the saved choice isn't one of
  // the explicit non-light modes. "dark" leaves the document on the dark base theme; "jarvis"
  // stamps data-theme=jarvis (which INHERITS the dark tokens, then hud.css re-skins them).
  if (saved === "jarvis") {
    document.documentElement.setAttribute("data-theme", "jarvis");
  } else if (saved !== "dark") {
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
    var t = document.documentElement.getAttribute("data-theme");
    return t === "light" || t === "jarvis" ? t : "dark";
  }

  function label(btn) {
    // the button names the NEXT theme in the cycle (Light -> Dark -> JARVIS -> Light)
    var next = MODES[(MODES.indexOf(mode()) + 1) % MODES.length];
    btn.textContent = next === "dark" ? "\u263e Dark mode"
      : next === "jarvis" ? "\u2b21 JARVIS mode" : "\u2600 Light mode";
    btn.setAttribute("aria-label", "Switch theme (next: " + next + ")");
  }

  document.addEventListener("DOMContentLoaded", function () {
    var btn = document.getElementById("themeToggle");
    if (btn) {
      label(btn);
      btn.addEventListener("click", function () {
        var next = MODES[(MODES.indexOf(mode()) + 1) % MODES.length];
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
