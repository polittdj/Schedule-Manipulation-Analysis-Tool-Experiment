/* Schedule Forensics — Driving-Path tiers drill (operator #72).
 *
 * The Driving-Path page buckets every activity driving the target into three tiers
 * (critical/driving, secondary, tertiary). This renders them as ONE organized chart with a
 * Tier + Slack(d) column, a Gantt-style Columns dropdown (add any standard or custom field,
 * remembered next visit), a Filter box, and an Excel export of exactly the chosen columns.
 * Fully local: the tier + slack per UID are embedded server-side (#drivingTiersData); the
 * activity fields come from the same-origin /api/analysis/<file> endpoint.
 */
"use strict";

(function () {
  var mount = document.getElementById("drivingTiers");
  var dataEl = document.getElementById("drivingTiersData");
  if (!mount || !dataEl) return;
  var payload = {};
  try { payload = JSON.parse(dataEl.textContent || "{}"); } catch (e) { payload = {}; }
  var FILE = payload.file || "";
  var TARGET = payload.target;
  var ROWS = payload.rows || [];

  var TIER_LABEL = { driving: "Critical / driving", secondary: "Secondary", tertiary: "Tertiary" };
  var COLS_KEY = "sf-driving-tiers-cols";
  // Tier + Slack are always-available driving-slack columns (embedded); the rest come from
  // /api/analysis. Defaults mirror the ribbon / finding drills.
  var STANDARD = [
    { key: "tier", label: "Tier", on: true },
    { key: "unique_id", label: "UID", on: true },
    { key: "name", label: "Task name", on: true },
    { key: "driving_slack_days", label: "Slack (d)", on: true },
    { key: "duration_days", label: "Duration (d)", on: false },
    { key: "percent_complete", label: "% complete", on: false },
    { key: "start", label: "Start", on: false },
    { key: "finish", label: "Finish", on: false },
    { key: "total_float_days", label: "Total float (d)", on: false },
    { key: "is_critical", label: "Critical", on: false },
    { key: "resource_names", label: "Resources", on: false },
    { key: "wbs", label: "WBS", on: false },
    { key: "baseline_start", label: "Baseline start", on: false },
    { key: "baseline_finish", label: "Baseline finish", on: false },
  ];
  var cols = null, filterText = "", cache = null;

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
    var v;
    if (f.key === "tier") v = TIER_LABEL[a.tier] || a.tier;
    else if (f.key === "driving_slack_days") v = a.driving_slack_days;
    else if (Object.prototype.hasOwnProperty.call(a, f.key)) v = a[f.key];
    else v = a.custom ? a.custom[f.key] : null;
    if (v === true) return "yes";
    if (v === false) return "no";
    if (v == null) return "";
    var s = String(v);
    return (window.SFGantt && SFGantt.fmtMDY(s)) || s;
  }
  function loadAnalysis() {
    if (cache) return Promise.resolve(cache);
    return fetch("/api/analysis/" + encodeURIComponent(FILE))
      .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); })
      .then(function (d) {
        var byUid = {};
        (d.activities || []).forEach(function (a) { byUid[a.unique_id] = a; });
        cache = { byUid: byUid, customLabels: d.custom_field_labels || [] };
        return cache;
      });
  }

  function render() {
    loadAnalysis().then(function (an) {
      buildCols(an.customLabels);
      var fields = cols.filter(function (f) { return f.on; });
      // merge the embedded tier + slack with each activity's fields
      var merged = ROWS.map(function (row) {
        var base = an.byUid[row.uid] || { unique_id: row.uid };
        var m = {};
        for (var k in base) m[k] = base[k];
        m.tier = row.tier;
        m.driving_slack_days = row.slack;
        return m;
      });
      var ql = filterText.trim().toLowerCase();
      var rows = merged.filter(function (a) {
        if (!ql) return true;
        return fields.some(function (f) { return cellValue(a, f).toLowerCase().indexOf(ql) !== -1; });
      });
      mount.textContent = "";
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
        class: "muted", text: rows.length + " / " + merged.length + " shown",
      }));
      // extra = the fields beyond the export route's built-in Tier/UID/Activity/Slack columns
      var builtin = { tier: 1, unique_id: 1, name: 1, driving_slack_days: 1 };
      var extra = fields.filter(function (f) { return !builtin[f.key]; }).map(function (f) {
        return f.key;
      });
      var href = "/export/xlsx/driving-tiers/" + encodeURIComponent(FILE) +
        "?target=" + encodeURIComponent(TARGET) +
        (extra.length ? "&cols=" + encodeURIComponent(extra.join(",")) : "");
      bar.appendChild(el("a", { class: "btn-link", href: href, text: "Excel (these columns)" }));
      mount.appendChild(bar);
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
      mount.appendChild(scroller);
    }).catch(function () { mount.textContent = "Failed to load the activity data."; });
  }

  render();
})();
