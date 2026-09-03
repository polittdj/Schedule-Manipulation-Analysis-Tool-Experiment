/* Schedule Forensics — Mission Ops view switcher (fully local; preference in localStorage).
 *
 * Loaded synchronously in <head> so the saved view applies before first paint (no flash of
 * the wrong theme). Four complete views (ADR-0195): CONSOLE (dark mission control — the
 * default), DAYLIGHT (clean light), APOLLO (retro CRT) and JARVIS (the HUD skin, hud.css).
 * Legacy saves migrate: "light" -> "daylight", "dark" or anything unknown -> "console".
 * The header carries a View <select id=themeSelect>; the #themeToggle button round-trips
 * daylight <-> the last dark view. Also stamps the header target-UID form with the current
 * path so setting a target returns you to the page you were on.
 */
"use strict";

(function () {
  var KEY = "sf-theme";
  var DARK_KEY = "sf-theme-dark"; // the last non-daylight view, for the toggle round-trip
  var THEMES = ["console", "daylight", "apollo", "jarvis"];

  function stored(key) {
    try { return localStorage.getItem(key); } catch (e) { return null; }
  }
  function persist(key, value) {
    try { localStorage.setItem(key, value); } catch (e) { /* keep the in-page switch */ }
  }

  // Migrate the legacy three-mode save, then default to CONSOLE (never the OS setting —
  // the view is an explicit operator choice, applied identically on every machine).
  var saved = stored(KEY);
  var theme;
  if (saved === "light") theme = "daylight";
  else if (saved === "dark") theme = "console";
  else theme = THEMES.indexOf(saved) >= 0 ? saved : "console";

  function lastDark() {
    var d = stored(DARK_KEY);
    return THEMES.indexOf(d) >= 0 && d !== "daylight" ? d : "console";
  }

  function label(next) {
    return next.charAt(0).toUpperCase() + next.slice(1);
  }

  function reflect() {
    var sel = document.getElementById("themeSelect");
    if (sel) sel.value = theme;
    var btn = document.getElementById("themeToggle");
    if (btn) {
      // the button names the NEXT view: daylight <-> the last dark view
      var next = theme === "daylight" ? lastDark() : "daylight";
      btn.textContent = next === "daylight" ? "☀ Daylight" : "☾ " + label(next);
      btn.setAttribute("aria-label", "Switch theme (next: " + next + ")");
    }
  }

  function apply(next) {
    theme = THEMES.indexOf(next) >= 0 ? next : "console";
    document.documentElement.setAttribute("data-theme", theme);
    persist(KEY, theme);
    if (theme !== "daylight") persist(DARK_KEY, theme);
    reflect();
  }

  // pre-paint stamp (this script loads before the stylesheets); persist the migrated value
  // back so the saved choice is stable in the new four-view vocabulary
  document.documentElement.setAttribute("data-theme", theme);
  persist(KEY, theme);
  if (theme !== "daylight") persist(DARK_KEY, theme);

  // Page scale (operator: "rescale the whole page"). Applied in <head> before first paint so a
  // saved zoom doesn't reflow-flash. CSS `zoom` scales text AND layout together — the layout is
  // px-based, so this is the reliable whole-page rescale (a root font-size would miss the px rules).
  var SCALE_KEY = "sf-scale";
  try {
    var savedScale = localStorage.getItem(SCALE_KEY);
    if (savedScale) document.documentElement.style.zoom = savedScale;
  } catch (e) { /* storage may be unavailable */ }

  document.addEventListener("DOMContentLoaded", function () {
    var sel = document.getElementById("themeSelect");
    if (sel) {
      sel.addEventListener("change", function () { apply(sel.value); });
    }
    var btn = document.getElementById("themeToggle");
    if (btn) {
      btn.addEventListener("click", function () {
        apply(theme === "daylight" ? lastDark() : "daylight");
      });
    }
    reflect();

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
