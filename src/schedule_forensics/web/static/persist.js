/* Schedule Forensics — per-page selection memory + universal Reset view (ADR-0186).
 *
 * Operator 2026-07-10: "When a user goes to any one of the pages and inputs information such
 * as Target UID or whatever I want those selections to remain in the tool's memory so that if
 * they switch to another page and then come back the information they input is still there as
 * well as the views" — plus a Reset button on every page that clears the page's selections and
 * returns to the default view.
 *
 * Two layers, both keyed by the page path (localStorage, this machine only — air-gap safe):
 *
 *   1. Query-string memory (sf-qs:<path>): server-applied selections travel in the query
 *      string (?target=…, ?file=…, ?group_field=…). Leaving a page with a query string saves
 *      it; returning to the page through a BARE nav link restores it via location.replace, so
 *      the server re-renders the remembered view. /groups is excluded — the group filter is
 *      session-wide server state already, and replaying an old ?apply/?clear would fight it.
 *
 *   2. Control memory (sf-ui:<path>): every value-bearing control (text/number/checkbox/
 *      radio/select/range/textarea) is saved on change and restored on the next visit, then a
 *      change/input event is dispatched so the page's own listeners repaint the view. Page
 *      scripts that only read a control at boot can listen for the "sf-restored" window event.
 *      Excluded: file/password/hidden inputs, the nav Target-UID + language forms (server-side
 *      session state already), and anything marked data-sf-nopersist.
 *
 *   Reset view: clears BOTH layers for this page plus the page's own persisted column-picker
 *   keys, then loads the bare path — the default view. Global preferences (theme, UI size,
 *   Timescale config) are NOT page state and keep their own controls' resets.
 */
"use strict";

