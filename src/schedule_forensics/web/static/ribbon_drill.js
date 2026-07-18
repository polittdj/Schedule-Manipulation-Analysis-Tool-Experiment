/* Schedule Forensics — Quality-Ribbon metric click-drill (operator 2026-07-08).
 *
 * Click any metric cell (any file x any measure) and the activities behind that figure are
 * listed below the ribbon with UID / name / duration / % complete / start / finish. A
 * Gantt-style Columns dropdown adds any other standard or custom field, and the choice is
 * SET ONCE: it persists in localStorage and applies to every subsequent cell click (and the
 * next visit) instead of being re-picked per selection. Excel export downloads exactly the
 * current selection + columns. Fully local: offender UIDs are embedded server-side
 * (window.SF_RIBBON_DRILL); activity field data comes from the same-origin /api/analysis.
 */
"use strict";

(function () {
  var drill = document.getElementById("ribbonDrill");
  var _drillEl = document.getElementById("sfRibbonDrillData");
  var _boot = {};
  if (_drillEl) { try { _boot = JSON.parse(_drillEl.textContent || "{}"); } catch (e) { _boot = {}; } }
  var DATA = _boot.drill || {};
  var LABELS = _boot.labels || {};
  if (!drill) return;

  var COLS_KEY = "sf-ribbon-drill-cols"; // persisted set-once column choice (labels, on/off)

  // the operator's six defaults, always first; other standard fields off by default
  var STANDARD = [
    { key: "unique_id", label: "UID", on: true },
    { key: "name", label: "Task name", on: true },
    { key: "duration_days", label: "Duration (d)", on: true },
    { key: "percent_complete", label: "% complete", on: true },
    { key: "start", label: "Start", on: true },
    { key: "finish", label: "Finish", on: true },
    { key: "total_float_days", label: "Total float (d)", on: false },
    { key: "free_float_days", label: "Free float (d)", on: false },
    { key: "is_critical", label: "Critical", on: false },
    { key: "resource_names", label: "Resources", on: false },
    { key: "wbs", label: "WBS", on: false },
    { key: "baseline_start", label: "Baseline start", on: false },
    { key: "baseline_finish", label: "Baseline finish", on: false },
  ];

  var analysisCache = {}; // file -> {byUid, customLabels}
  var cols = null;        // [{key,label,on,custom}] built per available custom fields
  var selected = null;    // {file, metric}
  var filterText = "";    // narrows the drilled rows by text across every shown column

  function savedState() {
    try { return JSON.parse(localStorage.getItem(COLS_KEY) || "null"); } catch (e) { return null; }
  }
  function saveState() {
    if (!cols) return;
    var map = {};
    cols.forEach(function (f) { map[f.label] = f.on ? 1 : 0; });
    try { localStorage.setItem(COLS_KEY, JSON.stringify(map)); } catch (e) { /* unavailable */ }
  }
  function buildCols(customLabels) {
    cols = STANDARD.map(function (f) { return { key: f.key, label: f.label, on: f.on }; });
    (customLabels || []).forEach(function (lbl) {
      cols.push({ key: lbl, label: lbl, on: false, custom: true });
    });
    var saved = savedState();
    if (saved) {
      cols.forEach(function (f) {
        if (Object.prototype.hasOwnProperty.call(saved, f.label)) f.on = !!saved[f.label];
      });
    }
    return cols;
  }

  function el(tag, attrs) {
    var node = document.createElement(tag);
    for (var k in attrs || {}) {
      if (k === "text") node.textContent = attrs[k];
      else if (k === "class") node.className = attrs[k];
      else node.setAttribute(k, attrs[k]);
    }
    return node;
  }

  function cellValue(a, f) {
    var v = Object.prototype.hasOwnProperty.call(a, f.key) ? a[f.key]
      : (a.custom ? a.custom[f.key] : null);
    if (v === true) return "yes";
    if (v === false) return "no";
    if (v == null) return "";
    var s = String(v);
    return (window.SFGantt && SFGantt.fmtMDY(s)) || s;
  }

  function loadAnalysis(file) {
    if (analysisCache[file]) return Promise.resolve(analysisCache[file]);
    return fetch("/api/analysis/" + encodeURIComponent(file))
      .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); })
      .then(function (d) {
        var byUid = {};
        (d.activities || []).forEach(function (a) { byUid[a.unique_id] = a; });
        analysisCache[file] = { byUid: byUid, customLabels: d.custom_field_labels || [] };
        return analysisCache[file];
      });
  }

  function render() {
    if (!selected) return;
    var file = selected.file, metric = selected.metric;
    var uids = (DATA[file] || {})[metric] || [];
    loadAnalysis(file).then(function (an) {
      buildCols(an.customLabels);
      var fields = cols.filter(function (f) { return f.on; });
      drill.textContent = "";
      var label = LABELS[metric] || metric;
      drill.appendChild(el("h3", {
        text: uids.length + (uids.length === 1 ? " activity" : " activities") + " behind " +
          label + " — " + file,
      }));
      var bar = el("div", { class: "hist-drill-bar" });
      var colMount = el("span", { class: "field-toggles" });
      if (window.SFChecklist) {
        colMount.appendChild(SFChecklist.filter({
          values: cols.map(function (f) { return f.label; }),
          selected: new Set(fields.map(function (f) { return f.label; })),
          label: "Columns",
          title: "Add or remove columns (standard and custom fields) — remembered for every " +
            "metric click and the next visit",
          onChange: function (sel) {
            cols.forEach(function (f) { f.on = sel ? sel.has(f.label) : true; });
            saveState();  // SET ONCE: the choice persists across clicks + sessions
            render();
          },
        }));
      }
      bar.appendChild(colMount);
      var extra = fields.filter(function (f) {
        return ["unique_id", "name", "duration_days", "percent_complete", "start", "finish"]
          .indexOf(f.key) < 0;
      }).map(function (f) { return f.key; });
      var href = "/export/xlsx/ribbon-drill/" + encodeURIComponent(file) +
        "?metric=" + encodeURIComponent(metric) +
        (extra.length ? "&cols=" + encodeURIComponent(extra.join(",")) : "");
      bar.appendChild(el("a", { class: "btn-link", href: href, text: "Excel (this selection)" }));
      // filter the drilled activities by text across every shown column (operator 2026-07-08)
      var flt = el("input", { type: "search", placeholder: "Filter rows by any shown field" });
      flt.value = filterText;
      flt.addEventListener("input", function () { filterText = flt.value; render(); });
      bar.appendChild(flt);
      drill.appendChild(bar);
      var ql = filterText.trim().toLowerCase();
      var rows = uids.map(function (uid) { return an.byUid[uid]; }).filter(function (a) {
        if (!a) return false;
        if (!ql) return true;
        return fields.some(function (f) { return cellValue(a, f).toLowerCase().indexOf(ql) !== -1; });
      });
      bar.appendChild(el("span", {
        class: "muted", text: rows.length + " / " + uids.length + " shown",
      }));
      var scroller = el("div", { class: "hist-drill-scroll" });
      var table = el("table", { class: "hist-drill-table" });
      var thead = el("thead");
      var hr = el("tr");
      fields.forEach(function (f) { hr.appendChild(el("th", { text: f.label })); });
      thead.appendChild(hr);
      table.appendChild(thead);
      var tbody = el("tbody");
      rows.forEach(function (a) {
        var tr = el("tr");
        fields.forEach(function (f) { tr.appendChild(el("td", { text: cellValue(a, f) })); });
        tbody.appendChild(tr);
      });
      if (!rows.length) {
        var tr0 = el("tr");
        tr0.appendChild(el("td", {
          class: "muted",
          text: uids.length
            ? "No rows match the filter."
            : "No activities behind this figure — the measure counts nothing in this file.",
        }));
        tbody.appendChild(tr0);
      }
      table.appendChild(tbody);
      scroller.appendChild(table);
      drill.appendChild(scroller);
      drill.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }).catch(function () {
      drill.textContent = "Failed to load the activity data for " + file + ".";
    });
  }

  function select(cell) {
    document.querySelectorAll(".rib-cell.rib-selected").forEach(function (c) {
      c.classList.remove("rib-selected");
    });
    cell.classList.add("rib-selected");
    selected = { file: cell.getAttribute("data-file"), metric: cell.getAttribute("data-metric") };
    filterText = "";  // a new selection starts unfiltered (columns persist; the filter is per-view)
    render();
  }

  document.querySelectorAll(".rib-cell[data-metric]").forEach(function (cell) {
    cell.addEventListener("click", function () { select(cell); });
    cell.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); select(cell); }
    });
  });
})();
