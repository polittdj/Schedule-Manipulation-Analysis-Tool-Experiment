/* Schedule Forensics — story-progress enhancement (ADR-0196).
 *
 * The server renders the STORY-SO-FAR dashes with the current chapter marked. This adds the
 * cross-page "visited" state: it remembers which chapters you have opened (a global localStorage
 * list, unlike persist.js which is strictly per-page) and tints their dashes, so the progress
 * strip shows how far through the story you have travelled. Fully local, air-gap safe.
 */
"use strict";

(function () {
  var KEY = "sf-story-visited";
  function load() {
    try { return JSON.parse(localStorage.getItem(KEY) || "[]"); } catch (e) { return []; }
  }
  function save(v) {
    try { localStorage.setItem(KEY, JSON.stringify(v)); } catch (e) { /* in-page only */ }
  }
  document.addEventListener("DOMContentLoaded", function () {
    var dashes = [].slice.call(document.querySelectorAll(".story-dash"));
    if (!dashes.length) return;
    var visited = load();
    var curRoute = null;
    dashes.forEach(function (d) {
      if (d.classList.contains("cur")) curRoute = d.getAttribute("data-route");
    });
    if (curRoute && visited.indexOf(curRoute) < 0) { visited.push(curRoute); save(visited); }
    dashes.forEach(function (d) {
      var r = d.getAttribute("data-route");
      if (r && visited.indexOf(r) >= 0 && !d.classList.contains("cur")) d.classList.add("visited");
    });
  });
})();
