/* Schedule Forensics — SSI editable schedule grid (ADR-0123). Vendored, dependency-free, same-origin
 * only (air-gap). The whole schedule as an SSI-style grid: per-task Risk Ranking Factor (1-5) and
 * Best/Worst Case days are edited inline; a focus radio picks the analysis event. Edits queue in a
 * per-UID pending map and are batch-saved to /sra/grid on "Save grid" — no full re-render per cell.
 * The Microsoft-Project Year/Quarter/Month timeline + gridlines come from window.SFGantt (gantt.js).
 */
"use strict";

(function () {
  var host = document.getElementById("ssiGrid");
  if (!host || !window.SFGantt) return;
  var statusEl = document.getElementById("ssiGridStatus");
  var zoomEl = document.getElementById("ssiGridZoom");
  var DAY_MS = SFGantt.DAY_MS;
  var el = SFGantt.el;

  var rows = [];
  var dataDate = null;
  var pending = {}; // uid -> {uid, factor?, bc_days?, wc_days?, focus?}
  var lastFrozenWidth = 0; // MEASURED frozen data-column width (SFGantt.freezeColumns return)

  var forcedPx = null; // set by "View entire project"; cleared when the zoom slider is nudged
  var extraRightDays = 0; // unlimited right scroll (ADR-0187): grows at the pane's right edge
  function pxPerDay() {
    // the Timescale dialog's Size % scales the timeline in BOTH modes (fit + slider), so Size
    // works even after "View entire project" fits the page.
    var size = window.SFTimescale ? window.SFTimescale.sizeFactor() : 1;
    if (!(size > 0)) size = 1;
    if (forcedPx && forcedPx > 0) return forcedPx * size;
    var v = zoomEl ? parseFloat(zoomEl.value) : 1.4;
    return (isNaN(v) || v <= 0 ? 1.4 : v) * size;
  }
  // Auto-scale the timeline so the whole project span fits the visible width (no horizontal
  // scroll). The fill space subtracts the REAL measured frozen-column width recorded on each
  // paint (like path.js) — not a hard-coded estimate — so the bars use the entire page.
  function fitToProject() {
    var t0 = null, t1 = null;
    rows.forEach(function (r) {
      if (r.start) { var s = Date.parse(r.start); if (!isNaN(s)) t0 = t0 === null ? s : Math.min(t0, s); }
      if (r.finish) { var f = Date.parse(r.finish); if (!isNaN(f)) t1 = t1 === null ? f : Math.max(t1, f); }
    });
    if (dataDate) { var a = Date.parse(dataDate); if (!isNaN(a)) { t0 = t0 === null ? a : Math.min(t0, a); t1 = t1 === null ? a : Math.max(t1, a); } }
    if (t0 === null || t1 === null) return;
    var days = Math.max(1, (t1 - t0) / DAY_MS) + 4;
    var avail = Math.max(240, (host ? host.clientWidth : 1100) - (lastFrozenWidth || 520) - 18);
    forcedPx = Math.max(0.02, avail / days);
    render();
  }

  // Time axis from rows carrying ISO start/finish, padded two days each side and stretched to the
  // data date — the same construction every Gantt on the site uses.
  function buildAxis(items) {
    var px = pxPerDay();
    var t0 = null, t1 = null;
    items.forEach(function (it) {
      if (it.start) { var s = Date.parse(it.start); if (!isNaN(s)) t0 = t0 === null ? s : Math.min(t0, s); }
      if (it.finish) { var f = Date.parse(it.finish); if (!isNaN(f)) t1 = t1 === null ? f : Math.max(t1, f); }
    });
    if (dataDate) {
      var a = Date.parse(dataDate);
      if (!isNaN(a) && t0 !== null && t1 !== null) { t0 = Math.min(t0, a); t1 = Math.max(t1, a); }
    }
    if (t0 === null || t1 === null) return null;
    t0 -= 2 * DAY_MS; t1 += (2 + extraRightDays) * DAY_MS; // right pad grows via edge-extend (ADR-0187)
    var width = Math.max(120, Math.round((t1 - t0) / DAY_MS) * px);
    return { t0: t0, t1: t1, width: width, x: function (ms) { return Math.round(((ms - t0) / DAY_MS) * px); } };
  }

  function mark(uid, key, value) {
    if (!pending[uid]) pending[uid] = { uid: uid };
    pending[uid][key] = value;
    var n = Object.keys(pending).length;
    statusEl.textContent = n + " task(s) with unsaved edits.";
  }

  function inputCell(r, key, attrs) {
    var td = el("td");
    var a = { type: "number", class: "sra-inp", "data-uid": String(r.unique_id), "data-key": key };
    Object.keys(attrs || {}).forEach(function (k) { a[k] = attrs[k]; });
    var inp = el("input", a);
    if (r[key] != null) inp.value = r[key];
    // a body repaint (e.g. a column-filter change) must not silently blank an unsaved edit
    if (pending[r.unique_id] && pending[r.unique_id][key] != null) inp.value = pending[r.unique_id][key];
    td.appendChild(inp);
    return td;
  }

  function focusCell(r) {
    var td = el("td", { class: "sra-focus-cell" });
    var radio = el("input", { type: "radio", name: "ssiFocus", class: "sra-focus", "data-uid": String(r.unique_id) });
    if (r.is_focus || (pending[r.unique_id] && pending[r.unique_id].focus)) radio.checked = true;
    td.appendChild(radio);
    return td;
  }

  // --- MS-Project per-column checklist filters on the non-editable columns -----------------
  var FILTER_COLS = [
    { key: "unique_id", label: "UID" },
    { key: "name", label: "Task" },
    { key: "remaining_days", label: "Rem d" },
  ];
  var colFilters = {}; // key -> selected-value Set (null = unfiltered; an empty Set hides all)
  function cellText(r, key) { var v = r[key]; return v == null ? "" : String(v); }
  function distinctValues(key) {
    var seen = {};
    rows.forEach(function (r) { seen[cellText(r, key)] = true; });
    return Object.keys(seen).sort(function (a, b) {
      var na = parseFloat(a), nb = parseFloat(b);
      var bothNum = !isNaN(na) && !isNaN(nb) && /^-?\d/.test(a) && /^-?\d/.test(b);
      return bothNum ? na - nb : a < b ? -1 : a > b ? 1 : 0;
    });
  }
  function rowMatchesFilters(r) {
    return FILTER_COLS.every(function (f) {
      var sel = colFilters[f.key];
      return !sel || sel.has(cellText(r, f.key));
    });
  }
  // "show completed tasks" (parity with the Activities Gantt — ADR-0186): unchecked hides every
  // 100%-complete row, including fully complete summaries (same rule as app.js rowVisible)
  function includeCompleted() {
    var cb = document.getElementById("ssiShowDone");
    return !cb || cb.checked;
  }
  function rowVisible(r) {
    if (!includeCompleted() && (r.complete || (r.percent_complete || 0) >= 100)) return false;
    return rowMatchesFilters(r);
  }

  // --- Group by ANY field (operator #80: match the Path Gantts) --------------------------------
  var GRID_COLS = 7; // UID, Task, Rem d, Factor, BC d, WC d, Focus (the frozen data columns)
  function groupSelect() { return document.getElementById("ssiGridGroupBy"); }
  function groupBy() { var s = groupSelect(); return s ? s.value : ""; }
  function groupKeyOf(r, key) {
    if (key.indexOf("custom:") === 0) {
      var lb = key.slice(7);
      return (r.custom && r.custom[lb] != null && r.custom[lb] !== "" ? String(r.custom[lb]) : "(blank)");
    }
    var v = r[key];
    if (v === true) return "Yes";
    if (v === false) return "No";
    return v === null || v === undefined || v === "" ? "(blank)" : String(v);
  }
  // group the (already-filtered) list into [label, members] pairs, preserving first-seen order
  function groupList(list, key) {
    var order = [], byVal = {};
    list.forEach(function (r) {
      var k = groupKeyOf(r, key);
      if (!byVal[k]) { byVal[k] = []; order.push(k); }
      byVal[k].push(r);
    });
    return order.map(function (k) { return [k, byVal[k]]; });
  }
  // one-time: append the loaded rows' custom-field labels as group-by options (like path.js)
  function populateGroupCustom() {
    var sel = groupSelect();
    if (!sel) return;
    var have = {};
    Array.prototype.forEach.call(sel.options, function (o) { have[o.value] = true; });
    var labels = {};
    rows.forEach(function (r) {
      if (r.custom) Object.keys(r.custom).forEach(function (lb) { labels[lb] = true; });
    });
    Object.keys(labels).sort().forEach(function (lb) {
      if (have["custom:" + lb]) return;
      var o = document.createElement("option");
      o.value = "custom:" + lb;
      o.textContent = lb + " (custom)";
      sel.appendChild(o);
    });
  }

  // MS-Project "dates on bars" (ADR-0186): MM/DD/YYYY labels at the bar ends, clamped into
  // the track (the same construction as app.js barLabel).
  var LABEL_W = 64;
  function barDatesOn() {
    var cb = document.getElementById("ssiBarDates");
    return !!(cb && cb.checked);
  }
  function barLabel(track, axis, anchor, side, iso) {
    if (!iso) return;
    var lx = side === "s" ? anchor - LABEL_W : anchor;
    lx = Math.max(0, Math.min(axis.width - LABEL_W, lx));
    track.appendChild(el("div", {
      class: "g-barlabel g-barlabel-" + side,
      style: "left:" + lx + "px;width:" + LABEL_W + "px",
      text: SFGantt.fmtMDY(iso),
    }));
  }

  // The scheduled bar (start -> finish, accurate) plus a translucent Best/Worst-case finish envelope
  // (start + BC..WC days, a calendar-day projection — an approximate hint; the authoritative figures
  // are the BC/WC day columns and the SSI run).
  function timelineCell(r, axis, grid) {
    var cell = el("td", { class: "g-cell" });
    var track = el("div", { class: "g-track", style: "width:" + axis.width + "px" });
    SFGantt.paintGrid(track, grid);
    if (dataDate) { var sd = Date.parse(dataDate); if (!isNaN(sd)) track.appendChild(el("div", { class: "g-status", style: "left:" + axis.x(sd) + "px" })); }
    var s = r.start ? Date.parse(r.start) : null;
    var f = r.finish ? Date.parse(r.finish) : null;
    if (r.is_milestone && s != null) {
      track.appendChild(el("div", { class: "g-ms", title: r.name + " (milestone) " + (SFGantt.fmtMDY(r.start) || r.start), style: "left:" + axis.x(s) + "px" }));
      if (barDatesOn()) barLabel(track, axis, axis.x(s) + 7, "f", r.finish || r.start);
    } else if (s != null && f != null) {
      if (r.editable && r.bc_days != null && r.wc_days != null) {
        var bcEnd = s + r.bc_days * DAY_MS, wcEnd = s + r.wc_days * DAY_MS;
        var l = axis.x(Math.min(bcEnd, wcEnd)), w = Math.max(2, axis.x(Math.max(bcEnd, wcEnd)) - l);
        track.appendChild(el("div", {
          class: "g-envelope", title: "Best/Worst-case finish " + r.bc_days + "/" + r.wc_days + " d (approx)",
          style: "left:" + l + "px;width:" + w + "px",
        }));
      }
      var left = axis.x(s), width = Math.max(2, axis.x(f) - left);
      var cls = r.is_summary ? "g-bar g-sum" : r.is_critical ? "g-bar g-crit" : "g-bar";
      var bar = el("div", { class: cls, title: r.name + "  " + (SFGantt.fmtMDY(r.start) || r.start) + " -> " + (SFGantt.fmtMDY(r.finish) || r.finish), style: "left:" + left + "px;width:" + width + "px" });
      if (!r.is_summary && (r.complete || r.percent_complete > 0)) {
        bar.appendChild(el("div", { class: "g-done", style: "width:" + (r.complete ? 100 : Math.min(100, r.percent_complete)) + "%" }));
      }
      track.appendChild(bar);
      // MS-Project "dates on bars" (parity with the Activities Gantt — ADR-0186)
      if (barDatesOn()) {
        barLabel(track, axis, left - 3, "s", r.start);
        barLabel(track, axis, left + width + 3, "f", r.finish);
      }
    }
    cell.appendChild(track);
    SFGantt.paintNonwork(cell, axis); // continuous weekend/holiday shading over the full row
    return cell;
  }

  // repaint only the body rows (a column-filter change keeps the open dropdown + header alive)
  function paintBody(tbody, axis, grid) {
    var list = rows.filter(rowVisible);
    tbody.innerHTML = "";
    var paintOne = function (r) {
      var tr = el("tr");
      tr.setAttribute("data-uid", String(r.unique_id)); // Find-a-UID jump
      if (r.is_critical) tr.className = "crit";
      if (r.is_summary) tr.className = (tr.className + " sum").trim();
      if (r.has_risk) tr.className = (tr.className + " sra-risk").trim();
      // MS-Project Task Information on the NON-editable cells (UID / name) — the shared
      // dialog (ADR-0186); the grid rows already carry the full _activity_rows payload.
      // Editable input cells keep plain click-to-edit (no dialog stealing the focus).
      var uidTd = el("td", { text: String(r.unique_id) });
      var nm = el("td", { class: "name-cell", text: r.name });
      nm.style.paddingLeft = 6 + (r.outline_level || 0) * 14 + "px";
      var openInfo = function () { if (window.SFTaskInfo) SFTaskInfo.open(r); };
      uidTd.addEventListener("click", openInfo);
      nm.addEventListener("click", openInfo);
      tr.appendChild(uidTd);
      tr.appendChild(nm);
      tr.appendChild(el("td", { text: r.remaining_days == null ? "" : String(r.remaining_days) }));
      if (r.editable) {
        tr.appendChild(inputCell(r, "factor", { min: "0", max: "5", step: "1", style: "width:48px",
          title: "0 = no Best/Worst uncertainty (use remaining); 1-5 widen the spread" }));
        tr.appendChild(inputCell(r, "bc_days", { min: "0", step: "0.1", style: "width:64px" }));
        tr.appendChild(inputCell(r, "wc_days", { min: "0", step: "0.1", style: "width:64px" }));
        tr.appendChild(focusCell(r));
      } else {
        for (var i = 0; i < 4; i++) tr.appendChild(el("td"));
      }
      if (axis) tr.appendChild(timelineCell(r, axis, grid));
      tbody.appendChild(tr);
    };
    var gb = groupBy();
    if (gb) {
      // group rows under headers by any field (WBS, resources, critical, custom …), like path.js
      groupList(list, gb).forEach(function (g) {
        var bh = el("tr", { class: "sra-branch-head" });
        var btd = el("td", { text: g[0] + "  (" + g[1].length + ")" });
        btd.colSpan = axis ? GRID_COLS + 1 : GRID_COLS;
        bh.appendChild(btd);
        tbody.appendChild(bh);
        g[1].forEach(paintOne);
      });
    } else {
      list.forEach(paintOne);
    }
    if (!list.length) {
      var empty = el("tr");
      empty.appendChild(el("td", { class: "muted", text: "No tasks match the filters." }));
      tbody.appendChild(empty);
    }
    // re-pin the frozen data columns for the new rows (only once the table is in the DOM — the
    // initial render freezes after appending) and record their measured width for fitToProject
    var tbl = tbody.parentNode;
    if (tbl && tbl.isConnected && window.SFGantt && SFGantt.freezeColumns) {
      lastFrozenWidth = SFGantt.freezeColumns(tbl) || lastFrozenWidth;
    }
  }

  function render() {
    var axis = buildAxis(rows);
    var grid = axis ? SFGantt.gridLines(axis) : null;
    var table = el("table", { class: "gantt-grid sra-grid" });
    var thead = el("thead");
    var hr = el("tr");
    ["UID", "Task", "Rem d", "Factor", "BC d", "WC d", "Focus"].forEach(function (h) { hr.appendChild(el("th", { text: h })); });
    if (axis) {
      var th = el("th", { class: "g-head" });
      th.appendChild(SFGantt.buildTierScale(axis, "g-scale", dataDate));
      hr.appendChild(th);
    }
    thead.appendChild(hr);
    // MS-Project per-column checklist filters on the non-editable columns (UID / Task / Rem d)
    var tbody = el("tbody");
    var filterRow = el("tr", { class: "filter-row" });
    ["unique_id", "name", "remaining_days", null, null, null, null].forEach(function (key) {
      var td = el("td");
      var f = null;
      FILTER_COLS.forEach(function (fc) { if (fc.key === key) f = fc; });
      if (f && window.SFChecklist) {
        td.appendChild(SFChecklist.filter({
          values: distinctValues(f.key),
          selected: colFilters[f.key] || null,
          label: "Filter",
          title: "Filter " + f.label,
          onChange: function (sel) { colFilters[f.key] = sel; paintBody(tbody, axis, grid); },
        }));
      }
      filterRow.appendChild(td);
    });
    if (axis) filterRow.appendChild(el("td", { class: "muted" }));
    thead.appendChild(filterRow);
    table.appendChild(thead);
    table.appendChild(tbody);
    host.innerHTML = "";
    host.appendChild(table);
    if (window.SFColResize) SFColResize.attach(table, "ssiGrid"); // MS-Project drag-to-resize columns
    // paintBody locks the data columns (SFGantt.freezeColumns) so they stay visible as the wide
    // timeline scrolls left↔right, and records their measured width for fitToProject
    paintBody(tbody, axis, grid);
  }

  function load() {
    statusEl.textContent = "Loading grid...";
    fetch("/api/sra/grid")
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (res) {
        if (!res.ok) { statusEl.textContent = res.j.error || "Could not load the grid."; return; }
        rows = res.j.rows || [];
        dataDate = res.j.data_date || null;
        pending = {};
        populateGroupCustom();
        render();
        statusEl.textContent = rows.length + " tasks.";
      })
      .catch(function () { statusEl.textContent = "Could not load the grid."; });
  }

  function save() {
    var arr = Object.keys(pending).map(function (k) { return pending[k]; });
    if (!arr.length) { statusEl.textContent = "Nothing to save."; return; }
    statusEl.textContent = "Saving...";
    fetch("/sra/grid", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: "deltas=" + encodeURIComponent(JSON.stringify(arr)),
    })
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (res) {
        if (!res.ok) { statusEl.textContent = res.j.error || "Save failed."; return; }
        statusEl.textContent = "Saved " + res.j.saved + " change(s).";
        load();
      })
      .catch(function () { statusEl.textContent = "Save failed."; });
  }

  // one delegated listener for every editable cell (not thousands of per-input listeners)
  host.addEventListener("change", function (e) {
    var t = e.target;
    if (!t || !t.classList) return;
    var uid = parseInt(t.getAttribute("data-uid"), 10);
    if (isNaN(uid)) return;
    if (t.classList.contains("sra-focus")) mark(uid, "focus", true);
    else if (t.classList.contains("sra-inp")) mark(uid, t.getAttribute("data-key"), t.value);
  });

  // Excel / MS-Project column paste: copy a whole column (or a Factor/BC/WC block) and paste it onto
  // one cell to fill DOWN the column across every task in one go (no per-cell entry). A single value
  // pasted onto one cell falls through to the browser so manual entry still works.
  var COLS = ["factor", "bc_days", "wc_days"]; // left-to-right column order for a multi-column paste
  host.addEventListener("paste", function (e) {
    var t = e.target;
    if (!t || !t.classList || !t.classList.contains("sra-inp")) return;
    var cb = e.clipboardData || window.clipboardData;
    var text = cb ? cb.getData("text") : "";
    if (!text) return;
    var lines = text.replace(/\r\n/g, "\n").replace(/\r/g, "\n").split("\n");
    while (lines.length > 1 && lines[lines.length - 1] === "") lines.pop(); // Excel's trailing newline
    if (lines.length === 1 && lines[0].indexOf("\t") === -1) return; // single value -> manual entry
    e.preventDefault();
    var startCol = COLS.indexOf(t.getAttribute("data-key"));
    if (startCol < 0) startCol = 0;
    var byKey = {};
    COLS.forEach(function (k) {
      byKey[k] = Array.prototype.slice.call(host.querySelectorAll('input.sra-inp[data-key="' + k + '"]'));
    });
    var startRow = byKey[COLS[startCol]].indexOf(t);
    if (startRow < 0) startRow = 0;
    var filled = 0;
    lines.forEach(function (line, r) {
      line.split("\t").forEach(function (val, c) {
        var key = COLS[startCol + c];
        if (!key) return;
        var inp = byKey[key][startRow + r];
        if (!inp) return;
        var v = String(val).trim();
        inp.value = v;
        mark(parseInt(inp.getAttribute("data-uid"), 10), key, v);
        filled++;
      });
    });
    statusEl.textContent = "Pasted " + filled + " value(s) down the column — press Save grid to apply.";
  });

  var saveBtn = document.getElementById("ssiGridSave");
  if (saveBtn) saveBtn.addEventListener("click", save);
  var reloadBtn = document.getElementById("ssiGridReload");
  if (reloadBtn) reloadBtn.addEventListener("click", load);
  if (zoomEl) zoomEl.addEventListener("input", function () { forcedPx = null; if (rows.length) render(); });
  var groupEl = groupSelect();
  if (groupEl) groupEl.addEventListener("change", function () { if (rows.length) render(); });
  // scrolling to the pane's right edge extends the axis (unlimited right scroll, ADR-0187)
  SFGantt.attachEdgeExtend(host, function () { extraRightDays += 60; if (rows.length) render(); });
  var fitBtn = document.getElementById("ssiGridFit");
  if (fitBtn) fitBtn.addEventListener("click", function () { if (rows.length) fitToProject(); });
  // show-completed + dates-on-bars toggles (parity with the Activities Gantt — ADR-0186)
  var showDoneEl = document.getElementById("ssiShowDone");
  if (showDoneEl) showDoneEl.addEventListener("change", function () { if (rows.length) render(); });
  var barDatesEl = document.getElementById("ssiBarDates");
  if (barDatesEl) barDatesEl.addEventListener("change", function () { if (rows.length) render(); });
  // MS-Project Find: jump the grid to a UniqueID, scroll it into view and flash it
  var findEl = document.getElementById("ssiFind");
  if (findEl) {
    var goFind = function () {
      var uid = parseInt(findEl.value, 10);
      var status = document.getElementById("ssiFindStatus");
      if (!uid) return;
      var row = host.querySelector('tr[data-uid="' + uid + '"]');
      if (!row) { if (status) status.textContent = "UID " + uid + " not in view"; return; }
      if (status) status.textContent = "";
      row.scrollIntoView({ block: "center", behavior: "smooth" });
      host.querySelectorAll("tr.row-found").forEach(function (r) { r.classList.remove("row-found"); });
      row.classList.add("row-found");
    };
    findEl.addEventListener("change", goFind);
    findEl.addEventListener("keydown", function (e) { if (e.key === "Enter") { e.preventDefault(); goFind(); } });
  }
  // the Timescale dialog's OK repaints the grid with the new tiers/size/shading
  window.addEventListener("sf-timescale", function () { if (rows.length) render(); });

  load();
})();
