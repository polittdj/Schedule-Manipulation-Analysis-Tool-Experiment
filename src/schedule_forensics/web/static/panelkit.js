/* Schedule Forensics — panel-contract toolbar behavior (Mission Ops slice 1).
 *
 * One delegated click listener drives the three-glyph strip on any .panel:
 *   ⛶ [data-sf-big]   — toggle .is-big on the panel and flip the label
 *   ▦ [data-sf-data]  — toggle the panel's .sf-drawer data table and flip the label
 *   ⤓ [data-sf-excel] — follow the panel's data-export URL (an existing /export endpoint)
 *
 * ⛶ has TWO layouts, and this file must not care which one a panel got:
 *   - a MOSAIC TILE (`.mosaic .tile`) grows in place via `grid-column:1/-1` plus the round-10
 *     matched pair `.mosaic .tile.is-big .chart-host{height:74vh}` — it stays in the flow, so any
 *     number of tiles may be open at once and every one of them is reachable.
 *   - a BLOCK-LAYOUT panel (/evm, /scurve, /path, …) has no grid to span, so `.is-big` lifts it
 *     into a fixed near-full-viewport focus overlay (base.css, ADR-0304 amendment). Two of those
 *     open at once land on the same rect and the lower one's own ⛶ SHRINK becomes unclickable —
 *     measured on /evm: with panels 2 and 3 open, `elementFromPoint` over panel 2's button
 *     returned panel 3's `.panel-head`, and only a reload recovered it.
 * Hence the SINGLE-OPEN invariant below applies to overlays ONLY, and it decides which is which by
 * ASKING THE BROWSER for the panel's computed `position` rather than re-deriving base.css's
 * selector in JS — one owner for the rule, no second half-implementation of the vocabulary.
 * Escape closes an open overlay for the same reason; an in-flow tile is not a trap and is left be.
 *
 * Delegated addEventListener only — zero inline handlers (strict script-src CSP, ADR-0268).
 * Dependency-free and vendored (no CDN — air-gap posture, Law 1).
 */
"use strict";

(function () {
  var SEL = "[data-sf-big],[data-sf-data],[data-sf-excel]";

  // An enlarged panel is a focus OVERLAY only when base.css actually took it out of the flow.
  function isOverlay(panel) {
    return window.getComputedStyle(panel).position === "fixed";
  }

  // Put one panel back to its un-enlarged state, label and aria-pressed included.
  function shrink(panel) {
    panel.classList.remove("is-big");
    var btn = panel.querySelector("[data-sf-big]");
    if (!btn) return;
    btn.textContent = "⛶ ENLARGE";
    btn.setAttribute("aria-pressed", "false");
  }

  // Close every open overlay except `keep` (pass null to close them all). Returns how many closed.
  function closeOverlays(keep) {
    var open = document.querySelectorAll(".panel.is-big");
    var closed = 0;
    for (var i = 0; i < open.length; i++) {
      if (open[i] !== keep && isOverlay(open[i])) {
        shrink(open[i]);
        closed++;
      }
    }
    return closed;
  }

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
      // Single-open invariant: an overlay covers the page, so it may not stack on another one.
      if (big && isOverlay(panel)) closeOverlays(panel);
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

  // Escape dismisses the focus overlay (it is the only enlarge state that hides the page under it).
  document.addEventListener("keydown", function (ev) {
    if (ev.key !== "Escape") return;
    if (closeOverlays(null)) ev.preventDefault();
  });
})();
