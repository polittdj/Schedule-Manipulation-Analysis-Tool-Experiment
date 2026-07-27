/* Schedule Forensics — panel-contract toolbar behavior (Mission Ops slice 1).
 *
 * One delegated click listener drives the three-glyph strip on any .panel:
 *   ⛶ [data-sf-big]   — toggle .is-big on the panel (full-bleed row in a grid) and flip the label
 *   ▦ [data-sf-data]  — toggle the panel's .sf-drawer data table and flip the label
 *   ⤓ [data-sf-excel] — follow the panel's data-export URL (an existing /export endpoint)
 *
 * Delegated addEventListener only — zero inline handlers (strict script-src CSP, ADR-0268).
 * Dependency-free and vendored (no CDN — air-gap posture, Law 1).
 */
"use strict";

(function () {
  var SEL = "[data-sf-big],[data-sf-data],[data-sf-excel]";

  document.addEventListener("click", function (ev) {
    var target = ev.target;
    if (!(target instanceof Element)) return;
    var btn = target.closest(SEL);
    if (!btn) return;
    var panel = btn.closest(".panel");
    if (!panel) return;
    ev.preventDefault();

    if (btn.hasAttribute("data-sf-big")) {
      var big = panel.classList.toggle("is-big");
      btn.textContent = big ? "⛶ SHRINK" : "⛶ ENLARGE";
      btn.setAttribute("aria-pressed", big ? "true" : "false");
      return;
    }
    if (btn.hasAttribute("data-sf-data")) {
      var drawer = panel.querySelector(".sf-drawer");
      if (!drawer) return;
      var show = drawer.hasAttribute("hidden");
      if (show) drawer.removeAttribute("hidden");
      else drawer.setAttribute("hidden", "");
      btn.textContent = show ? "▦ HIDE DATA" : "▦ DATA";
      btn.setAttribute("aria-pressed", show ? "true" : "false");
      return;
    }
    // ⤓ EXCEL: the export URL lives on the panel (or the button itself as an override)
    var url = btn.getAttribute("data-export") || panel.getAttribute("data-export");
    if (url) window.location.href = url;
  });
})();
