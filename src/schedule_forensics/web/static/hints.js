/* Schedule Forensics — guidance layer: dismissable per-page guide tips + one-time nudges.
 *
 * The tips themselves are server-rendered (.guide-tip blocks — so they ride the normal i18n
 * pass); this script only (1) hides tips the operator has dismissed (persisted per tip id in
 * localStorage), (2) pulses key controls the first time a page is seen (a soft glow on the
 * dropzone / target UID / theme control), and (3) wires the dismiss buttons. Fully local.
 */
"use strict";

(function () {
  var KEY = "sf-hints-dismissed";

  function dismissed() {
    try { return JSON.parse(localStorage.getItem(KEY) || "{}"); } catch (e) { return {}; }
  }
  function save(map) {
    try { localStorage.setItem(KEY, JSON.stringify(map)); } catch (e) { /* unavailable */ }
  }

  document.addEventListener("DOMContentLoaded", function () {
    // highlight the CURRENT page's link in the header ribbon (operator 2026-07-08). Pick ONE
    // winner: an exact path match if there is one, else the SINGLE longest matching prefix — so
    // "/briefing" no longer also lights up "/brief" (the operator's Diagnostic-Brief-on-Executive
    // bug). A path segment boundary is required so "/brief" can't match "/briefing" as a prefix.
    var here = window.location.pathname;
    var links = Array.prototype.slice.call(document.querySelectorAll("header nav a[href]"));
    var winner = null;
    var winnerLen = -1;
    links.forEach(function (a) {
      var href = a.getAttribute("href");
      if (!href || href.charAt(0) !== "/") return;
      var match =
        href === here ||
        (href !== "/" && (here === href || here.indexOf(href + "/") === 0));
      if (match && href.length > winnerLen) { winner = a; winnerLen = href.length; }
    });
    if (winner) winner.classList.add("nav-active");

    var seen = dismissed();
    document.querySelectorAll(".guide-tip[data-tip-id]").forEach(function (tip) {
      var id = tip.getAttribute("data-tip-id");
      if (seen[id]) { tip.remove(); return; }
      var btn = tip.querySelector(".guide-dismiss");
      if (btn) {
        btn.addEventListener("click", function () {
          seen[id] = 1;
          save(seen);
          tip.remove();
        });
      }
    });

    // one-time nudges: softly pulse the controls a first-time user needs to discover
    var NUDGE_KEY = "sf-nudged";
    var nudgedAlready = false;
    try { nudgedAlready = localStorage.getItem(NUDGE_KEY) === "1"; } catch (e) { /* n/a */ }
    if (!nudgedAlready) {
      ["#drop", ".dropzone", "#themeToggle", ".targetform"].some(function (sel) {
        var el = document.querySelector(sel);
        if (el) { el.classList.add("sf-nudge"); return true; }
        return false;
      });
      try { localStorage.setItem(NUDGE_KEY, "1"); } catch (e) { /* n/a */ }
    }
  });
})();
