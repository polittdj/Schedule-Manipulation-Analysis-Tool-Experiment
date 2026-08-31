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
    // Dur is ON by default (operator 2026-08-20: the default grid carries UID, duration,
    // % complete, start and finish), seated before Start to read like the MS Project table.
    { key: "duration_days", label: "Dur (d)", on: true },
    { key: "start", label: "Start", on: true },
    { key: "finish", label: "Finish", on: true },
    { key: "baseline_finish", label: "Baseline finish", on: false },
    { key: "total_float_days", label: "TF (d)", on: false },
    { key: "percent_complete", label: "%", on: true },
    { key: "date_driven", label: "Date-driven", on: false },
    { key: "actual_start_driven", label: "Actual-start-driven", on: false },
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
  var pendingWholeFit = false; // ADR-0441: a fresh whole-schedule payload opens FITTED when huge
  var lastAxis = null, lastGrid = null, lastOn = null; // header built once; body repaints on filter
  var lastTable = null, lastScaleTh = null; // refs so a tier/zoom reflow rebuilds only the timeline
  var lastFrozenWidth = 0, refitting = false; // measured data-column width → the timeline fills the rest
  var extraRightDays = 0; // unlimited right scroll (ADR-0187): grows at the pane's right edge
  // Click-to-highlight (operator): clicking a task's row (any field) or its bar selects it — the whole
  // row of fields AND its Gantt bar highlight; clicking another task moves the highlight; clicking off
  // clears it. State-driven (a module var re-applied on every repaint) so it survives a filter, zoom,
  // tier change, or timescale event that rebuilds the tbody. Kept as a STRING for a stable compare.
  var selectedUid = null;
  // Session HIGHLIGHT mode (feature #10): the /api/driving response carries highlight_uids — the
  // session filter's matches for THIS file — when the operator chose "mark, don't drop". Painted
  // in paintOne (so it survives every repaint) as pv-match/pv-bar-match, composing with the
  // transient click selection above (a row can be both).
  var matchSet = null; // null = no highlight; else an object used as a Set of String(uid)

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
    // breathing room past the data-date line + the edge-extend growth (ADR-0187)
    t1 += (Math.max(4, Math.round(span * 0.04)) + extraRightDays) * DAY_MS;
    var spanDays = Math.max(1, (t1 - t0) / DAY_MS);
    var slider = Number($("pathZoom").value);
    // ADR-0441: "opens zoomed" (with the data date seated an inch in, ADR-0438) is right for a
    // season-scale schedule and useless for a decade-scale one — at the default 8 px/day a
    // 4,500-day span is a ~36,000px track (~38 pages) whose visible slice is almost always
    // empty. A whole-schedule view whose zoomed track would exceed SIXTEEN pages opens fitted
    // instead; anything shorter keeps the zoomed-and-seated opening (a ~2.5-year schedule is
    // ~7.5 pages — measured operator-approved territory, ADR-0438), and the slider and Fit
    // rezoom freely either way.
    if (pendingWholeFit) {
      pendingWholeFit = false;
      if (spanDays * (slider > 0 ? slider : 8) > 16 * availWidth()) fitFill = true;
    }
    // the Timescale dialog's Size % scales the timeline in BOTH modes: fitFill establishes the
    // page-fill baseline, then Size multiplies it (so Size works even when fitted to the page).
    var size = window.SFTimescale ? window.SFTimescale.sizeFactor() : 1;
    if (!(size > 0)) size = 1;
    var px = (fitFill ? Math.max(0.02, availWidth() / spanDays) : slider > 0 ? slider : 8) * size;
    var width = Math.max(120, Math.round(spanDays * px));
    return { t0: t0, t1: t1, width: width, x: function (ms) { return Math.round(((ms - t0) / DAY_MS) * px); } };
  }

  // "View entire project": widen the axis to every path activity and auto-scale it to fit the page.
  function fitToProject() {
    scopeAll = true;
    fitFill = true;
    reflow();
  }

  // Seat the gold data-date line ~1 inch right of the frozen data columns (operator
  // 2026-08-20; ONE_INCH ≈ 96 CSS px, the same seat /analysis uses). Runs once per payload
  // (seatPending), after the load's paint SETTLES — column widths keep moving through the
  // first layout/font passes, so the seat is a LIVE-geometry delta (where the line is now vs
  // where it should sit), deferred a double animation frame and re-checked once when the
  // fonts finish loading. Only a pane that actually overflows moves (Math.max clamps to 0).
  var seatPending = false;
  var seatEpoch = 0; // bumps per payload so a stale deferred seat never fires late
  var ONE_INCH_PX = 96;
  function seatDataDate() {
    if (!data || !data.data_date) return;
    var now = view.querySelector(".path-track .pv-now");
    if (!now) return;
    var frozen = 0;
    var ths = view.querySelectorAll("thead tr:first-child th");
    for (var i = 0; i < ths.length - 1; i++) frozen += ths[i].offsetWidth;
    var delta = (now.getBoundingClientRect().left - view.getBoundingClientRect().left) -
      (frozen + ONE_INCH_PX);
    view.scrollLeft = Math.max(0, view.scrollLeft + delta);
  }
  function maybeSeat() {
    if (!seatPending || refitting) return;
    seatPending = false;
    seatEpoch += 1;
    var epoch = seatEpoch;
    requestAnimationFrame(function () {
      requestAnimationFrame(function () {
        if (epoch !== seatEpoch) return;
        seatDataDate();
        // fonts settling after first paint re-widen the columns; correct once more
        if (document.fonts && document.fonts.status !== "loaded") {
          document.fonts.ready.then(function () {
            if (epoch === seatEpoch) seatDataDate();
          });
        }
      });
    });
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
    if (data.whole_schedule) {
      // the path export routes REQUIRE a target — a whole-schedule export link would 422.
      // Hide the bar honestly; it returns the moment a trace exists.
      $("pathExport").style.display = "none";
      return;
    }
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
    // the whole-schedule default (operator 2026-08-20): no target yet — say so, with the live
    // filtered count, and point at the UID click that starts a trace
    if (data && data.whole_schedule) {
      $("pathStatus").textContent = rows.length + " of " + data.rows.length +
        " activities — complete schedule (no target selected)" +
        (data.data_date ? " — data date " + data.data_date : "") +
        " — click a row's UID to trace the driving paths to it.";
      return;
    }
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
    maybeSeat(); // one-shot data-date seat, after the load's final paint
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
    // ADR-0441: SFColResize pinned this th's inline width at ATTACH time (render only). Under
    // table-layout:fixed a reflow'd scale otherwise floats inside the stale column — after Fit
    // the operator's 12-year view kept a 40,104px column around a 969px track, with the pane
    // still scrolled into the dead space. The column must follow the axis on every reflow.
    lastScaleTh.style.width = axis.width + "px";
    lastScaleTh.style.minWidth = axis.width + "px";
    lastScaleTh.style.maxWidth = axis.width + "px";
    paintRows();
    refitToColumns(assumed);
    maybeSeat(); // one-shot data-date seat, after the load's final paint
  }

  // MS-Project-style logic-link connectors (operator 2026-07-08): an SVG overlay per
  // timeline row pair — elbow from the predecessor bar's finish down to the successor's start.
  function drawLinkLines(tbody, rows, x) {
    var rowTop = {};
    var trs = tbody.querySelectorAll("tr");
    var idx = 0;
    trs.forEach(function (tr) {
      if (tr.classList.contains("path-branch-head")) return;
      var r = rows[idx];
      // rows and non-header trs are painted in the same order (paintOne appends 1:1)
      if (r) rowTop[r.unique_id] = tr;
      idx += 1;
    });
    rows.forEach(function (r) {
      (r.drives || []).forEach(function (lk) {
        var fromTr = rowTop[r.unique_id];
        var toTr = rowTop[lk.uid];
        var toRow = null;
        for (var i = 0; i < rows.length; i++) if (rows[i].unique_id === lk.uid) toRow = rows[i];
        if (!fromTr || !toTr || !toRow || !r.finish || !toRow.start) return;
        var track = toTr.querySelector(".path-track");
        var fromTrack = fromTr.querySelector(".path-track");
        if (!track || !fromTrack) return;
        var x1 = x(Date.parse(r.finish));
        var x2 = x(Date.parse(toRow.start));
        var dy = toTr.rowIndex - fromTr.rowIndex; // vertical span in rows
        var h = 15 * dy; // approximate row pitch (density pass: ~15px)
        var svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
        svg.setAttribute("class", "pv-link");
        svg.style.cssText = "position:absolute;left:0;top:" + (-h) + "px;width:100%;height:" +
          Math.abs(h) + "px;overflow:visible;pointer-events:none";
        var path = document.createElementNS("http://www.w3.org/2000/svg", "path");
        var midY = h > 0 ? Math.abs(h) : 0;
        path.setAttribute("d", "M" + x1 + " " + (h > 0 ? 7 : Math.abs(h) + 7) +
          " L" + x1 + " " + (h > 0 ? midY + 3 : 3) + " L" + x2 + " " + (h > 0 ? midY + 3 : 3));
        path.setAttribute("fill", "none");
        path.setAttribute("stroke", lk.on_path ? "rgba(220,60,80,.75)" : "rgba(120,150,200,.55)");
        path.setAttribute("stroke-width", "1");
        path.setAttribute("marker-end", "");
        svg.appendChild(path);
        track.appendChild(svg);
      });
    });
  }

  // ── Windowed row painting (S5, ADR-0442) ─────────────────────────────────────────────
  // One-shot paintRows at the operator's row scale (2,280 rows) measured 1,417 ms post-ADR-0441
  // — every row pays its own gridline divs, non-working shading and freeze styles. A flat grid
  // at or above WINDOW_MIN_ROWS materializes only the viewport slice ± WINDOW_OVERSCAN rows,
  // with spacer rows keeping the scrollbar honest; a vertical scroll re-aims the window. The
  // whole-schedule DEFAULT view is exactly the flat shape, so the pathological case gets the
  // fix while every other posture keeps the full paint: grouped/summaries/parallel output,
  // "Show links" (the connector overlay joins arbitrary row pairs), Find (marks every match),
  // and print (the A5 contract prints scroll panes in full) all force a complete tbody.
  // WINDOW_MIN_ROWS anchors between the largest committed full-paint suite (TP5, 121 rows —
  // 3.3x headroom below) and the operator scale (2,301 — 5.8x above), per the ADR-0441
  // threshold rule: the neighbour suites' green is the boundary-setter.
  var WINDOW_MIN_ROWS = 400;
  var WINDOW_OVERSCAN = 40; // rows materialized beyond each viewport edge
  var winState = null; // {start, end, total} while a windowed paint is on screen, else null
  var winRowH = 18; // measured row pitch (Name wrapping makes rows uneven; refined per paint)
  var windowFullOnce = false; // Find / beforeprint force the NEXT paint to be full
  function vSpacer(cols, h) {
    var td = el("td", { style: "height:" + Math.max(0, Math.round(h)) + "px;padding:0;border:0" });
    td.colSpan = cols;
    return el("tr", { class: "pv-vspacer", "aria-hidden": "true" }, [td]);
  }

  function paintRows() {
    var tbody = $("pathBody");
    if (!tbody || !lastAxis) return;
    var axis = lastAxis, gridLns = lastGrid, on = lastOn, x = axis.x, width = axis.width;
    var rows = visibleRows();
    paintStatus(rows);
    // Capture the pane's vertical position BEFORE the clear: emptying the tbody collapses the
    // content height and the browser clamps scrollTop to 0, so a slice computed after the
    // clear would always window the top rows — and the user's position died with every
    // repaint. Restored after painting (S5, ADR-0442).
    var keepScrollTop = view.scrollTop;
    tbody.innerHTML = "";
    // SSI Output modes (operator 2026-07-08): Waterfall = flat chronological (default);
    // With Summaries = grouped under top-level WBS headers; Separate parallel paths = the
    // server's branch decomposition of the driving path, one header per parallel branch.
    var output = radioVal("pathOutput", "waterfall");
    var groups = null;
    var gb = $("pathGroupBy") ? $("pathGroupBy").value : "";
    if (gb) {
      var byVal = {};
      var orderG = [];
      rows.forEach(function (r) {
        var k = groupKeyOf(r, gb);
        if (!byVal[k]) { byVal[k] = []; orderG.push(k); }
        byVal[k].push(r);
      });
      orderG.sort();
      groups = orderG.map(function (k) { return [k, byVal[k]]; });
    } else if (output === "parallel" && data.parallel_paths && data.parallel_paths.length) {
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
    var barDates = $("pathBarDates") && $("pathBarDates").checked;
    var LABEL_W = 64; // "MM/DD/YYYY" width estimate at the 9px label font (matches app.js)
    function barLabel(track, anchor, side, iso) {
      var lx = side === "s" ? anchor - LABEL_W : anchor;
      lx = Math.max(0, Math.min(width - LABEL_W, lx));
      track.appendChild(el("div", {
        class: "g-barlabel g-barlabel-" + side,
        style: "left:" + lx + "px;width:" + LABEL_W + "px",
        text: SFGantt.fmtMDY(iso),
      }));
    }
    var paintOne = function (r) {
      // re-apply the click-to-highlight selection on every repaint (survives filter/zoom/tier changes)
      var selected = selectedUid !== null && String(r.unique_id) === selectedUid;
      var matched = matchSet !== null && matchSet[String(r.unique_id)] === 1;
      var tr = el("tr", { class: (r.complete ? "done" : "") + (selected ? " pv-selected" : "") +
        (matched ? " pv-match" : "") });
      tr.setAttribute("data-uid", r.unique_id); // Find-a-UID jump + Task Information join
      // On THIS grid a single click highlights the task (operator's click-to-highlight — the row of
      // fields + its bar); the MS-Project Task Information dialog (shared, ADR-0186) moves to a
      // DOUBLE click so its full-screen overlay doesn't cover the very highlight the single click
      // creates (and doesn't block clicking the next task). The checklist dropdowns stopPropagation.
      tr.addEventListener("dblclick", function () {
        if (window.SFTaskInfo) SFTaskInfo.openFrom($("pathSchedule").value, r.unique_id);
      });
      on.forEach(function (f) {
        if (f.key === "unique_id") {
          // the UID cell is the retarget affordance (operator 2026-08-20): clicking it sets
          // the Target UID and re-traces the driving paths to THIS activity. A real element +
          // delegated listener (CSP: no inline handlers); Enter works via the keydown hook.
          var tdU = el("td");
          tdU.appendChild(el("span", {
            class: "pv-uid", role: "link", tabindex: "0",
            title: "Trace the driving paths to UID " + r.unique_id,
            text: fmt(r.unique_id),
          }));
          tr.appendChild(tdU);
          return;
        }
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
      // whole-schedule rows carry no tier/slack — the tooltip must not read "slack null d"
      var slackTip = r.driving_slack_days === null || r.driving_slack_days === undefined
        ? "" : " — slack " + r.driving_slack_days + "d";
      if (r.start && r.finish) {
        if (r.is_milestone) {
          track.appendChild(el("div", {
            class: "g-ms tier-" + r.tier + (selected ? " pv-bar-selected" : "") +
              (matched ? " pv-bar-match" : ""),
            style: "left:" + x(Date.parse(r.finish)) + "px",
            title: r.name + " (milestone)" + slackTip,
          }));
          // MS-Project "dates on bars": a milestone shows its finish beside the diamond
          if (barDates && r.finish) barLabel(track, x(Date.parse(r.finish)) + 7, "f", r.finish);
        } else {
          var left = x(Date.parse(r.start));
          var w = Math.max(2, x(Date.parse(r.finish)) - left);
          var bar = el("div", {
            class: "gantt-bar tier-" + r.tier + (r.complete ? " done" : "") +
              (selected ? " pv-bar-selected" : "") + (matched ? " pv-bar-match" : ""),
            style: "left:" + left + "px;width:" + w + "px",
            title: r.name + (r.tier ? " — " + r.tier : "") + slackTip + " — " +
              (SFGantt.fmtMDY(r.start) || r.start) + " → " + (SFGantt.fmtMDY(r.finish) || r.finish) +
              ", " + r.percent_complete + "%",
          });
          if (!r.complete && r.percent_complete > 0 && r.percent_complete < 100) {
            bar.appendChild(el("div", { class: "g-done", style: "width:" + r.percent_complete + "%" }));
          }
          track.appendChild(bar);
          // MS-Project "dates on bars": start left of the bar, finish right of it
          if (barDates) {
            barLabel(track, left - 3, "s", r.start);
            barLabel(track, left + w + 3, "f", r.finish);
          }
        }
      }
      cell.appendChild(track);
      SFGantt.paintNonwork(cell, lastAxis); // continuous weekend/holiday shading over the full row
      tr.appendChild(cell);
      tbody.appendChild(tr);
    };
    var wantWindow = !groups && !windowFullOnce && rows.length >= WINDOW_MIN_ROWS &&
      !($("pathShowLinks") && $("pathShowLinks").checked);
    windowFullOnce = false;
    winState = null;
    if (groups) {
      groups.forEach(function (g) {
        var bh = el("tr", { class: "path-branch-head" });
        var btd = el("td", { text: g[0] });
        btd.colSpan = on.length + 1;
        bh.appendChild(btd);
        tbody.appendChild(bh);
        g[1].forEach(paintOne);
      });
    } else if (wantWindow) {
      var rowH = winRowH > 0 ? winRowH : 18;
      var headH = tbody.offsetTop || 0; // the sticky thead's height in content coordinates
      var visTop = Math.max(0, keepScrollTop - headH);
      var wStart = Math.max(0, Math.floor(visTop / rowH) - WINDOW_OVERSCAN);
      var wCount = Math.ceil((view.clientHeight || 600) / rowH) + 2 * WINDOW_OVERSCAN;
      var wEnd = Math.min(rows.length, wStart + wCount);
      if (wStart > 0) tbody.appendChild(vSpacer(on.length + 1, wStart * rowH));
      for (var wi = wStart; wi < wEnd; wi++) paintOne(rows[wi]);
      if (wEnd < rows.length) tbody.appendChild(vSpacer(on.length + 1, (rows.length - wEnd) * rowH));
      winState = { start: wStart, end: wEnd, total: rows.length };
      // Refine the pitch estimate from what actually painted, then re-true the SPACERS to it
      // immediately: spacers sized from a stale estimate misreport the grid's extent, so a
      // jump-to-bottom undershoots the tail. Adjusting the top spacer shifts the content under
      // the viewport, so the pane position is compensated by the same delta.
      var winTrs = tbody.querySelectorAll("tr[data-uid]");
      if (winTrs.length > 1) {
        var wLast = winTrs[winTrs.length - 1];
        var wSpan = wLast.offsetTop + wLast.offsetHeight - winTrs[0].offsetTop;
        if (wSpan > 0) {
          winRowH = wSpan / winTrs.length;
          var sps = tbody.querySelectorAll("tr.pv-vspacer td");
          if (wStart > 0 && sps.length) {
            var oldTopH = parseFloat(sps[0].style.height) || 0;
            var newTopH = Math.round(wStart * winRowH);
            if (Math.abs(newTopH - oldTopH) > 2) {
              sps[0].style.height = newTopH + "px";
              keepScrollTop += newTopH - oldTopH;
            }
          }
          if (wEnd < rows.length && sps.length) {
            var spBot = sps[sps.length - 1];
            if (wStart === 0 || sps.length > 1) {
              spBot.style.height = Math.round((rows.length - wEnd) * winRowH) + "px";
            }
          }
        }
      }
    } else {
      rows.forEach(paintOne);
    }
    if ($("pathShowLinks") && $("pathShowLinks").checked) drawLinkLines(tbody, rows, x);
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
    // put the pane back where the user had it (the clear clamped it — see keepScrollTop above)
    if (view.scrollTop !== keepScrollTop) view.scrollTop = keepScrollTop;
  }

  // --- Group by ANY field (operator 2026-07-08, e.g. a custom CA-WBS code) -----------
  function populateGroupBy() {
    var sel = $("pathGroupBy");
    if (!sel) return;
    var keep = sel.value;
    // Build options via el() so every label goes through textContent / a real attribute value —
    // a field label or custom-field Alias is attacker-controlled free text from an opposing-party
    // schedule (MSPDI <Alias>), and string-concatenating it into innerHTML was a stored DOM-XSS
    // (Law 1: it would run as first-party code in the CUI tool). el() never treats data as HTML.
    sel.textContent = "";
    sel.appendChild(el("option", { value: "", text: "(none)" }));
    FIELDS.forEach(function (f) {
      if (f.key === "drives" || f.key === "name") return;
      sel.appendChild(el("option", { value: f.key, text: f.label }));
    });
    ((data && data.custom_field_labels) || []).forEach(function (lb) {
      sel.appendChild(el("option", { value: "custom:" + lb, text: lb + " (custom)" }));
    });
    sel.value = keep;
  }
  function groupKeyOf(r, key) {
    if (key.indexOf("custom:") === 0) {
      var lb = key.slice(7);
      return (r.custom && r.custom[lb]) || "(blank)";
    }
    var v = r[key];
    return v === null || v === undefined || v === "" ? "(blank)" : String(v);
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
  // Shared /api/driving success path: store the payload, sync the column/group machinery,
  // and render under the mode's axis posture. A trace fits the selected tier to the page
  // (the SSI workflow); the whole-schedule default opens at the zoom-slider px so the data
  // date can be SEATED ~1 inch right of the frozen columns (operator 2026-08-20) instead of
  // compressing years of history into the pane.
  function applyPayload(j, posture) {
    data = j;
    // session HIGHLIGHT mode: mark the filter's matches on this grid (null = not highlighting)
    matchSet = null;
    if (data.highlight_uids && data.highlight_uids.length !== undefined) {
      matchSet = {};
      for (var mi = 0; mi < data.highlight_uids.length; mi++) matchSet[String(data.highlight_uids[mi])] = 1;
    }
    syncCustomColumns();
    populateGroupBy();
    renderToggles();
    updateExportLinks();
    scopeAll = posture === "whole"; // the default view spans every activity by definition
    fitFill = posture !== "whole"; // a fresh trace auto-scales; the whole view opens zoomed
    pendingWholeFit = posture === "whole"; // …unless the span dwarfs the page (ADR-0441)
    seatPending = true; // seat the data date after the (re)paint settles
    render();
  }
  function fetchDriving(url, failText) {
    fetch(url)
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (res) {
        if (!res.ok) { $("pathStatus").textContent = res.j.error || failText; data = null; view.textContent = ""; return; }
        applyPayload(res.j, res.j.whole_schedule ? "whole" : "trace");
      })
      .catch(function () { $("pathStatus").textContent = failText; });
  }
  function trace() {
    var sched = $("pathSchedule").value;
    var target = $("pathTarget").value;
    // no target = the complete schedule (operator 2026-08-20) — the page's default view
    if (!target) { wholeSchedule(); return; }
    var url = "/api/driving/" + encodeURIComponent(sched) +
      "?target=" + encodeURIComponent(target) +
      "&secondary=" + encodeURIComponent($("pathSec").value || "10") +
      "&tertiary=" + encodeURIComponent($("pathTer").value || "20") + optionParams();
    $("pathStatus").textContent = "Tracing…";
    fetchDriving(url, "Trace failed.");
  }
  function wholeSchedule() {
    var sched = $("pathSchedule").value;
    if (!sched) return;
    $("pathStatus").textContent = "Loading the complete schedule…";
    fetchDriving("/api/driving/" + encodeURIComponent(sched), "Load failed.");
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
  // Click-to-highlight: re-skin the currently-selected row + its bar without a full repaint. A full
  // paintRows() also re-applies the classes (paintOne reads selectedUid), so selection survives every
  // rebuild; this just makes the immediate click feel instant.
  function reskinSelection() {
    var prev = view.querySelectorAll(".pv-selected, .pv-bar-selected");
    for (var i = 0; i < prev.length; i++) prev[i].classList.remove("pv-selected", "pv-bar-selected");
    if (selectedUid === null) return;
    var tr = view.querySelector('tr[data-uid="' + selectedUid + '"]');
    if (!tr) return;
    tr.classList.add("pv-selected");
    var bar = tr.querySelector(".gantt-bar, .g-ms");
    if (bar) bar.classList.add("pv-bar-selected");
  }
  // one document-level listener: a click on a task row (any field cell, the track, or the bar — all
  // live inside its <tr data-uid>) selects that task; a click ANYWHERE else — empty pane, a
  // group-header row, or off the grid entirely (a heading, a control) — clears the selection, so
  // "click off and the highlight goes away" holds everywhere. The checklist filter dropdowns
  // stopPropagation, so tuning a column filter never clears the selection.
  document.addEventListener("click", function (e) {
    var inGrid = view.contains(e.target);
    // UID click = retarget (operator 2026-08-20): set the Target UID and re-trace the
    // driving paths to that activity. Runs before the highlight logic; the row highlight
    // still applies (the traced view always contains its own target).
    var uidEl = inGrid && e.target.closest ? e.target.closest(".pv-uid") : null;
    if (uidEl) {
      var uidRow = uidEl.closest("tr[data-uid]");
      if (uidRow) {
        $("pathTarget").value = uidRow.getAttribute("data-uid");
        selectedUid = uidRow.getAttribute("data-uid");
        trace();
        return;
      }
    }
    var row = inGrid && e.target.closest ? e.target.closest("tr[data-uid]") : null;
    var uid = row ? row.getAttribute("data-uid") : null;
    if (uid === selectedUid) return; // same task, or an off-click with nothing selected — no-op
    selectedUid = uid;
    reskinSelection();
  });
  // keyboard parity for the UID retarget affordance (role=link, tabindex=0)
  document.addEventListener("keydown", function (e) {
    if (e.key !== "Enter") return;
    var uidEl = view.contains(e.target) && e.target.closest ? e.target.closest(".pv-uid") : null;
    var uidRow = uidEl ? uidEl.closest("tr[data-uid]") : null;
    if (!uidRow) return;
    e.preventDefault();
    $("pathTarget").value = uidRow.getAttribute("data-uid");
    selectedUid = uidRow.getAttribute("data-uid");
    trace();
  });
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
  if ($("pathGroupBy")) $("pathGroupBy").addEventListener("change", function () { if (data) paintRows(); });
  if ($("pathShowLinks")) $("pathShowLinks").addEventListener("change", function () { if (data) paintRows(); });
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
  // ADR-0441: a slider drag fires dozens of input events and each rebuild is O(rows × gridlines)
  // — measured 4-6 s per rebuild at an operator-scale 2,280 rows, which reads as a dead page.
  // The burst coalesces into one trailing rebuild.
  // ADR-0441: a slider drag fires dozens of input events and each rebuild is O(rows × gridlines)
  // — measured 4-6 s per rebuild at an operator-scale 2,280 rows, which reads as a dead page.
  // The burst coalesces into one trailing rebuild.
  var pathZoomTimer;
  $("pathZoom").addEventListener("input", function () {
    fitFill = false;
    clearTimeout(pathZoomTimer);
    pathZoomTimer = setTimeout(reflow, 120);
  });
  // the Timescale dialog's OK repaints the timeline with the new tiers/size/shading
  window.addEventListener("sf-timescale", function () { if (data) reflow(); });
  var pathFit = $("pathFit");
  if (pathFit) pathFit.addEventListener("click", fitToProject);
  // scrolling to the pane's right edge extends the axis (unlimited right scroll, ADR-0187);
  // fires only in fixed-zoom mode — a fill-to-page timeline has no scrollbar to extend
  SFGantt.attachEdgeExtend(view, function () { extraRightDays += 60; if (data) reflow(); });
  // MS-Project "dates on bars" (parity with the Activities Gantt — ADR-0186)
  if ($("pathBarDates")) $("pathBarDates").addEventListener("change", function () { if (data) paintRows(); });
  // Vertical scroll re-aims the painted window (S5, ADR-0442): when the visible slice nears
  // either edge of what is materialized, repaint around the new position. rAF-throttled; inert
  // whenever the last paint was full (winState null). Horizontal scrolls change nothing here.
  var winScrollQueued = false;
  view.addEventListener("scroll", function () {
    if (!winState || winScrollQueued) return;
    winScrollQueued = true;
    requestAnimationFrame(function () {
      winScrollQueued = false;
      if (!winState) return;
      var tbody = $("pathBody");
      var rowH = winRowH > 0 ? winRowH : 18;
      var headH = tbody ? tbody.offsetTop : 0;
      var visStart = Math.floor(Math.max(0, view.scrollTop - headH) / rowH);
      var visEnd = visStart + Math.ceil((view.clientHeight || 600) / rowH);
      var margin = WINDOW_OVERSCAN / 2;
      if ((visStart - winState.start < margin && winState.start > 0) ||
          (winState.end - visEnd < margin && winState.end < winState.total)) {
        paintRows();
      }
    });
  }, { passive: true });
  // Print materializes every row first: the A5 print contract prints the scroll panes in full
  // (base.css forces .path-view overflow visible), so a windowed tbody would print spacers.
  window.addEventListener("beforeprint", function () {
    if (winState) { windowFullOnce = true; paintRows(); }
  });
  window.addEventListener("afterprint", function () { if (data) paintRows(); });
  // MS-Project Find: jump the traced grid to a UniqueID, scroll it into view and flash it.
  // A windowed grid materializes only the viewport slice, and findTask searches the DOM —
  // so a non-empty Find forces one full paint first (marks then survive scrolling; the next
  // zoom/filter repaint re-windows, which is when pre-fix marks were lost too).
  function findUid(q) {
    if (winState && String(q == null ? "" : q).trim()) {
      windowFullOnce = true;
      paintRows();
    }
    SFGantt.findTask(view, q, $("pathFindStatus"));
  }
  var pathFind = $("pathFind");
  if (pathFind) {
    var goFind = function () { findUid(pathFind.value); };
    pathFind.addEventListener("change", goFind);
    pathFind.addEventListener("keydown", function (e) { if (e.key === "Enter") { e.preventDefault(); goFind(); } });
  }
  // column-mover grip (SFGantt): reorder the FIELD MODEL so repaints keep the new order —
  // without this the DOM fallback moved cells but the next paintRows() reset them (ADR-0186)
  document.addEventListener("sf-colmove", function (ev) {
    if (!view.contains(ev.target)) return;
    var visible = FIELDS.filter(function (f) { return f.on; });
    var i = ev.detail.index;
    // the ↔ menu sends a single step (dir); a header drag sends an absolute target (to)
    var to = (ev.detail.to != null) ? ev.detail.to : i + ev.detail.dir;
    if (i < 0 || i >= visible.length || to < 0 || to >= visible.length || i === to) return;
    ev.preventDefault(); // re-render from the model instead of a raw DOM move
    var order = visible.slice();
    order.splice(to, 0, order.splice(i, 1)[0]); // move visible[i] to position `to`
    var vi = 0; // write the new visible order back into the ON slots, leaving hidden fields put
    for (var k = 0; k < FIELDS.length; k++) if (FIELDS[k].on) FIELDS[k] = order[vi++];
    render();
  });
  // switching the version re-loads the same view mode for the newly-picked file
  $("pathSchedule").addEventListener("change", function () {
    if ($("pathTarget").value) trace(); else wholeSchedule();
  });
  // a remembered Target UID restored by persist.js (ADR-0186) arrives AFTER this boot ran —
  // it may re-trace OVER the whole-schedule default, but never clobber an explicit trace
  window.addEventListener("sf-restored", function () {
    if ($("pathTarget").value && (!data || data.whole_schedule)) trace();
  });
  // a session-wide target traces immediately; otherwise the COMPLETE schedule is the
  // default view (operator 2026-08-20) — a UID click or Trace starts the path analysis
  if ($("pathTarget").value) trace(); else wholeSchedule();
})();
