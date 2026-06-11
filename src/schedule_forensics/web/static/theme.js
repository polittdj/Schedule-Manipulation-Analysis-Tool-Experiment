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
  if (saved === "light") document.documentElement.setAttribute("data-theme", "light");

  function mode() {
    return document.documentElement.getAttribute("data-theme") === "light" ? "light" : "dark";
  }

  function label(btn) {
    btn.textContent = mode() === "light" ? "☾ Dark mode" : "☀ Light mode";
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
    // the target form returns to the page it was submitted from
    var back = document.querySelector(".targetform input[name=next_url]");
    if (back) back.value = location.pathname + location.search;
  });
})();
