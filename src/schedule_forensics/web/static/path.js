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
    { key: "drag_days", label: "Drag (d)", on: false },
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
  // Timeline span + scale state. By default the axis fits the SELECTED tier (the path you picked) and
  // the px auto-scales to fill the page next to the frozen columns; "View entire project" widens the
  // axis to every traced activity; nudging the zoom slider switches to a fixed px (wide → scroll).
  var scopeAll = false; // true = span every path activity, not just the selected tier
  var fitFill = true; // true = auto-scale px so the span fills the page width; the zoom slider clears it
  var lastAxis = null, lastGrid = null, lastOn = null; // header built once; body repaints on filter
  var lastTable = null, lastScaleTh = null; // refs so a tier/zoom reflow rebuilds only the timeline
  var lastFrozenWidth = 0, refitting = false; // measured data-column width → the timeline fills the rest

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
    if (v === null || v === undefined || v === "") return "—";
    var s = String(v);
    // operator: every Gantt date reads MM/DD/YYYY, no time-of-day (fmtMDY returns "" for
    // non-dates so every other value passes through). The underlying data stays ISO.
    return SFGantt.fmtMDY(s) || s;
  }
  // the raw (filterable) value of a column for a row; the "Drives →" column isn't value-filterable
  function rawValue(r, f) {
    if (f.key === "drives") return null;
    return f.custom ? r.custom && r.custom[f.label] : r[f.key];
  }
  // Numeric/date-aware comparator for the checklist filter value lists: MM/DD/YYYY dates sort
  // chronologically, raw ISO dates lexically, numbers numerically, everything else lexically.
  function compareValues(a, b) {
    var mdy = /^(\d\d)\/(\d\d)\/(\d{4})$/;
    var ma = mdy.exec(a), mb = mdy.exec(b);
    if (ma && mb) {
      var ka = ma[3] + ma[1] + ma[2], kb = mb[3] + mb[1] + mb[2]; // yyyymmdd
      return ka < kb ? -1 : ka > kb ? 1 : 0;
    }
    var iso = /^\d{4}-\d\d-\d\d/;
    if (iso.test(a) && iso.test(b)) return a < b ? -1 : a > b ? 1 : 0;
    var na = parseFloat(a), nb = parseFloat(b);
    var bothNum = !isNaN(na) && !isNaN(nb) && /^-?\d/.test(a) && /^-?\d/.test(b);
    return bothNum ? na - nb : a < b ? -1 : a > b ? 1 : 0;
  }
  // distinct, numeric/date-aware sorted formatted values of a column — the checklist contents
  function distinctValues(f) {
    var seen = {};
    (data ? data.rows : []).forEach(function (r) { seen[fmt(rawValue(r, f))] = true; });
    return Object.keys(seen).sort(compareValues);
  }
  function rowMatchesColumns(r) {
    return (lastOn || []).every(function (f) {
      var sel = colFilters[f.key];
      if (!sel || f.key === "drives") return true; // unfiltered
      return sel.has(fmt(rawValue(r, f))); // an empty Set hides every row
    });
  }

  // The width left for the timeline once the (measured) data columns are subtracted — so the bars
  // fill the page right up against the frozen columns. lastFrozenWidth is measured after each paint;
  // 360 is the first-paint estimate before the columns are laid out.
  function availWidth() {
    var vw = view ? view.clientWidth : 960;
    return Math.max(240, vw - (lastFrozenWidth || 360) - 18);
  }

  // The rows that DEFINE the timeline span: the selected tier when one is picked (so choosing a path
  // fits the axis to it and the bars fill the page next to the columns) — else every traced activity.
  // "View entire project" (scopeAll) forces the full set.
  function axisRows() {
    if (!data) return [];
    if (!scopeAll && pathTierSel) {
      var sub = data.rows.filter(function (r) { return pathTierSel.has(r.tier); });
      if (sub.length) return sub; // fall through to all rows if the tier has nothing dated
    }
    return data.rows;
  }

  // Build the px-per-day axis from axisRows(): a small LEFT margin keeps the first bar close to the
  // columns; a larger RIGHT margin keeps the gold data-date line off the right border. In fill mode
  // the px auto-scales so the whole span fits the page; the zoom slider switches to a fixed px (wide
  // → horizontal scroll, with the columns frozen).
  function buildAxis() {
    var t0 = null, t1 = null;
    function scan(list) {
      list.forEach(function (r) {
        if (r.start) t0 = Math.min(t0 === null ? Infinity : t0, Date.parse(r.start));
        if (r.finish) t1 = Math.max(t1 === null ? -Infinity : t1, Date.parse(r.finish));
      });
    }
    scan(axisRows());
    if (t0 === null || t1 === null) scan(data.rows); // a tier with no dated rows → fall back to all
    if (data.data_date) t1 = Math.max(t1 === null ? -Infinity : t1, Date.parse(data.data_date));
    if (t0 === null || t1 === null) return null;
    var span = Math.max(1, (t1 - t0) / DAY_MS);
    t0 -= 2 * DAY_MS; // bars sit close to the data columns
    t1 += Math.max(4, Math.round(span * 0.04)) * DAY_MS; // breathing room past the data-date line
    var spanDays = Math.max(1, (t1 - t0) / DAY_MS);
    var slider = Number($("pathZoom").value);
    var px = fitFill ? Math.max(0.02, availWidth() / spanDays) : (slider > 0 ? slider : 8);
    var width = Math.max(120, Math.round(spanDays * px));
    return { t0: t0, t1: t1, width: width, x: function (ms) { return Math.round(((ms - t0) / DAY_MS) * px); } };
  }

  // "View entire project": widen the axis to every path activity and auto-scale it to fit the page.
  function fitToProject() {
    scopeAll = true;
    fitFill = true;
    reflow();
  }

  // Once the data columns are laid out, refit the fill width to their REAL measured width so the
  // timeline uses the exact remaining page space (operator: "utilize the entire page space"). Runs
  // at most once per render via the refitting guard.
  function refitToColumns(assumed) {
    if (fitFill && !refitting && Math.abs(lastFrozenWidth - assumed) > 6) {
      refitting = true;
      reflow();
      refitting = false;
    }
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
      "&tertiary=" + encodeURIComponent($("pathTer").value || "20") + optionParams() +
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
  // render() builds the whole table (column titles + the MS-Project per-column filter row + the date
  // axis) and stores refs; reflow() rebuilds ONLY the timeline (axis scale + bars) in place when the
  // span changes (tier / zoom / View entire project), leaving the open dropdowns alone; paintRows()
  // repopulates only the body for a row filter. The axis fits axisRows() (the selected tier, else
  // every activity) so the chosen path fills the page next to the frozen columns.
  function render() {
    if (window.SFChecklist) SFChecklist.close();
    view.textContent = "";
    if (!data) { $("pathStatus").textContent = ""; return; }
    var on = FIELDS.filter(function (f) { return f.on; });
    lastOn = on;
    var assumed = lastFrozenWidth;
    var axis = buildAxis();
    if (!axis) { paintStatus([]); return; }
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
    lastScaleTh = thTime;

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
    lastTable = table;
    if (window.SFColResize) SFColResize.attach(table, "path"); // MS-Project drag-to-resize columns
    paintRows();
    refitToColumns(assumed);
  }

  // Rebuild only the timeline scale + bars (no header teardown, no SFChecklist.close) so selecting a
  // tier or zooming re-fits the span without closing the tier / filter dropdowns mid-interaction.
  function reflow() {
    if (!data || !lastTable || !lastScaleTh) { render(); return; }
    var assumed = lastFrozenWidth;
    var axis = buildAxis();
    if (!axis) { paintStatus([]); return; }
    lastAxis = axis;
    lastGrid = SFGantt.gridLines(axis);
    lastScaleTh.textContent = "";
    lastScaleTh.appendChild(SFGantt.buildTierScale(axis, "path-scale", data.data_date));
    paintRows();
    refitToColumns(assumed);
  }

  function paintRows() {
    var tbody = $("pathBody");
    if (!tbody || !lastAxis) return;
    var axis = lastAxis, gridLns = lastGrid, on = lastOn, x = axis.x, width = axis.width;
    var rows = visibleRows();
    paintStatus(rows);
    tbody.innerHTML = "";
    // SSI Output modes (operator 2026-07-08): Waterfall = flat chronological (default);
    // With Summaries = grouped under top-level WBS headers; Separate parallel paths = the
    // server's branch decomposition of the driving path, one header per parallel branch.
    var output = radioVal("pathOutput", "waterfall");
    var groups = null;
    if (output === "parallel" && data.parallel_paths && data.parallel_paths.length) {
      var byUid = {};
      rows.forEach(function (r) { byUid[r.unique_id] = r; });
      var used = {};
      groups = [];
      data.parallel_paths.forEach(function (pp) {
        var members = pp.uids.map(function (u) { return byUid[u]; }).filter(Boolean);
        members.forEach(function (r) { used[r.unique_id] = 1; });
        if (members.length) groups.push([pp.label, members]);
      });
      var rest = rows.filter(function (r) { return !used[r.unique_id]; });
      if (rest.length) groups.push(["Off-path (secondary / tertiary / beyond)", rest]);
    } else if (output === "summaries") {
      var byWbs = {};
      var order = [];
      rows.forEach(function (r) {
        var g = (r.wbs || "").split(".")[0] || "(no WBS)";
        if (!byWbs[g]) { byWbs[g] = []; order.push(g); }
        byWbs[g].push(r);
      });
      groups = order.map(function (g) { return ["WBS " + g, byWbs[g]]; });
    }
    var paintOne = function (r) {
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
        // fmt renders booleans as yes/—, blanks as —, and dates as MM/DD/YYYY (operator format)
        var text = fmt(f.custom ? (r.custom && r.custom[f.label]) : r[f.key]);
        // the Name column wraps to its FULL text (no truncation); other columns stay nowrap
        var attrs = f.key === "name" ? { class: "pv-name", text: text } : { text: text };
        if (f.key === "drag_days" && r.drag_days != null) attrs = { class: "pv-drag", text: text };
        tr.appendChild(el("td", attrs));
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
              (SFGantt.fmtMDY(r.start) || r.start) + " → " + (SFGantt.fmtMDY(r.finish) || r.finish) +
              ", " + r.percent_complete + "%",
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
    };
    if (groups) {
      groups.forEach(function (g) {
        var bh = el("tr", { class: "path-branch-head" });
        var btd = el("td", { text: g[0] });
        btd.colSpan = on.length + 1;
        bh.appendChild(btd);
        tbody.appendChild(bh);
        g[1].forEach(paintOne);
      });
    } else {
      rows.forEach(paintOne);
    }
    if (!rows.length) {
      tbody.appendChild(
        el("tr", {}, [el("td", { class: "muted", text: "No activities match the filters." })])
      );
    }
    // pin the data columns to the left so they stay put as the wide timeline scrolls; the returned
    // total width drives the fill-to-page refit in render()/reflow()
    if (window.SFGantt && SFGantt.freezeColumns && lastTable) {
      lastFrozenWidth = SFGantt.freezeColumns(lastTable) || lastFrozenWidth;
    }
  }

  // --- SSI Directional Path options (operator 2026-07-08) ----------------------------
  var dragOn = false; // toggled by the Run Drag Analysis button; re-traces with drag=1
  function radioVal(name, fallback) {
    var el = document.querySelector('input[name=' + name + ']:checked');
    return el ? el.value : fallback;
  }
  function optionParams() {
    return "&direction=" + encodeURIComponent(radioVal("pathDir", "predecessors")) +
      "&range_mode=" + encodeURIComponent(radioVal("pathRange", "all")) +
      "&range_days=" + encodeURIComponent($("pathRangeDays").value || "0") +
      "&ignore_constraints=" + ($("pathIgnoreConstraints").checked ? "1" : "0") +
      "&ignore_leveling=" + ($("pathIgnoreLeveling").checked ? "1" : "0") +
      "&drag=" + (dragOn ? "1" : "0");
  }

  // --- data loading -----------------------------------------------------------------
  function trace() {
    var sched = $("pathSchedule").value;
    var target = $("pathTarget").value;
    if (!target) { $("pathStatus").textContent = "Enter a target UniqueID, then Trace."; return; }
    var url = "/api/driving/" + encodeURIComponent(sched) +
      "?target=" + encodeURIComponent(target) +
      "&secondary=" + encodeURIComponent($("pathSec").value || "10") +
      "&tertiary=" + encodeURIComponent($("pathTer").value || "20") + optionParams();
    $("pathStatus").textContent = "Tracing…";
    fetch(url)
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (res) {
        if (!res.ok) { $("pathStatus").textContent = res.j.error || "Trace failed."; data = null; view.textContent = ""; return; }
        data = res.j;
        syncCustomColumns();
        renderToggles();
        updateExportLinks();
        scopeAll = false; // a fresh trace fits the selected tier, not the whole project
        fitFill = true; // and auto-scales to the page until the zoom slider is nudged
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
      // selecting a tier IS "selecting a path": re-fit the timeline to it so its bars fill the page
      onChange: function (s) { pathTierSel = s; scopeAll = false; fitFill = true; reflow(); },
    }));
  }
  $("pathRun").addEventListener("click", trace);
  $("pathDrag").addEventListener("click", function () {
    dragOn = true;
    FIELDS.forEach(function (f) { if (f.key === "drag_days") f.on = true; });
    trace();
  });
  // option changes re-trace immediately when a trace is already on screen
  ["pathRangeDays", "pathIgnoreConstraints", "pathIgnoreLeveling"].forEach(function (id) {
    var oel = $(id);
    if (oel) oel.addEventListener("change", function () { if (data) trace(); });
  });
  ["pathDir", "pathRange", "pathOutput"].forEach(function (name) {
    document.querySelectorAll("input[name=" + name + "]").forEach(function (rb) {
      rb.addEventListener("change", function () {
        if (name === "pathOutput") { if (data) paintRows(); return; }
        if (data) trace();
      });
    });
  });
  $("pathHideDone").addEventListener("change", paintRows);
  // debounce the free-text filter: each keystroke otherwise rebuilds the whole tbody and rewrites
  // ~10k inline freeze styles on a ~1700-row grid, janking while typing (audit M7)
  var pathFilterTimer;
  $("pathFilter").addEventListener("input", function () {
    clearTimeout(pathFilterTimer);
    pathFilterTimer = setTimeout(paintRows, 140);
  });
  $("pathZoom").addEventListener("input", function () { fitFill = false; reflow(); });
  var pathFit = $("pathFit");
  if (pathFit) pathFit.addEventListener("click", fitToProject);
  if ($("pathTarget").value) trace(); // a session-wide target traces immediately
})();
