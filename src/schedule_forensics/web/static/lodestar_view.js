/* LODESTAR — the view switch (ADR-0543). Loaded synchronously in <head>, before any stylesheet
 * paints, so the saved view applies on the first frame (no flash of the wrong one).
 *
 * Four views, one token set (static/lodestar_tokens.css): DARK (the default), BRIGHT, HIGH
 * CONTRAST and CONSOLE (opt-in; never carried into an export or a print). The choice lives in
 * this browser's localStorage under LODESTAR's own key — never Polaris²'s "sf-theme", whose four
 * names are another program's — and LODESTAR's fixed preferred port (47810) keeps the same
 * origin across restarts, so the choice survives one. A v1 save (console / daylight / apollo /
 * jarvis, from the old frame, which shared Polaris²'s switch) maps once onto the new names.
 *
 * Every element carrying data-ls-view (the header's <select>, the palette's commands) reads and
 * writes the view through window.LSView. Strict CSP: no inline script anywhere — this file is it.
 */
"use strict";

(function () {
  var KEY = "lodestar-view";
  var VIEWS = ["dark", "bright", "contrast", "console"];
  var LABELS = { dark: "Dark", bright: "Bright", contrast: "High contrast", console: "Console" };
  //: the v1 frame's four (Polaris²'s) views, read once from its key and never written back
  var LEGACY = { console: "dark", daylight: "bright", apollo: "console", jarvis: "console" };

  function stored(key) {
    try { return localStorage.getItem(key); } catch (e) { return null; }
  }
  function persist(value) {
    try { localStorage.setItem(KEY, value); } catch (e) { /* the in-page switch still works */ }
  }

  // scripting is on: the studio's script-only controls show, its no-script fallbacks hide
  document.documentElement.classList.remove("no-js");
  document.documentElement.classList.add("js");

  var saved = stored(KEY);
  var view = VIEWS.indexOf(saved) >= 0 ? saved : (LEGACY[stored("sf-theme")] || "dark");
  document.documentElement.setAttribute("data-theme", view);

  function reflect() {
    var sels = document.querySelectorAll("select[data-ls-view]");
    for (var i = 0; i < sels.length; i++) sels[i].value = view;
  }
  function apply(next) {
    view = VIEWS.indexOf(next) >= 0 ? next : "dark";
    document.documentElement.setAttribute("data-theme", view);
    persist(view);
    reflect();
  }

  window.LSView = {
    views: VIEWS.slice(),
    label: function (v) { return LABELS[v] || v; },
    get: function () { return view; },
    set: apply,
  };

  function wire() {
    reflect();
    document.addEventListener("change", function (ev) {
      var t = ev.target;
      if (t && t.matches && t.matches("select[data-ls-view]")) apply(t.value);
    });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", wire);
  else wire();
})();
