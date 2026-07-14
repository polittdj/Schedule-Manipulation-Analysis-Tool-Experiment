/* Metric Workbench (ADR-0204) — Acumen-style: the selectable library (server-rendered on the
 * left) drives a ribbon of chosen metrics x versions; clicking a value drills into the
 * activities behind it with filter / sort / group / add-columns / Excel. Vendored, no build
 * step, CSP-safe (DOM built with createElement + textContent; no innerHTML from data). */
(function () {
  "use strict";

  var DATA = null; // /api/workbench payload
  var drill = { rows: [], columns: [], fields: [], extra: [], sort: null, asc: true, group: "", filter: "", metric: "", file: "", name: "" };

  function el(tag, attrs, text) {
    var n = document.createElement(tag);
    if (attrs) Object.keys(attrs).forEach(function (k) { n.setAttribute(k, attrs[k]); });
    if (text != null) n.textContent = text;
    return n;
  }

  function fmt(cell, unit) {
    // "—" for a missing cell OR an unmeasurable metric (applicable === false → the value is a
    // placeholder 0, not a real measurement); informational extras stay applicable.
    if (cell == null || cell.value == null || cell.applicable === false) return "—";
    var v = cell.value;
    if (unit === "%") return v.toFixed(2) + "%";
    if (unit === "ratio") return v.toFixed(2);
    if (unit === "days") return v.toFixed(1);
    return String(Math.round(v)); // count
  }

  function statusClass(status) {
    if (status === "PASS") return "wb-pass";
    if (status === "FAIL") return "wb-fail";
    return "wb-na";
  }

  function checkedMetrics() {
    var picks = {};
    var boxes = document.querySelectorAll(".wb-pick");
    for (var i = 0; i < boxes.length; i++) picks[boxes[i].value] = boxes[i].checked;
    return picks;
  }

  // ── the ribbon: metrics (rows) x versions (columns), only the checked metrics ──
  function renderRibbon() {
    var host = document.getElementById("wbRibbon");
    host.innerHTML = "";
    if (!DATA) { host.appendChild(el("p", { class: "muted" }, "Loading…")); return; }
    var picks = checkedMetrics();
    var metrics = DATA.metrics.filter(function (m) { return picks[m.id]; });
    if (!metrics.length) { host.appendChild(el("p", { class: "muted" }, "Select one or more metrics on the left.")); return; }

    var table = el("table", { class: "wb-matrix" });
    var thead = el("thead");
    var hr = el("tr");
    hr.appendChild(el("th", { scope: "col" }, "Metric"));
    DATA.versions.forEach(function (ver) {
      var th = el("th", { scope: "col", class: "wb-ver" });
      th.appendChild(el("div", { class: "wb-ver-label" }, ver.label));
      if (ver.status) th.appendChild(el("div", { class: "wb-ver-date" }, ver.status));
      hr.appendChild(th);
    });
    thead.appendChild(hr);
    table.appendChild(thead);

    var tbody = el("tbody");
    var lastFamily = null;
    metrics.forEach(function (m) {
      if (m.family !== lastFamily) {
        lastFamily = m.family;
        var fr = el("tr", { class: "wb-fam-row" });
        var fc = el("th", { colspan: String(DATA.versions.length + 1), scope: "colgroup" }, m.family);
        fr.appendChild(fc);
        tbody.appendChild(fr);
      }
      var tr = el("tr");
      var nameCell = el("th", { scope: "row", class: "wb-metric-name", title: m.describe }, m.name);
      tr.appendChild(nameCell);
      DATA.versions.forEach(function (ver) {
        var cell = DATA.cells[m.id][ver.key];
        var td = el("td", { class: "wb-cell " + statusClass(cell ? cell.status : "NA") }, fmt(cell, m.unit));
        if (cell && cell.offenders > 0) {
          td.classList.add("wb-clickable");
          td.setAttribute("tabindex", "0");
          td.setAttribute("role", "button");
          td.setAttribute("title", cell.offenders + " activities — click to list them");
          var open = function () { openDrill(m.id, m.name, ver.key, ver.label); };
          td.addEventListener("click", open);
          td.addEventListener("keydown", function (e) { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); open(); } });
        }
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    host.appendChild(table);
  }

  // ── the drill grid: filter / sort / group / add columns / Excel ──
  function openDrill(metricId, metricName, fileKey, fileLabel) {
    drill.metric = metricId; drill.file = fileKey; drill.name = metricName;
    drill.extra = []; drill.sort = null; drill.asc = true; drill.group = ""; drill.filter = "";
    var host = document.getElementById("wbDrill");
    host.innerHTML = "";
    host.appendChild(el("p", { class: "muted" }, "Loading activities behind " + metricName + " · " + fileLabel + "…"));
    fetch("/api/workbench/drill?metric=" + encodeURIComponent(metricId) + "&file=" + encodeURIComponent(fileKey))
      .then(function (r) { return r.json().then(function (j) { if (!r.ok) throw new Error(j.error || "failed"); return j; }); })
      .then(function (j) {
        drill.rows = j.rows; drill.columns = j.columns; drill.fields = j.fields;
        renderDrill(metricName, fileLabel);
      })
      .catch(function (e) { host.innerHTML = ""; host.appendChild(el("p", { class: "muted" }, "Could not load the drill: " + e.message)); });
  }

  function drillValue(row, col) {
    if (col === "UID") return row.uid;
    if (Object.prototype.hasOwnProperty.call(row, col)) return row[col];
    return row.fields ? row.fields[col] : null;
  }

  function visibleColumns() { return ["UID"].concat(drill.columns).concat(drill.extra); }

  function filteredSortedRows() {
    var cols = visibleColumns();
    var rows = drill.rows.filter(function (r) {
      if (!drill.filter) return true;
      var needle = drill.filter.toLowerCase();
      for (var i = 0; i < cols.length; i++) {
        var v = drillValue(r, cols[i]);
        if (v != null && String(v).toLowerCase().indexOf(needle) >= 0) return true;
      }
      return false;
    });
    if (drill.sort) {
      rows = rows.slice().sort(function (a, b) {
        var va = drillValue(a, drill.sort), vb = drillValue(b, drill.sort);
        if (va == null) return 1; if (vb == null) return -1;
        var na = parseFloat(va), nb = parseFloat(vb);
        var cmp = (!isNaN(na) && !isNaN(nb)) ? na - nb : String(va).localeCompare(String(vb));
        return drill.asc ? cmp : -cmp;
      });
    }
    return rows;
  }

  function exportHref() {
    var q = "?metric=" + encodeURIComponent(drill.metric);
    if (drill.extra.length) q += "&cols=" + encodeURIComponent(drill.extra.join(","));
    return "/export/xlsx/workbench-drill/" + encodeURIComponent(drill.file) + q;
  }

  function renderDrill(metricName, fileLabel) {
    var host = document.getElementById("wbDrill");
    host.innerHTML = "";
    var panel = el("div", { class: "panel" });
    panel.appendChild(el("h3", null, "Behind: " + metricName + " · " + fileLabel));

    var bar = el("div", { class: "viz-controls wb-drill-bar" });
    var filterIn = el("input", { type: "search", placeholder: "Filter…", "aria-label": "Filter rows" });
    filterIn.value = drill.filter;
    filterIn.addEventListener("input", function () { drill.filter = filterIn.value; renderGrid(panel); });
    bar.appendChild(labelWrap("Filter", filterIn));

    var groupSel = el("select");
    groupSel.appendChild(el("option", { value: "" }, "(none)"));
    drill.fields.forEach(function (f) { groupSel.appendChild(el("option", { value: f }, f)); });
    groupSel.value = drill.group;
    groupSel.addEventListener("change", function () { drill.group = groupSel.value; renderGrid(panel); });
    bar.appendChild(labelWrap("Group by", groupSel));

    var colSel = el("select");
    colSel.appendChild(el("option", { value: "" }, "+ add column…"));
    drill.fields.forEach(function (f) {
      if (drill.extra.indexOf(f) < 0 && drill.columns.indexOf(f) < 0) colSel.appendChild(el("option", { value: f }, f));
    });
    colSel.addEventListener("change", function () {
      if (colSel.value) { drill.extra.push(colSel.value); renderDrill(metricName, fileLabel); }
    });
    bar.appendChild(labelWrap("Columns", colSel));

    var xls = el("a", { class: "btn", href: exportHref() }, "Export (Excel)");
    bar.appendChild(xls);
    panel.appendChild(bar);

    var gridHost = el("div", { class: "wb-grid-host" });
    gridHost.id = "wbGridHost";
    panel.appendChild(gridHost);
    host.appendChild(panel);
    renderGrid(panel);
  }

  function labelWrap(text, control) {
    var l = el("label");
    l.appendChild(document.createTextNode(text + " "));
    l.appendChild(control);
    return l;
  }

  function renderGrid(panel) {
    var gridHost = panel.querySelector("#wbGridHost");
    gridHost.innerHTML = "";
    var cols = visibleColumns();
    var rows = filteredSortedRows();
    var count = el("p", { class: "muted wb-count" }, rows.length + " activit" + (rows.length === 1 ? "y" : "ies"));
    gridHost.appendChild(count);

    var table = el("table", { class: "wb-grid" });
    var thead = el("thead");
    var hr = el("tr");
    cols.forEach(function (c) {
      var th = el("th", { scope: "col", class: "wb-sortable" });
      th.appendChild(document.createTextNode(c));
      if (drill.sort === c) th.appendChild(el("span", { class: "wb-arrow" }, drill.asc ? " ▲" : " ▼"));
      if (drill.extra.indexOf(c) >= 0) {
        var x = el("button", { type: "button", class: "linkbtn wb-colx", title: "remove column" }, "×");
        x.addEventListener("click", function (e) { e.stopPropagation(); drill.extra = drill.extra.filter(function (k) { return k !== c; }); renderDrill(drill.name, ""); });
        th.appendChild(x);
      }
      th.addEventListener("click", function () { if (drill.sort === c) drill.asc = !drill.asc; else { drill.sort = c; drill.asc = true; } renderGrid(panel); });
      hr.appendChild(th);
    });
    thead.appendChild(hr);
    table.appendChild(thead);

    var tbody = el("tbody");
    if (drill.group) {
      var groups = {};
      var order = [];
      rows.forEach(function (r) {
        var k = drillValue(r, drill.group);
        k = (k == null || k === "") ? "(blank)" : String(k);
        if (!groups[k]) { groups[k] = []; order.push(k); }
        groups[k].push(r);
      });
      order.sort();
      order.forEach(function (k) {
        var gr = el("tr", { class: "wb-grp" });
        gr.appendChild(el("th", { colspan: String(cols.length), scope: "colgroup" }, drill.group + ": " + k + "  (" + groups[k].length + ")"));
        tbody.appendChild(gr);
        groups[k].forEach(function (r) { tbody.appendChild(gridRow(r, cols)); });
      });
    } else {
      rows.forEach(function (r) { tbody.appendChild(gridRow(r, cols)); });
    }
    table.appendChild(tbody);
    gridHost.appendChild(table);
  }

  function gridRow(r, cols) {
    var tr = el("tr");
    cols.forEach(function (c) {
      var v = drillValue(r, c);
      tr.appendChild(el("td", null, v == null ? "" : String(v)));
    });
    return tr;
  }

  // ── library controls ──
  function wireLibrary() {
    document.querySelectorAll(".wb-pick").forEach(function (b) { b.addEventListener("change", renderRibbon); });
    var all = document.getElementById("wbAll"), none = document.getElementById("wbNone");
    if (all) all.addEventListener("click", function () { setAll(true); });
    if (none) none.addEventListener("click", function () { setAll(false); });
    document.querySelectorAll(".wb-fam-all").forEach(function (b) { b.addEventListener("click", function () { setFamily(b.getAttribute("data-family"), true); }); });
    document.querySelectorAll(".wb-fam-none").forEach(function (b) { b.addEventListener("click", function () { setFamily(b.getAttribute("data-family"), false); }); });
  }
  function setAll(v) { document.querySelectorAll(".wb-pick").forEach(function (b) { b.checked = v; }); renderRibbon(); }
  function setFamily(fam, v) {
    var box = document.querySelector('.wb-family[data-family="' + fam + '"]');
    if (box) box.querySelectorAll(".wb-pick").forEach(function (b) { b.checked = v; });
    renderRibbon();
  }

  function init() {
    wireLibrary();
    var host = document.getElementById("wbRibbon");
    if (host) host.appendChild(el("p", { class: "muted" }, "Loading…"));
    fetch("/api/workbench")
      .then(function (r) { return r.json().then(function (j) { if (!r.ok) throw new Error(j.error || "failed"); return j; }); })
      .then(function (j) { DATA = j; renderRibbon(); })
      .catch(function (e) { if (host) { host.innerHTML = ""; host.appendChild(el("p", { class: "muted" }, "Could not load the workbench: " + e.message)); } });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