(function () {
  var PATH = location.pathname;
  var QS_KEY = "sf-qs:" + PATH;
  var UI_KEY = "sf-ui:" + PATH;
  // pages whose query string must NOT be replayed: /groups mutates the session-wide filter
  var SKIP_QS = { "/groups": true };
  // one-shot params that must never be replayed on return
  var VOLATILE_PARAMS = { clear: true, apply: true };
  // per-page persisted column-picker keys (cleared by Reset view alongside the two layers)
  var PAGE_KEYS = {
    "/resources": ["sf-res-drill-cols"],
    "/trend": ["sf-findings-drill-cols"],
    "/integrity": ["sf-findings-drill-cols"],
    "/risks": ["sf-whatif-cols", "sf-whatif-added-cols"],
    "/ribbon": ["sf-ribbon-drill-cols"],
    "/driving-path": ["sf-driving-tiers-cols"],
  };

  function store() {
    try { return window.localStorage; } catch (e) { return null; }
  }
  var ls = store();
  if (!ls) return; // storage blocked — degrade to the pre-ADR-0186 behavior

  // ---- layer 1: query-string memory --------------------------------------------------
  function cleanedSearch() {
    var raw = location.search.replace(/^\?/, "");
    if (!raw) return "";
    var kept = raw.split("&").filter(function (kv) {
      var name = decodeURIComponent(kv.split("=")[0] || "");
      return !VOLATILE_PARAMS[name];
    });
    return kept.length ? "?" + kept.join("&") : "";
  }
  if (!SKIP_QS[PATH]) {
    if (location.search) {
      var clean = cleanedSearch();
      try {
        if (clean) ls.setItem(QS_KEY, clean);
        else ls.removeItem(QS_KEY); // the page was opened with ONLY volatile params
      } catch (e) { /* quota — fail open */ }
    } else {
      var saved = null;
      try { saved = ls.getItem(QS_KEY); } catch (e) { saved = null; }
      if (saved) location.replace(PATH + saved + location.hash);
    }
  }

  // ---- layer 2: control memory --------------------------------------------------------
  var SKIP_TYPES = { file: true, password: true, hidden: true, button: true, submit: true, image: true, reset: true };

  function keyOf(ctl) {
    if (ctl.id) return "#" + ctl.id;
    if (ctl.type === "radio" && ctl.name) return "radio:" + ctl.name;
    if (ctl.name) {
      // name-keyed controls disambiguated by document order among same-named controls
      var same = document.querySelectorAll('[name="' + ctl.name + '"]');
      var idx = Array.prototype.indexOf.call(same, ctl);
      return "name:" + ctl.name + ":" + idx;
    }
    return null;
  }

  function persistable(ctl) {
    if (!ctl || !ctl.tagName) return false;
    var tag = ctl.tagName.toLowerCase();
    if (tag !== "input" && tag !== "select" && tag !== "textarea") return false;
    if (tag === "input" && SKIP_TYPES[ctl.type]) return false;
    if (ctl.closest("[data-sf-nopersist]") || ctl.hasAttribute("data-sf-nopersist")) return false;
    // the nav Target-UID + language forms are SERVER session state — replaying a stale client
    // copy over them would fight the session (and language auto-submits on change)
    var form = ctl.form;
    if (form) {
      var action = form.getAttribute("action") || "";
      if (action === "/target" || action === "/language" || action === "/session/wipe") return false;
    }
    return true;
  }

  function readState() {
    try { return JSON.parse(ls.getItem(UI_KEY) || "{}") || {}; } catch (e) { return {}; }
  }
  var state = readState();
  var saveTimer = null;
  function writeState() {
    clearTimeout(saveTimer);
    saveTimer = setTimeout(function () {
      try { ls.setItem(UI_KEY, JSON.stringify(state)); } catch (e) { /* quota — fail open */ }
    }, 120);
  }

  function record(ctl) {
    if (!persistable(ctl)) return;
    var key = keyOf(ctl);
    if (!key) return;
    if (ctl.type === "checkbox") state[key] = { c: !!ctl.checked };
    else if (ctl.type === "radio") { if (ctl.checked) state[key] = { v: ctl.value }; }
    else state[key] = { v: ctl.value };
    writeState();
  }

  function fire(ctl, type) {
    try { ctl.dispatchEvent(new Event(type, { bubbles: true })); } catch (e) { /* old engines */ }
  }

  function restore() {
    var restored = [];
    Object.keys(state).forEach(function (key) {
      var entry = state[key];
      var ctl = null;
      if (key.charAt(0) === "#") ctl = document.getElementById(key.slice(1));
      else if (key.indexOf("radio:") === 0) {
        var radios = document.querySelectorAll('input[type=radio][name="' + key.slice(6) + '"]');
        Array.prototype.forEach.call(radios, function (rb) {
          if (rb.value === entry.v && persistable(rb) && !rb.checked) {
            rb.checked = true;
            restored.push(rb);
          }
        });
        return;
      } else if (key.indexOf("name:") === 0) {
        var parts = key.split(":");
        var same = document.querySelectorAll('[name="' + parts[1] + '"]');
        ctl = same[Number(parts[2])] || null;
      }
      if (!ctl || !persistable(ctl)) return;
      if (ctl.type === "checkbox") {
        if (ctl.checked !== !!entry.c) { ctl.checked = !!entry.c; restored.push(ctl); }
      } else if (entry.v !== undefined && String(ctl.value) !== String(entry.v)) {
        // a <select> whose remembered option no longer exists must keep its default
        if (ctl.tagName.toLowerCase() === "select") {
          var has = Array.prototype.some.call(ctl.options, function (o) { return o.value === entry.v; });
          if (!has) return;
        }
        ctl.value = entry.v;
        restored.push(ctl);
      }
    });
    // let the page's own listeners repaint the remembered view (change for discrete controls,
    // input for continuous ones — matching the listeners the pages attach)
    restored.forEach(function (ctl) {
      var continuous = ctl.type === "range" || ctl.tagName.toLowerCase() === "textarea" ||
        ctl.type === "text" || ctl.type === "search" || ctl.type === "number";
      if (continuous) fire(ctl, "input");
      fire(ctl, "change");
    });
    try { window.dispatchEvent(new Event("sf-restored")); } catch (e) { /* old engines */ }
  }

  // ---- Reset view ---------------------------------------------------------------------
  function resetPage() {
    try {
      ls.removeItem(QS_KEY);
      ls.removeItem(UI_KEY);
      (PAGE_KEYS[PATH] || []).forEach(function (k) { ls.removeItem(k); });
    } catch (e) { /* storage gone — the bare reload still resets the server-side view */ }
    location.assign(PATH); // the bare path IS the default view
  }

  function injectResetButton() {
    if (document.getElementById("sfResetView")) return;
    var btn = document.createElement("button");
    btn.id = "sfResetView";
    btn.type = "button";
    btn.className = "sf-reset-view";
    btn.title = "Clear every selection you made on this page (inputs, filters, toggles, remembered view) and return to the default view";
    var glyph = document.createElement("span");
    glyph.setAttribute("aria-hidden", "true");
    glyph.setAttribute("data-no-i18n", "");
    glyph.textContent = "⟲ ";
    var label = document.createElement("span");
    label.textContent = "Reset view"; // its own text node so the i18n layer can translate it
    btn.appendChild(glyph);
    btn.appendChild(label);
    btn.addEventListener("click", resetPage);
    // fixed-position on <body> (operator 2026-07-10: the float version was easy to miss on
    // busy pages like /path — the button must be unmissable on EVERY page and every Gantt)
    document.body.appendChild(btn);
  }

  function boot() {
    injectResetButton();
    restore();
    // one delegated recorder per event kind — inputs save as you type, discrete controls on change
    document.addEventListener("change", function (ev) { record(ev.target); }, true);
    document.addEventListener("input", function (ev) { record(ev.target); }, true);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();
