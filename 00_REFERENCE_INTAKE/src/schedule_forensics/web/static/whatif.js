/* Schedule Forensics — What-if tables: filter + add columns + Excel export.
 *
 * The Critical-Path Evolution "What-if" panel lists (1) the activities whose own changes took
 * them OFF the critical path (reverted for the counterfactual) and (2) the activities ADDED to
 * the critical path between the two versions (operator 2026-07-09). Both lists are operable:
 * a Gantt-style Columns dropdown adds any standard or custom field, a Filter box narrows the
 * rows by text across every shown column, and Excel exports exactly the chosen columns.
 * Fully local: rows are embedded server-side (#whatifData / #whatifAddedData); no network call.
 */
"use strict";

(function () {
  function initTable(cfg) {
    var mount = document.getElementById(cfg.mountId);
    var dataEl = document.getElementById(cfg.dataId);
    if (!mount || !dataEl) return;
    var payload = {};
    try { payload = JSON.parse(dataEl.textContent || "{}"); } catch (e) { payload = {}; }
    var ROWS = payload.rows || [];
    var CUSTOM = payload.customLabels || [];
    var A_FILE = mount.getAttribute("data-a") || "";
    var B_FILE = mount.getAttribute("data-b") || "";

    var STANDARD = cfg.baseCols.concat([
      { key: "duration_days", label: "Duration (d)", on: false },
      { key: "percent_complete", label: "% complete", on: false },
      { key: "start", label: "Start", on: false },
      { key: "finish", label: "Finish", on: false },
      { key: "wbs", label: "WBS", on: false },
      { key: "resource_names", label: "Resources", on: false },
    ]);
    var cols = null;
    var filterText = "";

    function savedState() {
      try { return JSON.parse(localStorage.getItem(cfg.colsKey) || "null"); } catch (e) { return null; }
    }
    function saveState() {
      if (!cols) return;
      var m = {};
      cols.forEach(function (f) { m[f.label] = f.on ? 1 : 0; });
      try { localStorage.setItem(cfg.colsKey, JSON.stringify(m)); } catch (e) { /* n/a */ }
    }
    function buildCols() {
      cols = STANDARD.map(function (f) { return { key: f.key, label: f.label, on: f.on }; });
      CUSTOM.forEach(function (lbl) { cols.push({ key: lbl, label: lbl, on: false, custom: true }); });
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

    function render() {
      buildCols();
      var fields = cols.filter(function (f) { return f.on; });
      var ql = filterText.trim().toLowerCase();
      var shown = ROWS.filter(function (a) {
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
        class: "muted", text: shown.length + " / " + ROWS.length + " " + cfg.countNoun,
      }));
      // Excel export of the chosen columns (server recomputes this pair's analysis)
      var baseKeys = cfg.baseCols.map(function (f) { return f.key; });
      var extra = fields.filter(function (f) {
        return baseKeys.indexOf(f.key) < 0;
      }).map(function (f) { return f.key; });
      if (A_FILE && B_FILE) {
        var href = cfg.exportPath + "?a=" + encodeURIComponent(A_FILE) +
          "&b=" + encodeURIComponent(B_FILE) +
          (extra.length ? "&cols=" + encodeURIComponent(extra.join(",")) : "");
        bar.appendChild(el("a", { class: "btn-link", href: href, text: "Excel (these columns)" }));
      }
      mount.appendChild(bar);

      var scroller = el("div", { class: "hist-drill-scroll" });
      var table = el("table", { class: "hist-drill-table" });
      var thead = el("thead");
      var hr = el("tr");
      fields.forEach(function (f) { hr.appendChild(el("th", { text: f.label })); });
      thead.appendChild(hr);
      table.appendChild(thead);
      var tbody = el("tbody");
      shown.forEach(function (a) {
        var tr = el("tr");
        fields.forEach(function (f) { tr.appendChild(el("td", { text: cellValue(a, f) })); });
        tbody.appendChild(tr);
      });
      if (!shown.length) {
        var tr0 = el("tr");
        tr0.appendChild(el("td", { class: "muted", text: "No rows match the filter." }));
        tbody.appendChild(tr0);
      }
      table.appendChild(tbody);
      scroller.appendChild(table);
      mount.appendChild(scroller);
    }

    render();
  }

  // reverted-changes table (activities whose own changes took them OFF the path)
  initTable({
    mountId: "whatifTable",
    dataId: "whatifData",
    colsKey: "sf-whatif-cols",
    countNoun: "change(s)",
    exportPath: "/export/xlsx/whatif",
    baseCols: [
      { key: "unique_id", label: "UID", on: true },
      { key: "name", label: "Activity", on: true },
      { key: "why_left", label: "Why it left", on: true },
      { key: "change_reverted", label: "Change reverted", on: true },
    ],
  });

  // added-to-the-critical-path table (operator 2026-07-09)
  initTable({
    mountId: "whatifAddedTable",
    dataId: "whatifAddedData",
    colsKey: "sf-whatif-added-cols",
    countNoun: "activity(ies)",
    exportPath: "/export/xlsx/whatif-added",
    baseCols: [
      { key: "unique_id", label: "UID", on: true },
      { key: "name", label: "Activity", on: true },
      { key: "why_entered", label: "Why it entered", on: true },
      { key: "detail", label: "Detail", on: true },
    ],
  });
})();
