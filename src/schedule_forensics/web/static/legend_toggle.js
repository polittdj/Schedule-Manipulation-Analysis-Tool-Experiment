/* SFLegend — click a legend entry to show/hide that series on any chart; plus a show-all/none
 * control (ADR-0276). Dependency-free, air-gap / CSP-safe (no innerHTML, no external asset).
 *
 * A chart OPTS IN by following one convention:
 *   - each series' on-screen SVG element(s) carry  data-series="<key>"
 *   - each legend entry carries                     data-series-toggle="<key>"  (role=button, focusable)
 *   - an optional show-all/none control carries     data-series-all
 * The <key> is any stable string (the series label works). The hidden set lives on the SCOPE — the
 * smallest ancestor that holds BOTH the legend and the series (e.g. trend's `.chart` wrap) — so
 * several charts on one page stay independent.
 *
 * Animated steppers rebuild their series SVG every frame, which would drop the hidden state. So the
 * FIRST time a scope hides a series a MutationObserver is attached to that scope; on any subtree
 * childList change (a redraw) it RE-APPLIES the hidden set to the freshly-drawn elements. The
 * observer is lazy (only while something is hidden) and watches childList only, so apply()'s own
 * style writes never retrigger it and there is no loop.
 *
 * This only styles the on-screen SVG (`display:none`), reversibly — it never removes data, and the
 * hidden data-table / Excel export are untouched, so a "hidden" series is a VIEW filter, not a
 * dropped number (Law 2 / honest-N).
 */
"use strict";

(function () {
  var HIDDEN = "__sfHiddenSeries"; // Set<string> stamped on the scope element
  var MO = "__sfLegendMo"; // the lazy MutationObserver stamped on the scope element

  // the smallest ancestor of `node` that also contains series elements (so the legend and its
  // series share one scope); null if none (a legend with no tagged series — a no-op, static chart).
  function scopeFor(node) {
    var n = node;
    while (n && n.querySelector) {
      if (n.querySelector("[data-series]")) return n;
      n = n.parentNode;
    }
    return null;
  }

  function hiddenSet(scope) {
    if (!scope[HIDDEN]) scope[HIDDEN] = {}; // plain object as a Set (ES5-safe, no Set dependency)
    return scope[HIDDEN];
  }

  function apply(scope) {
    var hid = hiddenSet(scope);
    var series = scope.querySelectorAll("[data-series]");
    for (var i = 0; i < series.length; i++) {
      var key = series[i].getAttribute("data-series");
      series[i].style.display = hid[key] ? "none" : "";
    }
    var items = scope.querySelectorAll("[data-series-toggle]");
    for (var j = 0; j < items.length; j++) {
      var k = items[j].getAttribute("data-series-toggle");
      var off = !!hid[k];
      if (items[j].classList) items[j].classList.toggle("legend-off", off);
      items[j].setAttribute("aria-pressed", off ? "false" : "true");
    }
  }

  function anyHidden(scope) {
    var hid = scope[HIDDEN];
    if (!hid) return false;
    for (var k in hid) { if (hid[k]) return true; }
    return false;
  }

  // start watching a scope for redraws once it has a hidden series, so animated frames keep the
  // filter; stop when nothing is hidden any more (keeps the observer count minimal).
  function syncObserver(scope) {
    if (anyHidden(scope)) {
      if (!scope[MO] && typeof MutationObserver === "function") {
        var mo = new MutationObserver(function () { apply(scope); });
        mo.observe(scope, { childList: true, subtree: true });
        scope[MO] = mo;
      }
    } else if (scope[MO]) {
      scope[MO].disconnect();
      scope[MO] = null;
    }
  }

  function toggle(scope, key) {
    var hid = hiddenSet(scope);
    hid[key] = !hid[key];
    apply(scope);
    syncObserver(scope);
  }

  function setAll(scope, hideAll) {
    var hid = hiddenSet(scope);
    var items = scope.querySelectorAll("[data-series-toggle]");
    for (var k in hid) { delete hid[k]; }
    if (hideAll) {
      for (var i = 0; i < items.length; i++) hid[items[i].getAttribute("data-series-toggle")] = true;
    }
    apply(scope);
    syncObserver(scope);
  }

  // one delegated click listener for the whole app
  document.addEventListener("click", function (e) {
    var t = e.target;
    if (!t || !t.closest) return;
    var item = t.closest("[data-series-toggle]");
    if (item) {
      var scope = scopeFor(item);
      if (scope) toggle(scope, item.getAttribute("data-series-toggle"));
      return;
    }
    var all = t.closest("[data-series-all]");
    if (all) {
      var sc = scopeFor(all);
      if (sc) setAll(sc, !anyHidden(sc)); // nothing hidden → hide all (none); else show all
    }
  });

  // keyboard parity: Enter / Space on a focused legend control routes through the click handler
  document.addEventListener("keydown", function (e) {
    if (e.key !== "Enter" && e.key !== " " && e.key !== "Spacebar") return;
    var t = e.target;
    if (!t || !t.closest) return;
    var item = t.closest("[data-series-toggle], [data-series-all]");
    if (!item) return;
    e.preventDefault();
    item.click();
  });

  // public hook so a chart can register a legend/scope built after load, or re-apply on demand
  window.SFLegend = { apply: apply, toggle: toggle, setAll: setAll, scopeFor: scopeFor };
})();
