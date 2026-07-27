/* Schedule Forensics — finding / signal citation drill.
 *
 * Each finding cites N activities; the table truncates to "(+66 more)". Clicking the "view all N"
 * link opens the FULL cited-activity list below the table (operator 2026-07-08) in an organized
 * chart with a Gantt-style Columns dropdown (add any standard or custom field), a Filter box, and
 * an Excel export of the selection. Fully local: the finding's citation UIDs are embedded
 * server-side (#findingsData); activity fields come from the same-origin /api/analysis/<file>
 * endpoint. Used by the Integrity findings table (one file for all findings) AND the Trend page's
 * manipulation-signals table (each signal cites its OWN version — a finding may carry a per-finding
 * `file`, which overrides the payload's top-level `file`).
 */
"use strict";

(function () {
  var drill = document.getElementById("findingsDrill");
  var dataEl = document.getElementById("findingsData");
  if (!drill || !dataEl) return;
  var payload = {};
  try { payload = JSON.parse(dataEl.textContent || "{}"); } catch (e) { payload = {}; }
  var FILE = payload.file || "";
  var FINDINGS = payload.findings || [];

  var COLS_KEY = "sf-findings-drill-cols";
  var STANDARD = [
    { key: "unique_id", label: "UID", on: true },
    { key: "name", label: "Task name", on: true },
    { key: "duration_days", label: "Duration (d)", on: true },
    { key: "percent_complete", label: "% complete", on: true },
    { key: "start", label: "Start", on: true },
    { key: "finish", label: "Finish", on: true },
    { key: "total_float_days", label: "Total float (d)", on: false },
    { key: "is_critical", label: "Critical", on: false },
    { key: "resource_names", label: "Resources", on: false },
    { key: "wbs", label: "WBS", on: false },
    { key: "baseline_start", label: "Baseline start", on: false },
    { key: "baseline_finish", label: "Baseline finish", on: false },
  ];
  var cols = null, filterText = "", selected = null, cache = {}; // cache keyed by file

  function savedState() {
    try { return JSON.parse(localStorage.getItem(COLS_KEY) || "null"); } catch (e) { return null; }
  }
  function saveState() {
    if (!cols) return;
    var m = {};
    cols.forEach(function (f) { m[f.label] = f.on ? 1 : 0; });
    try { localStorage.setItem(COLS_KEY, JSON.stringify(m)); } catch (e) { /* n/a */ }
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
    if (cache[file]) return Promise.resolve(cache[file]);
    return fetch("/api/analysis/" + encodeURIComponent(file))
      .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); })
      .then(function (d) {
        var byUid = {};
        (d.activities || []).forEach(function (a) { byUid[a.unique_id] = a; });
        cache[file] = { byUid: byUid, customLabels: d.custom_field_labels || [] };
        return cache[file];
      });
  }

  function render() {
    if (selected === null) return;
    var finding = FINDINGS[selected];
    if (!finding) return;
    var file = finding.file || FILE; // a signal cites its own version; findings fall back to FILE
    loadAnalysis(file).then(function (an) {
      buildCols(an.customLabels);
      var fields = cols.filter(function (f) { return f.on; });
      var uids = finding.uids || [];
      var ql = filterText.trim().toLowerCase();
      var rows = uids.map(function (u) { return an.byUid[u]; }).filter(function (a) {
        if (!a) return false;
        if (!ql) return true;
        return fields.some(function (f) { return cellValue(a, f).toLowerCase().indexOf(ql) !== -1; });
      });
      drill.textContent = "";
      drill.appendChild(el("h3", {
        text: 'All ' + uids.length + ' cited activities — "' + finding.title + '"',
      }));
      var bar = el("div", { class: "hist-drill-bar" });
      var colMount = el("span", { class: "field-toggles" });
      if (window.SFChecklist) {
        colMount.appendChild(SFChecklist.filter({
          values: cols.map(function (f) { return f.label; }),
          selected: new Set(fields.map(function (f) { return f.label; })),
          label: "Columns",
          title: "Add or remove columns (standard and custom fields) — remembered next visit",
          onChange: function (sel) {
            cols.forEach(function (f) { f.on = sel ? sel.has(f.label) : true; });
            saveState();
            render();
          },
        }));
      }
      bar.appendChild(colMount);
      var flt = el("input", { type: "search", placeholder: "Filter rows by any shown field" });
      flt.value = filterText;
      flt.addEventListener("input", function () { filterText = flt.value; render(); });
      bar.appendChild(flt);
      bar.appendChild(el("span", {
        class: "muted", text: rows.length + " / " + uids.length + " shown",
      }));
      var extra = fields.filter(function (f) {
        return ["unique_id", "name", "duration_days", "percent_complete", "start", "finish"]
          .indexOf(f.key) < 0;
      }).map(function (f) { return f.key; });
      var href = "/export/xlsx/activities/" + encodeURIComponent(file) +
        "?uids=" + encodeURIComponent(uids.join(",")) +
        (extra.length ? "&cols=" + encodeURIComponent(extra.join(",")) : "");
      bar.appendChild(el("a", { class: "btn-link", href: href, text: "Excel (these columns)" }));
      var close = el("a", { class: "btn-link", href: "#", text: "Close" });
      close.addEventListener("click", function (e) {
        e.preventDefault(); selected = null; filterText = ""; drill.textContent = "";
      });
      bar.appendChild(close);
      drill.appendChild(bar);
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
        tr0.appendChild(el("td", { class: "muted", text: "No rows match the filter." }));
        tbody.appendChild(tr0);
      }
      table.appendChild(tbody);
      scroller.appendChild(table);
      drill.appendChild(scroller);
      drill.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }).catch(function () { drill.textContent = "Failed to load the activity data."; });
  }

  document.querySelectorAll("a.cite-more[data-finding]").forEach(function (a) {
    a.addEventListener("click", function (e) {
      e.preventDefault();
      selected = parseInt(a.getAttribute("data-finding"), 10);
      filterText = "";
      render();
    });
  });
})();
