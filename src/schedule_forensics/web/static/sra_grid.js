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

  function pxPerDay() {
    var v = zoomEl ? parseFloat(zoomEl.value) : 1.4;
    return isNaN(v) || v <= 0 ? 1.4 : v;
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
    t0 -= 2 * DAY_MS; t1 += 2 * DAY_MS;
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
    td.appendChild(inp);
    return td;
  }

  function focusCell(r) {
    var td = el("td", { class: "sra-focus-cell" });
    var radio = el("input", { type: "radio", name: "ssiFocus", class: "sra-focus", "data-uid": String(r.unique_id) });
    if (r.is_focus) radio.checked = true;
    td.appendChild(radio);
    return td;
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
      track.appendChild(el("div", { class: "g-ms", title: r.name + " (milestone) " + r.start, style: "left:" + axis.x(s) + "px" }));
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
      var bar = el("div", { class: cls, title: r.name + "  " + r.start + " -> " + r.finish, style: "left:" + left + "px;width:" + width + "px" });
      if (!r.is_summary && (r.complete || r.percent_complete > 0)) {
        bar.appendChild(el("div", { class: "g-done", style: "width:" + (r.complete ? 100 : Math.min(100, r.percent_complete)) + "%" }));
      }
      track.appendChild(bar);
    }
    cell.appendChild(track);
    return cell;
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
    table.appendChild(thead);
    var tbody = el("tbody");
    rows.forEach(function (r) {
      var tr = el("tr");
      if (r.is_critical) tr.className = "crit";
      if (r.is_summary) tr.className = (tr.className + " sum").trim();
      if (r.has_risk) tr.className = (tr.className + " sra-risk").trim();
      tr.appendChild(el("td", { text: String(r.unique_id) }));
      var nm = el("td", { class: "name-cell", text: r.name });
      nm.style.paddingLeft = 6 + (r.outline_level || 0) * 14 + "px";
      tr.appendChild(nm);
      tr.appendChild(el("td", { text: r.remaining_days == null ? "" : String(r.remaining_days) }));
      if (r.editable) {
        tr.appendChild(inputCell(r, "factor", { min: "1", max: "5", step: "1", style: "width:48px" }));
        tr.appendChild(inputCell(r, "bc_days", { min: "0", step: "0.1", style: "width:64px" }));
        tr.appendChild(inputCell(r, "wc_days", { min: "0", step: "0.1", style: "width:64px" }));
        tr.appendChild(focusCell(r));
      } else {
        for (var i = 0; i < 4; i++) tr.appendChild(el("td"));
      }
      if (axis) tr.appendChild(timelineCell(r, axis, grid));
      tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    host.innerHTML = "";
    host.appendChild(table);
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
  if (zoomEl) zoomEl.addEventListener("input", function () { if (rows.length) render(); });

  load();
})();
