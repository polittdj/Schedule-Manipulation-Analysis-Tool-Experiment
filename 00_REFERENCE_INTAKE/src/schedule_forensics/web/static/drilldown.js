/* Shared activity drill-down (issue #331 follow-up) — click any element marked `sf-drill`
 * (a scorecard line, a churn-bar segment, a status-bar segment) to list the activities behind it
 * in a modal grid where you can filter, add/remove columns, sort, and export to Excel.
 *
 * The trigger element carries data-uids (comma-separated UniqueIDs), data-file (the schedule key)
 * and data-title (a heading). This script fetches /api/activities/drill for that UID set and
 * renders the same grid the Metric Workbench uses. Fully local, CSP-safe (DOM built with
 * createElement + textContent; no innerHTML from data), no external asset (air-gap, Law 1).
 */
"use strict";

(function () {
  var BASE_COLS = ["Name", "Duration (d)", "% complete", "Start", "Finish"];
  var state = null; // {rows, columns, fields, extra, sort, asc, filter, uids, file, title}

  function el(tag, attrs, text) {
    var n = document.createElement(tag);
    if (attrs) Object.keys(attrs).forEach(function (k) { n.setAttribute(k, attrs[k]); });
    if (text != null) n.textContent = text;
    return n;
  }

  function overlay() {
    var o = document.getElementById("sfDrillOverlay");
    if (o) return o;
    o = el("div", { id: "sfDrillOverlay", class: "sf-drill-overlay", role: "dialog", "aria-modal": "true" });
    o.addEventListener("click", function (e) { if (e.target === o) close(); });
    document.addEventListener("keydown", function (e) { if (e.key === "Escape") close(); });
    (document.getElementById("sfDrillMount") || document.body).appendChild(o);
    return o;
  }

  function close() {
    var o = document.getElementById("sfDrillOverlay");
    if (o) o.parentNode.removeChild(o);
    state = null;
  }

  function drillValue(row, col) {
    if (col === "UID") return row.uid;
    if (Object.prototype.hasOwnProperty.call(row, col)) return row[col];
    return row.fields ? row.fields[col] : null;
  }

  function visibleColumns() { return ["UID"].concat(state.columns).concat(state.extra); }

  function filteredSortedRows() {
    var cols = visibleColumns();
    var rows = state.rows.filter(function (r) {
      if (!state.filter) return true;
      var needle = state.filter.toLowerCase();
      for (var i = 0; i < cols.length; i++) {
        var v = drillValue(r, cols[i]);
        if (v != null && String(v).toLowerCase().indexOf(needle) >= 0) return true;
      }
      return false;
    });
    if (state.sort) {
      rows = rows.slice().sort(function (a, b) {
        var va = drillValue(a, state.sort), vb = drillValue(b, state.sort);
        if (va == null) return 1; if (vb == null) return -1;
        var na = parseFloat(va), nb = parseFloat(vb);
        var cmp = (!isNaN(na) && !isNaN(nb)) ? na - nb : String(va).localeCompare(String(vb));
        return state.asc ? cmp : -cmp;
      });
    }
    return rows;
  }

  function exportHref() {
    var q = "?file=" + encodeURIComponent(state.file) +
            "&uids=" + encodeURIComponent(state.uids) +
            "&title=" + encodeURIComponent(state.title);
    if (state.extra.length) q += "&cols=" + encodeURIComponent(state.extra.join(","));
    return "/export/xlsx/activities-drill" + q;
  }

  function labelWrap(text, control) {
    var l = el("label");
    l.appendChild(document.createTextNode(text + " "));
    l.appendChild(control);
    return l;
  }

  function render() {
    var o = overlay();
    o.innerHTML = "";
    var dialog = el("div", { class: "sf-drill-dialog panel" });

    var head = el("div", { class: "sf-drill-head" });
    head.appendChild(el("h3", null, state.title + " · " + state.label));
    var x = el("button", { type: "button", class: "linkbtn sf-drill-close", "aria-label": "Close" }, "✕");
    x.addEventListener("click", close);
    head.appendChild(x);
    dialog.appendChild(head);

    var bar = el("div", { class: "viz-controls" });
    var filterIn = el("input", { type: "search", placeholder: "Filter…", "aria-label": "Filter rows" });
    filterIn.value = state.filter;
    filterIn.addEventListener("input", function () { state.filter = filterIn.value; renderGrid(dialog); });
    bar.appendChild(labelWrap("Filter", filterIn));

    var colSel = el("select");
    colSel.appendChild(el("option", { value: "" }, "+ add column…"));
    state.fields.forEach(function (f) {
      if (state.extra.indexOf(f) < 0 && state.columns.indexOf(f) < 0) {
        colSel.appendChild(el("option", { value: f }, f));
      }
    });
    colSel.addEventListener("change", function () {
      if (colSel.value) { state.extra.push(colSel.value); render(); }
    });
    bar.appendChild(labelWrap("Columns", colSel));

    bar.appendChild(el("a", { class: "btn", href: exportHref() }, "Export (Excel)"));
    dialog.appendChild(bar);

    var gridHost = el("div", { class: "sf-drill-grid-host" });
    dialog.appendChild(gridHost);
    o.appendChild(dialog);
    renderGrid(dialog);
  }

  function renderGrid(dialog) {
    var gridHost = dialog.querySelector(".sf-drill-grid-host");
    gridHost.innerHTML = "";
    var cols = visibleColumns();
    var rows = filteredSortedRows();
    gridHost.appendChild(el("p", { class: "muted" }, rows.length + " activit" + (rows.length === 1 ? "y" : "ies")));

    var table = el("table", { class: "scorecard-table sf-drill-grid" });
    var hr = el("tr");
    cols.forEach(function (c) {
      var th = el("th", { scope: "col", class: "sf-drill-sortable" });
      th.appendChild(document.createTextNode(c));
      if (state.sort === c) th.appendChild(el("span", null, state.asc ? " ▲" : " ▼"));
      if (state.extra.indexOf(c) >= 0) {
        var rm = el("button", { type: "button", class: "linkbtn", title: "remove column" }, " ✕");
        rm.addEventListener("click", function (e) {
          e.stopPropagation();
          state.extra = state.extra.filter(function (k) { return k !== c; });
          render();
        });
        th.appendChild(rm);
      }
      th.addEventListener("click", function () {
        if (state.sort === c) state.asc = !state.asc; else { state.sort = c; state.asc = true; }
        renderGrid(dialog);
      });
      hr.appendChild(th);
    });
    table.appendChild(hr);
    rows.forEach(function (r) {
      var tr = el("tr");
      cols.forEach(function (c) {
        var v = drillValue(r, c);
        tr.appendChild(el("td", null, v == null ? "" : String(v)));
      });
      table.appendChild(tr);
    });
    gridHost.appendChild(table);
  }

  function open(uids, file, title) {
    var o = overlay();
    o.innerHTML = "";
    o.appendChild(el("p", { class: "panel muted" }, "Loading activities…"));
    fetch("/api/activities/drill?file=" + encodeURIComponent(file) +
          "&uids=" + encodeURIComponent(uids) +
          "&title=" + encodeURIComponent(title))
      .then(function (r) { return r.json().then(function (j) { if (!r.ok) throw new Error(j.error || "failed"); return j; }); })
      .then(function (j) {
        state = {
          rows: j.rows || [], columns: j.columns || BASE_COLS, fields: j.fields || [],
          extra: [], sort: null, asc: true, filter: "",
          uids: uids, file: j.file || file, title: j.title || title, label: j.label || ""
        };
        render();
      })
      .catch(function (e) {
        o.innerHTML = "";
        var p = el("div", { class: "panel" });
        p.appendChild(el("p", { class: "notice err" }, "Could not load the activities: " + e.message));
        var x = el("button", { type: "button", class: "btn" }, "Close");
        x.addEventListener("click", close);
        p.appendChild(x);
        o.appendChild(p);
      });
  }

  // delegated: works for server-rendered AND any dynamically added .sf-drill trigger
  function triggerFrom(node) {
    while (node && node !== document) {
      if (node.classList && node.classList.contains("sf-drill")) return node;
      node = node.parentNode;
    }
    return null;
  }
  function fire(t) {
    var uids = t.getAttribute("data-uids") || "";
    var file = t.getAttribute("data-file") || "";
    var title = t.getAttribute("data-title") || "Activities";
    if (uids) open(uids, file, title);
  }
  document.addEventListener("click", function (e) {
    var t = triggerFrom(e.target);
    if (t) { e.preventDefault(); fire(t); }
  });
  document.addEventListener("keydown", function (e) {
    if (e.key !== "Enter" && e.key !== " ") return;
    var t = triggerFrom(e.target);
    if (t) { e.preventDefault(); fire(t); }
  });

  // Tag any element (incl. an SVG <rect>/<g>) as a drill trigger for a UID set. Charts call this
  // per bar so a click lists the activities behind it. `uids` is an array or comma string; a falsy
  // / empty set leaves the node inert (no cursor, no class) so empty bars aren't clickable.
  function mark(node, uids, file, title) {
    if (!node) return node;
    var ids = Array.isArray(uids) ? uids.filter(function (u) { return u != null; }).join(",") : (uids || "");
    if (!ids) return node;
    var cls = node.getAttribute("class") || "";
    if (cls.split(/\s+/).indexOf("sf-drill") < 0) node.setAttribute("class", (cls + " sf-drill").trim());
    node.setAttribute("data-uids", ids);
    node.setAttribute("data-file", file == null ? "" : String(file));
    node.setAttribute("data-title", title || "Activities");
    node.setAttribute("role", "button");
    node.setAttribute("tabindex", "0");
    if (node.style) node.style.cursor = "pointer";
    return node;
  }

  window.SFDrill = { open: open, close: close, mark: mark };
})();
