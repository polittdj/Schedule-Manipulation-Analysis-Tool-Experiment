/* Schedule Forensics — driving-path corridor animation (ADR-0096).
 *
 * Steps/plays through the loaded versions, drawing the driving corridor between two UIDs as a
 * scalable date-axis Gantt on an axis held FIXED across every version, so the corridor visibly
 * shifts as the schedule slips. Data is embedded in #dpData (computed server-side); activities
 * that ENTERED the corridor since the prior version are outlined. Dependency-free; nothing
 * leaves the machine.
 */
"use strict";

(function () {
  var mount = document.getElementById("dpChart");
  var dataEl = document.getElementById("dpData");
  if (!mount || !dataEl) return;

  var DAY_MS = 86400000;
  var payload = JSON.parse(dataEl.textContent);
  var versions = (payload && payload.versions) || [];
  if (!versions.length) return;

  var idx = versions.length - 1; // start on the newest version
  var px = 6; // pixels per calendar day
  var forcedPx = null; // set by "View entire project"; cleared when a zoom button is pressed
  var timer = null;
  var lastFrozenWidth = 0; // MEASURED frozen data-column width (SFGantt.freezeColumns return)
  var colFilters = {}; // MS-Project per-column filter: "uid"/"name" -> Set|null (null = all)

  function $(id) { return document.getElementById(id); }
  function el(tag, attrs, kids) {
    var node = document.createElement(tag);
    for (var k in attrs || {}) {
      if (k === "text") node.textContent = attrs[k];
      else node.setAttribute(k, attrs[k]);
    }
    (kids || []).forEach(function (c) { node.appendChild(c); });
    return node;
  }

  // one date range across ALL versions, so the axis is shared and the bars move between frames
  var t0 = null, t1 = null;
  function span(ms) {
    if (ms === null || isNaN(ms)) return;
    t0 = Math.min(t0 === null ? Infinity : t0, ms);
    t1 = Math.max(t1 === null ? -Infinity : t1, ms);
  }
  versions.forEach(function (v) {
    (v.activities || []).forEach(function (a) {
      if (a.start) span(Date.parse(a.start));
      if (a.finish) span(Date.parse(a.finish));
    });
    if (v.data_date) span(Date.parse(v.data_date));
  });
  if (t0 === null || t1 === null) return;
  t0 -= 2 * DAY_MS; t1 += 2 * DAY_MS;
  // unlimited right scroll (ADR-0187): the pane's right edge extends the shared axis
  SFGantt.attachEdgeExtend(mount, function () { t1 += 60 * DAY_MS; render(); });
  // pixels per calendar day: the "View entire project" fit overrides the zoom buttons until
  // nudged; the Timescale dialog's Size % scales the button zoom (the fit is already exact)
  function pxPerDay() {
    var size = window.SFTimescale ? window.SFTimescale.sizeFactor() : 1;
    if (!(size > 0)) size = 1;
    if (forcedPx && forcedPx > 0) return forcedPx * size; // Size scales even the fitted view
    return px * size;
  }
  var x = function (ms) { return Math.round(((ms - t0) / DAY_MS) * pxPerDay()); };
  // Auto-scale so the whole (shared, fixed) corridor span fits the visible width — no scroll.
  // The fill space subtracts the REAL measured frozen-column width recorded on each paint (like
  // path.js) rather than a hard-coded estimate, so the corridor uses the entire page.
  function fitToProject() {
    var days = Math.max(1, (t1 - t0) / DAY_MS);
    var avail = Math.max(240, (mount ? mount.clientWidth : 1000) - (lastFrozenWidth || 320) - 18);
    forcedPx = Math.max(0.02, avail / days);
    render();
  }

  // --- MS-Project per-column checklist filters (UID / Name), persistent across versions -----
  function distinctValues(getter) {
    var seen = {};
    versions.forEach(function (v) {
      (v.activities || []).forEach(function (a) { seen[getter(a)] = true; });
    });
    return Object.keys(seen).sort(function (a, b) {
      var na = parseFloat(a), nb = parseFloat(b);
      var bothNum = !isNaN(na) && !isNaN(nb) && /^-?\d/.test(a) && /^-?\d/.test(b);
      return bothNum ? na - nb : a < b ? -1 : a > b ? 1 : 0;
    });
  }
  function rowMatchesFilters(a) {
    if (colFilters.uid && !colFilters.uid.has(String(a.uid))) return false;
    if (colFilters.name && !colFilters.name.has(String(a.name))) return false;
    return true;
  }

  function render() {
    var v = versions[idx];
    $("dpLabel").textContent = "Version " + (idx + 1) + "/" + versions.length + " — " + v.label +
      (v.data_date ? " (data date " + v.data_date + ")" : "") + " — " + v.status +
      (v.change_note ? " · " + v.change_note : "");
    mount.textContent = "";
    var acts = v.activities || [];
    if (!acts.length) {
      mount.appendChild(el("p", { class: "muted", text: "No driving corridor in this version." }));
      return;
    }
    var width = Math.max(120, Math.round((t1 - t0) / DAY_MS) * pxPerDay());
    // MS-Project timeline: stacked Year/Quarter/Month header + month/quarter/year gridlines,
    // shared with every other Gantt on the site (static/gantt.js).
    var axis = { t0: t0, t1: t1, width: width, x: x };
    var gridLns = SFGantt.gridLines(axis);

    var table = el("table", { class: "gantt-grid path-grid" });
    var thead = el("thead");  // a <thead> so the shared sticky-header CSS locks it on scroll
    var head = el("tr");
    head.appendChild(el("th", { text: "UID" }));
    head.appendChild(el("th", { text: "Name" }));
    var thTime = el("th", { class: "g-head path-timeline-head" });
    thTime.appendChild(SFGantt.buildTierScale(axis, "path-scale", v.data_date));
    head.appendChild(thTime);
    thead.appendChild(head);
    // MS-Project per-column checklist filters (UID / Name) — the selection survives stepping
    // between versions; a filter change repaints only the body rows
    var tbody = el("tbody");
    var filterRow = el("tr", { class: "filter-row" });
    [
      { key: "uid", label: "UID", getter: function (a) { return String(a.uid); } },
      { key: "name", label: "Name", getter: function (a) { return String(a.name); } },
    ].forEach(function (f) {
      var td = el("td");
      if (window.SFChecklist) {
        td.appendChild(SFChecklist.filter({
          values: distinctValues(f.getter),
          selected: colFilters[f.key] || null,
          label: "Filter",
          title: "Filter " + f.label,
          onChange: function (sel) { colFilters[f.key] = sel; paintBody(tbody, v, acts, gridLns, width); },
        }));
      }
      filterRow.appendChild(td);
    });
    filterRow.appendChild(el("td", { class: "muted" }));
    thead.appendChild(filterRow);
    table.appendChild(thead);
    table.appendChild(tbody);
    mount.appendChild(table);
    if (window.SFColResize) SFColResize.attach(table, "driving"); // MS-Project drag-to-resize columns
    // paintBody locks the UID/Name columns (SFGantt.freezeColumns) so they stay visible as the
    // wide corridor timeline scrolls, and records their measured width for fitToProject
    paintBody(tbody, v, acts, gridLns, width);
  }

  // repaint only the corridor body rows for the current version + column filters
  function paintBody(tbody, v, acts, gridLns, width) {
    var list = acts.filter(rowMatchesFilters);
    tbody.innerHTML = "";
    var barDates = $("dpBarDates") && $("dpBarDates").checked;
    var LABEL_W = 64; // "MM/DD/YYYY" width estimate at the 9px label font (matches app.js)
    function barLabel(track, anchor, side, iso) {
      var lx = side === "s" ? anchor - LABEL_W : anchor;
      lx = Math.max(0, Math.min(width - LABEL_W, lx));
      track.appendChild(el("div", {
        class: "g-barlabel g-barlabel-" + side,
        style: "left:" + lx + "px;width:" + LABEL_W + "px",
        text: SFGantt.fmtMDY(iso),
      }));
    }
    list.forEach(function (a) {
      var tr = el("tr");
      tr.setAttribute("data-uid", a.uid); // Find-a-UID jump + Task Information join
      // MS-Project Task Information on row click (shared dialog — ADR-0186), sourced from
      // THIS VERSION's file so the figures match the frame on screen
      tr.addEventListener("click", function () {
        if (window.SFTaskInfo) SFTaskInfo.openFrom(v.label, a.uid);
      });
      tr.appendChild(el("td", { text: String(a.uid) }));
      tr.appendChild(el("td", { class: "pv-name", text: a.name }));
      var cell = el("td", { class: "path-timeline" });
      var track = el("div", { class: "path-track", style: "width:" + width + "px" });
      SFGantt.paintGrid(track, gridLns);
      if (v.data_date) {
        track.appendChild(el("div", { class: "pv-now", style: "left:" + x(Date.parse(v.data_date)) + "px" }));
      }
      var entered = a.entered ? " dp-entered" : "";
      if (a.start && a.finish) {
        if (a.is_milestone) {
          track.appendChild(el("div", {
            class: "g-ms tier-DRIVING" + entered, style: "left:" + x(Date.parse(a.finish)) + "px",
            title: a.name + " (milestone) " + (SFGantt.fmtMDY(a.finish) || a.finish) + (a.entered ? " — entered" : ""),
          }));
          if (barDates) barLabel(track, x(Date.parse(a.finish)) + 7, "f", a.finish);
        } else {
          var left = x(Date.parse(a.start));
          var w = Math.max(2, x(Date.parse(a.finish)) - left);
          track.appendChild(el("div", {
            class: "gantt-bar tier-DRIVING" + entered,
            style: "left:" + left + "px;width:" + w + "px",
            title: a.name + " — " + (SFGantt.fmtMDY(a.start) || a.start) + " → " + (SFGantt.fmtMDY(a.finish) || a.finish) + (a.entered ? " (entered)" : ""),
          }));
          if (barDates) {
            barLabel(track, left - 3, "s", a.start);
            barLabel(track, left + w + 3, "f", a.finish);
          }
        }
      }
      cell.appendChild(track);
      SFGantt.paintNonwork(cell, { t0: t0, t1: t1, width: width, x: x }); // continuous shading
      tr.appendChild(cell);
      tbody.appendChild(tr);
    });
    if (!list.length) {
      var empty = el("tr");
      empty.appendChild(el("td", { class: "muted", text: "No activities match the filters." }));
      tbody.appendChild(empty);
    }
    var tbl = tbody.parentNode;
    if (tbl && tbl.isConnected && window.SFGantt && SFGantt.freezeColumns) {
      lastFrozenWidth = SFGantt.freezeColumns(tbl) || lastFrozenWidth;
    }
  }

  function stopPlay() {
    if (timer) { clearInterval(timer); timer = null; $("dpPlay").innerHTML = "&#9654; Auto-play"; }
  }
  function step(delta) { idx = (idx + delta + versions.length) % versions.length; render(); }

  $("dpPrev").addEventListener("click", function () { stopPlay(); step(-1); });
  $("dpNext").addEventListener("click", function () { stopPlay(); step(1); });
  $("dpPlay").addEventListener("click", function () {
    if (timer) { stopPlay(); return; }
    idx = 0; render(); $("dpPlay").innerHTML = "&#9208; Pause";
    timer = setInterval(function () {
      if (idx >= versions.length - 1) { stopPlay(); return; }
      step(1);
    }, 1100);
  });
  $("dpZoomIn").addEventListener("click", function () { forcedPx = null; px = Math.min(40, px + 2); render(); });
  $("dpZoomOut").addEventListener("click", function () { forcedPx = null; px = Math.max(1, px - 2); render(); });
  var dpFit = $("dpFit");
  if (dpFit) dpFit.addEventListener("click", fitToProject);
  // MS-Project "dates on bars" (parity with the Activities Gantt — ADR-0186)
  var dpBarDates = $("dpBarDates");
  if (dpBarDates) dpBarDates.addEventListener("change", render);
  // MS-Project Find: jump the corridor to a UniqueID, scroll it into view and flash it
  var dpFind = $("dpFind");
  if (dpFind) {
    var goFind = function () { SFGantt.findTask(mount, dpFind.value, $("dpFindStatus")); };
    dpFind.addEventListener("change", goFind);
    dpFind.addEventListener("keydown", function (e) { if (e.key === "Enter") { e.preventDefault(); goFind(); } });
  }
  // the Timescale dialog's OK repaints the corridor with the new tiers/size/shading
  window.addEventListener("sf-timescale", render);

  render();
})();
