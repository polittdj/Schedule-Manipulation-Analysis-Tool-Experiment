/* Schedule Forensics — SSI-style path analysis workspace.
 *
 * Data grid on the left, a SCALABLE timeline on the right (zoom = pixels per day,
 * horizontal scroll) with month ticks and the gold data-date line. The driving /
 * secondary / tertiary tiers come from /api/driving with the user's own day-bands and
 * target UID; columns are add/removable, rows filterable (tier, substring, hide 100%
 * complete). The Ask-the-AI panel is the page-shell one (ask.js). Dependency-free;
 * nothing leaves the machine.
 */
"use strict";

(function () {
  var view = document.getElementById("pathView");
  if (!view) return;

  var DAY_MS = 86400000;
  var FIELDS = [
    { key: "unique_id", label: "UID", on: true },
    { key: "name", label: "Name", on: true },
    { key: "wbs", label: "WBS", on: false },
    { key: "tier", label: "Tier", on: true },
    { key: "driving_slack_days", label: "Slack (d)", on: true },
    { key: "start", label: "Start", on: true },
    { key: "finish", label: "Finish", on: true },
    { key: "baseline_finish", label: "Baseline finish", on: false },
    { key: "duration_days", label: "Dur (d)", on: false },
    { key: "total_float_days", label: "TF (d)", on: false },
    { key: "percent_complete", label: "%", on: true },
    { key: "date_driven", label: "Date-driven", on: false },
    { key: "resource_names", label: "Resources", on: false },
    { key: "drives", label: "Drives →", on: false },
  ];
  var data = null; // last /api/driving payload
  var pathTierSel = null; // checklist selection of tiers to show (null = all)
  var colFilters = {}; // MS-Project per-column filter: field key -> Set|null (null = unfiltered)
  var forcedPx = null; // set by "View entire project"; cleared by the zoom slider
  var lastAxis = null, lastGrid = null, lastOn = null; // header built once; body repaints on filter

  function el(tag, attrs, kids) {
    var node = document.createElement(tag);
    for (var k in attrs || {}) {
      if (k === "text") node.textContent = attrs[k];
      else node.setAttribute(k, attrs[k]);
    }
    (kids || []).forEach(function (c) { node.appendChild(c); });
    return node;
  }
  function $(id) { return document.getElementById(id); }

  function fmt(v) {
    if (v === true) return "yes";
    if (v === false) return "—";
    return v === null || v === undefined || v === "" ? "—" : String(v);
  }
  // the raw (filterable) value of a column for a row; the "Drives →" column isn't value-filterable
  function rawValue(r, f) {
    if (f.key === "drives") return null;
    return f.custom ? r.custom && r.custom[f.label] : r[f.key];
  }
  // distinct, numeric/ISO-aware sorted formatted values of a column — the checklist contents
  function distinctValues(f) {
    var seen = {};
    (data ? data.rows : []).forEach(function (r) { seen[fmt(rawValue(r, f))] = true; });
    var iso = /^\d{4}-\d\d-\d\d/;
    return Object.keys(seen).sort(function (a, b) {
      if (iso.test(a) && iso.test(b)) return a < b ? -1 : a > b ? 1 : 0;
      var na = parseFloat(a), nb = parseFloat(b);
      var bothNum = !isNaN(na) && !isNaN(nb) && /^-?\d/.test(a) && /^-?\d/.test(b);
      return bothNum ? na - nb : a < b ? -1 : a > b ? 1 : 0;
    });
  }
  function rowMatchesColumns(r) {
    return (lastOn || []).every(function (f) {
      var sel = colFilters[f.key];
      if (!sel || f.key === "drives") return true; // unfiltered
      return sel.has(fmt(rawValue(r, f))); // an empty Set hides every row
    });
  }

  // pixels per calendar day: the "View entire project" fit overrides the slider until it's nudged
  function pxPerDay() {
    if (forcedPx && forcedPx > 0) return forcedPx;
    var v = Number($("pathZoom").value);
    return v > 0 ? v : 8;
  }
  function fitToProject() {
    if (!data) return;
    var t0 = null, t1 = null;
    data.rows.forEach(function (r) {
      if (r.start) t0 = Math.min(t0 === null ? Infinity : t0, Date.parse(r.start));
      if (r.finish) t1 = Math.max(t1 === null ? -Infinity : t1, Date.parse(r.finish));
    });
    if (data.data_date) t1 = Math.max(t1 === null ? -Infinity : t1, Date.parse(data.data_date));
    if (t0 === null || t1 === null) return;
    var days = Math.max(1, (t1 - t0) / DAY_MS) + 4;
    var avail = Math.max(240, (view ? view.clientWidth : 960) - 380);
    forcedPx = Math.max(0.02, avail / days);
    render();
  }

  // --- columns dropdown (MS-Project-style "add/remove columns") ---------------------
  function renderToggles() {
    var box = $("pathFields");
    box.textContent = "";
    if (!window.SFChecklist) return;
    box.appendChild(
      window.SFChecklist.filter({
        values: FIELDS.map(function (f) { return f.label; }),
        selected: new Set(
          FIELDS.filter(function (f) { return f.on; }).map(function (f) { return f.label; })
        ),
        label: "Columns",
        title: "Add or remove columns",
        onChange: function (sel) {
          FIELDS.forEach(function (f) { f.on = sel ? sel.has(f.label) : true; });
          updateExportLinks(); // a toggled-on custom column is added to the export too
          render();
        },
      })
    );
  }

  // Keep the export links in sync with the chosen custom columns (ADR-0095): the path export
  // mirrors whichever custom fields are toggled on in the grid, via the &cols= query param.
  function updateExportLinks() {
    if (!data) return;
    var onCustom = FIELDS.filter(function (f) { return f.custom && f.on; })
      .map(function (f) { return f.label; });
    var q = "/" + encodeURIComponent($("pathSchedule").value) +
      "?target=" + encodeURIComponent($("pathTarget").value) +
      "&secondary=" + encodeURIComponent($("pathSec").value || "10") +
      "&tertiary=" + encodeURIComponent($("pathTer").value || "20") +
      (onCustom.length ? "&cols=" + encodeURIComponent(onCustom.join(",")) : "");
    $("pathXlsx").href = "/export/xlsx/path" + q;
    $("pathDocx").href = "/export/docx/path" + q;
    $("pathExport").style.display = "";
  }

  // The schedule's mapped custom fields (ADR-0088) become optional columns, off by default —
  // discovered from the payload so any file's fields appear without hard-coding. State persists
  // in FIELDS across reloads, so a chosen custom column stays on when the target/version changes.
  function syncCustomColumns() {
    var labels = (data && data.custom_field_labels) || [];
    var have = {};
    FIELDS.forEach(function (f) { if (f.custom) have[f.label] = true; });
    labels.forEach(function (label) {
      if (!have[label]) FIELDS.push({ key: "cf:" + label, label: label, on: false, custom: true });
    });
  }

  // --- filtering --------------------------------------------------------------------
  function visibleRows() {
    if (!data) return [];
    var hideDone = $("pathHideDone").checked;
    var q = $("pathFilter").value.trim().toLowerCase();
    return data.rows.filter(function (r) {
      if (hideDone && r.complete) return false;
      if (pathTierSel && !pathTierSel.has(r.tier)) return false; // empty Set hides every row
      if (q && (r.name + " " + r.unique_id).toLowerCase().indexOf(q) < 0) return false;
      if (!rowMatchesColumns(r)) return false; // MS-Project per-column value filters
      return true;
    });
  }

  function paintStatus(rows) {
    $("pathStatus").textContent = data && data.note
      ? data.note
      : rows.length + " of " + (data ? data.rows.length : 0) + " path activities to UID " +
        (data ? data.target_uid : "") + " (" + ((data && data.target_name) || "?") + ")" +
        (data && data.data_date ? " — data date " + data.data_date : "") +
        (data && data.coverage ? " — " + data.coverage : "");
  }

  // --- the two-pane grid + scalable timeline ----------------------------------------
  // render() builds the header (column titles + the MS-Project per-column filter row) and the date
  // axis once; paintRows() repopulates only the body, so toggling a filter checkbox or hide-completed
  // keeps the open filter dropdown in place. The axis spans ALL rows so it is stable as filters change.
  function render() {
    if (window.SFChecklist) SFChecklist.close();
    view.textContent = "";
    if (!data) { $("pathStatus").textContent = ""; return; }
    var on = FIELDS.filter(function (f) { return f.on; });
    lastOn = on;
    var px = pxPerDay();
    var t0 = null, t1 = null;
    data.rows.forEach(function (r) {
      if (r.start) t0 = Math.min(t0 === null ? Infinity : t0, Date.parse(r.start));
      if (r.finish) t1 = Math.max(t1 === null ? -Infinity : t1, Date.parse(r.finish));
    });
    if (data.data_date) t1 = Math.max(t1 === null ? -Infinity : t1, Date.parse(data.data_date));
    if (t0 === null || t1 === null) { paintStatus([]); return; }
    t0 -= 2 * DAY_MS; t1 += 2 * DAY_MS;
    var width = Math.max(120, Math.round((t1 - t0) / DAY_MS) * px);
    var x = function (ms) { return Math.round(((ms - t0) / DAY_MS) * px); };
    var axis = { t0: t0, t1: t1, width: width, x: x };
    lastAxis = axis;
    lastGrid = SFGantt.gridLines(axis);

    var table = el("table", { class: "gantt-grid path-grid" });
    // header rows live in a <thead> so the shared sticky-header CSS locks them on scroll
    var thead = el("thead");
    var head = el("tr");
    on.forEach(function (f) { head.appendChild(el("th", { text: f.label })); });
    var thTime = el("th", { class: "g-head path-timeline-head" });
    thTime.appendChild(SFGantt.buildTierScale(axis, "path-scale", data.data_date));
    head.appendChild(thTime);
    thead.appendChild(head);

    // MS-Project per-column filter dropdowns (each lists that column's distinct values)
    var filterRow = el("tr", { class: "filter-row" });
    on.forEach(function (f) {
      var td = el("td");
      if (window.SFChecklist && f.key !== "drives") {
        td.appendChild(window.SFChecklist.filter({
          values: distinctValues(f),
          selected: colFilters[f.key] || null,
          label: "Filter",
          title: "Filter " + f.label,
          onChange: function (sel) { colFilters[f.key] = sel; paintRows(); },
        }));
      }
      filterRow.appendChild(td);
    });
    filterRow.appendChild(el("td", { class: "muted" }));
    thead.appendChild(filterRow);
    table.appendChild(thead);

    var tbody = el("tbody", { id: "pathBody" });
    table.appendChild(tbody);
    view.appendChild(table);
    if (window.SFColResize) SFColResize.attach(table, "path"); // MS-Project drag-to-resize columns
    paintRows();
  }

  function paintRows() {
    var tbody = $("pathBody");
    if (!tbody || !lastAxis) return;
    var axis = lastAxis, gridLns = lastGrid, on = lastOn, x = axis.x, width = axis.width;
    var rows = visibleRows();
    paintStatus(rows);
    tbody.innerHTML = "";
    rows.forEach(function (r) {
      var tr = el("tr", { class: r.complete ? "done" : "" });
      on.forEach(function (f) {
        if (f.key === "drives") {
          var links = (r.drives || []).map(function (lk) {
            var lag = lk.lag_days
              ? (lk.lag_days > 0 ? " +" + lk.lag_days + "d" : " " + lk.lag_days + "d")
              : "";
            return lk.uid + " (" + lk.type + lag + ")" + (lk.on_path ? "*" : "");
          });
          tr.appendChild(el("td", { class: "pv-drives", text: links.length ? links.join(", ") : "—" }));
          return;
        }
        var v = f.custom ? (r.custom && r.custom[f.label]) : r[f.key];
        if (typeof v === "boolean") v = v ? "yes" : "—";
        var text = v === null || v === undefined ? "—" : String(v);
        // the Name column wraps to its FULL text (no truncation); other columns stay nowrap
        tr.appendChild(el("td", f.key === "name" ? { class: "pv-name", text: text } : { text: text }));
      });
      var cell = el("td", { class: "path-timeline" });
      var track = el("div", { class: "path-track", style: "width:" + width + "px" });
      SFGantt.paintGrid(track, gridLns);
      if (data.data_date) {
        track.appendChild(el("div", { class: "pv-now", style: "left:" + x(Date.parse(data.data_date)) + "px" }));
      }
      if (r.start && r.finish) {
        if (r.is_milestone) {
          track.appendChild(el("div", {
            class: "g-ms tier-" + r.tier, style: "left:" + x(Date.parse(r.finish)) + "px",
            title: r.name + " (milestone) — slack " + r.driving_slack_days + "d",
          }));
        } else {
          var left = x(Date.parse(r.start));
          var w = Math.max(2, x(Date.parse(r.finish)) - left);
          var bar = el("div", {
            class: "gantt-bar tier-" + r.tier + (r.complete ? " done" : ""),
            style: "left:" + left + "px;width:" + w + "px",
            title: r.name + " — " + r.tier + ", slack " + r.driving_slack_days + "d, " +
              r.start + " → " + r.finish + ", " + r.percent_complete + "%",
          });
          if (!r.complete && r.percent_complete > 0 && r.percent_complete < 100) {
            bar.appendChild(el("div", { class: "g-done", style: "width:" + r.percent_complete + "%" }));
          }
          track.appendChild(bar);
        }
      }
      cell.appendChild(track);
      tr.appendChild(cell);
      tbody.appendChild(tr);
    });
    if (!rows.length) {
      tbody.appendChild(
        el("tr", {}, [el("td", { class: "muted", text: "No activities match the filters." })])
      );
    }
  }

  // --- data loading -----------------------------------------------------------------
  function trace() {
    var sched = $("pathSchedule").value;
    var target = $("pathTarget").value;
    if (!target) { $("pathStatus").textContent = "Enter a target UniqueID, then Trace."; return; }
    var url = "/api/driving/" + encodeURIComponent(sched) +
      "?target=" + encodeURIComponent(target) +
      "&secondary=" + encodeURIComponent($("pathSec").value || "10") +
      "&tertiary=" + encodeURIComponent($("pathTer").value || "20");
    $("pathStatus").textContent = "Tracing…";
    fetch(url)
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (res) {
        if (!res.ok) { $("pathStatus").textContent = res.j.error || "Trace failed."; data = null; view.textContent = ""; return; }
        data = res.j;
        syncCustomColumns();
        renderToggles();
        updateExportLinks();
        render();
      })
      .catch(function () { $("pathStatus").textContent = "Trace failed."; });
  }

  renderToggles();
  // the MS-Project-style tier checklist (select-all / clear which of the four tiers show)
  var pathTierMount = $("pathTier");
  if (pathTierMount && window.SFChecklist) {
    pathTierMount.appendChild(window.SFChecklist.filter({
      values: ["DRIVING", "SECONDARY", "TERTIARY", "BEYOND"],
      selected: null,
      label: "Tier",
      title: "Show driving-path tiers",
      onChange: function (s) { pathTierSel = s; paintRows(); },
    }));
  }
  $("pathRun").addEventListener("click", trace);
  $("pathHideDone").addEventListener("change", paintRows);
  $("pathFilter").addEventListener("input", paintRows);
  $("pathZoom").addEventListener("input", function () { forcedPx = null; render(); });
  var pathFit = $("pathFit");
  if (pathFit) pathFit.addEventListener("click", fitToProject);
  if ($("pathTarget").value) trace(); // a session-wide target traces immediately
})();
