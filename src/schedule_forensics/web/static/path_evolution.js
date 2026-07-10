/* Schedule Forensics — Critical-Path Evolution Gantt stepper (M18 item 7; table Gantt ADR-0187).
 *
 * A Prev/Next/Auto-play stepper over /api/evolution: each frame draws one version's critical
 * path as the SAME table-based Gantt every other page uses (operator 2026-07-10: "format the
 * Critical Path Gantt chart like the other Gantt Charts") — frozen data columns (UID, Name, %,
 * Dur, Start, Finish, Why), MS-Project tiered timescale + gridlines + non-working shading from
 * SFGantt/SFTimescale, per-column checklist filters, drag-to-resize + movable columns, the
 * sticky bottom scrollbar, dates-on-bars, and the shared Task Information dialog on row click.
 *
 * The date axis is LOCKED across every version (held fixed frame to frame so the path visibly
 * extends as the finish slips). Activities that ENTERED the path are green, those that STAYED
 * blue-grey, and a ▲ marks a duration change; activities that LEFT the path are drawn in a
 * second table as dashed/struck ghost bars at their prior position. Every entered/left activity
 * carries a reason chip explaining WHY it moved (new task / duration change / logic change /
 * constraint / slip / completed) — hover for the detail.
 *
 * Zoom buttons change the pixels-per-day scale (like the other Gantts); the pan arrows scroll
 * the pane; "View entire project" re-fits the whole locked axis to the page; scrolling to the
 * pane's right edge EXTENDS the axis (unlimited right scroll, ADR-0187). A ?target=<uid> focus
 * highlights that activity's row in every frame. The "filter the path" selector keeps its four
 * scopes (driving-to-focus / one version's path / movement / search). Dependency-free.
 */
"use strict";

(function () {
  var box = document.getElementById("evoChart");
  if (!box || !window.SFGantt) return;
  var DAY = 86400000;

  // reason code -> { short label, theme color }
  var REASON = {
    new: { label: "new task", color: "var(--ok)" },
    duration_up: { label: "duration ↑", color: "var(--warn)" },
    duration_down: { label: "duration ↓", color: "var(--warn)" },
    constraint: { label: "constraint", color: "var(--warn)" },
    logic_added: { label: "logic added", color: "var(--accent)" },
    logic_removed: { label: "logic removed", color: "var(--bad)" },
    slack_consumed: { label: "slip elsewhere", color: "var(--muted)" },
    completed: { label: "completed", color: "var(--ok)" },
    removed: { label: "removed", color: "var(--bad)" },
    gained_float: { label: "gained float", color: "var(--muted)" },
  };

  // the LOCKED full axis (fullLo..fullHi, padded) shared by every frame; extraRightDays grows
  // when the pane is scrolled to its right edge (unlimited right scroll)
  var data = null, index = 0, timer = null, fullLo = 0, fullHi = 1;
  var extraRightDays = 0;
  var pxZoom = null; // pixels/day set by the zoom buttons; null = fit the whole axis to the page
  var lastFrozenWidth = 0; // measured frozen-column width (SFGantt.freezeColumns return)
  var hideDone = false, focusUid = null;
  // filter-by-path: switchable modes — none | driving | version | movement | search
  var filterMode = "none", filterVersion = 0, searchText = "";
  var moveSet = { entered: true, stayed: true, left: true };
  var colFilters = {}; // per-column checklist filters (like every other Gantt); key -> Set|null

  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }
  // dates read MM/DD/YYYY like every other Gantt (shared SFGantt.fmtMDY; data stays ISO)
  function fmtDate(iso) {
    if (!iso) return "—";
    var s = String(iso);
    return SFGantt.fmtMDY(s) || s;
  }
  function barDatesOn() {
    var cb = document.getElementById("evoBarDates");
    return !!(cb && cb.checked);
  }

  function callout(snap) {
    var c = el("div", "ev-callout");
    var move = snap.finish_delta_days;
    var moveText = move == null ? "" :
      move > 0 ? " (slipped " + move + "d)" :
      move < 0 ? " (pulled in " + (-move) + "d)" : " (no move)";
    c.appendChild(el("span", "ev-finish", "Project finish: " + snap.project_finish + moveText));
    var sig = el("span", "ev-signals");
    var bits = [
      snap.entered.length + " entered",
      snap.left.length + " left",
      snap.duration_changed.length + " duration-changed on path",
    ];
    if (snap.shortened_on_path.length) bits.push(snap.shortened_on_path.length + " shortened on path");
    if (snap.removed_logic_count) bits.push(snap.removed_logic_count + " logic links removed");
    sig.textContent = bits.join(" · ");
    if ((snap.shortened_on_path.length || snap.removed_logic_count || snap.left.length) &&
        move != null && move <= 0) {
      sig.classList.add("ev-flag");
    }
    c.appendChild(sig);
    return c;
  }

  function legend() {
    var wrap = el("div", "legend");
    if (data && data.tier === "all") {
      // colour-by-tier legend (driving-slack tiers to the focus)
      [["driving", "var(--bad)", "critical / driving (0d)"],
        ["secondary", "var(--warn)", "secondary (≤ secondary days)"],
        ["tertiary", "var(--accent)", "tertiary"]].forEach(function (p) {
        var s = el("span", "", "■ " + p[2]);
        s.style.color = p[1];
        s.style.marginRight = "10px";
        wrap.appendChild(s);
      });
      return wrap;
    }
    [["ev-entered", "entered the path"], ["ev-stayed", "stayed"], ["ev-left", "left the path"]]
      .forEach(function (p) { wrap.appendChild(el("span", p[0], p[1])); });
    wrap.appendChild(el("span", "ev-stayed", "▲ duration change · hover a reason for detail"));
    return wrap;
  }

  // ---- the standard table Gantt (matches /path, /driving-path, the Activities grid) --------
  var COLS = [
    { key: "uid", label: "UID" },
    { key: "name", label: "Name" },
    { key: "percent_complete", label: "%" },
    { key: "duration", label: "Dur" },
    { key: "start", label: "Start" },
    { key: "finish", label: "Finish" },
    { key: "why", label: "Why" },
  ];
  function cellText(r, key) {
    if (key === "percent_complete") return r.percent_complete == null ? "" : r.percent_complete + "%";
    if (key === "start" || key === "finish") return fmtDate(r[key]);
    if (key === "why") {
      var rc = r.reason && REASON[r.reason];
      return rc ? rc.label : (r.kind === "stayed" ? "" : r.kind || "");
    }
    var v = r[key];
    return v == null ? "" : String(v);
  }
  function compareValues(a, b) {
    var mdy = /^(\d\d)\/(\d\d)\/(\d{4})$/;
    var ma = mdy.exec(a), mb = mdy.exec(b);
    if (ma && mb) {
      var ka = ma[3] + ma[1] + ma[2], kb = mb[3] + mb[1] + mb[2];
      return ka < kb ? -1 : ka > kb ? 1 : 0;
    }
    var na = parseFloat(a), nb = parseFloat(b);
    var bothNum = !isNaN(na) && !isNaN(nb) && /^-?\d/.test(a) && /^-?\d/.test(b);
    return bothNum ? na - nb : a < b ? -1 : a > b ? 1 : 0;
  }
  function rowMatchesColumns(r) {
    return COLS.every(function (c) {
      var sel = colFilters[c.key];
      return !sel || sel.has(cellText(r, c.key));
    });
  }

  function buildAxis() {
    var t0 = fullLo, t1 = fullHi + extraRightDays * DAY;
    var days = Math.max(1, (t1 - t0) / DAY);
    var size = window.SFTimescale ? SFTimescale.sizeFactor() : 1;
    if (!(size > 0)) size = 1;
    var avail = Math.max(240, (box.clientWidth || 1100) - (lastFrozenWidth || 430) - 18);
    var px = (pxZoom && pxZoom > 0 ? pxZoom : avail / days) * size;
    var width = Math.max(120, Math.round(days * px));
    return { t0: t0, t1: t1, width: width, x: function (ms) { return Math.round(((ms - t0) / DAY) * px); } };
  }

  // bar colour class: tier colours in all-tiers mode, else entered/stayed/left
  var TIER_CLASS = { driving: "ev-t-driving", secondary: "ev-t-secondary", tertiary: "ev-t-tertiary" };
  function barClass(r) {
    if (data && data.tier === "all" && r.tier && TIER_CLASS[r.tier]) return TIER_CLASS[r.tier];
    return r.kind === "entered" ? "ev-b-entered" : r.kind === "left" ? "ev-b-left" : "ev-b-stayed";
  }

  var LABEL_W = 64;
  function barLabel(track, axis, anchor, side, iso) {
    if (!iso) return;
    var lx = side === "s" ? anchor - LABEL_W : anchor;
    lx = Math.max(0, Math.min(axis.width - LABEL_W, lx));
    var d = el("div", "g-barlabel g-barlabel-" + side, SFGantt.fmtMDY(iso));
    d.style.left = lx + "px";
    d.style.width = LABEL_W + "px";
    track.appendChild(d);
  }

  // rows: [{uid, name, start, finish, kind, durBadge, reason, detail, percent_complete,
  // duration, complete}]. srcLabel = the schedule file these rows were read from (Task
  // Information provenance); "left the path" ghost rows pass the PRIOR version's label.
  function gantt(rows, srcLabel, statusDate) {
    var scroll = el("div", "gantt-scroll");
    if (!rows.length) { scroll.appendChild(el("p", "muted", "—")); return scroll; }
    var axis = buildAxis();
    var gridLns = SFGantt.gridLines(axis);
    var showDates = barDatesOn();

    var table = document.createElement("table");
    table.className = "gantt-grid evo-grid";
    var thead = document.createElement("thead");
    var head = document.createElement("tr");
    COLS.forEach(function (c) { head.appendChild(el("th", null, c.label)); });
    var thTime = el("th", "g-head");
    thTime.appendChild(SFGantt.buildTierScale(axis, "g-scale", statusDate));
    head.appendChild(thTime);
    thead.appendChild(head);
    // per-column MS-Project checklist filters — the same component as every other Gantt
    var filterRow = el("tr", "filter-row");
    COLS.forEach(function (c) {
      var td = document.createElement("td");
      if (window.SFChecklist) {
        var seen = {};
        rows.forEach(function (r) { seen[cellText(r, c.key)] = true; });
        td.appendChild(SFChecklist.filter({
          values: Object.keys(seen).sort(compareValues),
          selected: colFilters[c.key] || null,
          label: "Filter",
          title: "Filter " + c.label,
          onChange: function (sel) { colFilters[c.key] = sel; render(); },
        }));
        td.addEventListener("click", function (ev) { ev.stopPropagation(); });
      }
      filterRow.appendChild(td);
    });
    filterRow.appendChild(el("td", "muted"));
    thead.appendChild(filterRow);
    table.appendChild(thead);

    var tbody = document.createElement("tbody");
    rows.filter(rowMatchesColumns).forEach(function (r) {
      var tr = document.createElement("tr");
      tr.setAttribute("data-uid", r.uid);
      if (r.kind === "left") tr.className = "ev-row-left";
      if (focusUid != null && r.uid === focusUid) tr.className = (tr.className + " ev-focus").trim();
      // MS-Project Task Information on row click (shared dialog — ADR-0186), sourced from the
      // file this frame's rows were read from
      tr.addEventListener("click", function () {
        if (window.SFTaskInfo) SFTaskInfo.openFrom(srcLabel, r.uid);
      });
      COLS.forEach(function (c) {
        var td = document.createElement("td");
        td.textContent = cellText(r, c.key);
        if (c.key === "name") {
          td.className = "name-cell";
          if (r.kind === "left") td.style.textDecoration = "line-through";
        }
        if (c.key === "why" && r.reason && REASON[r.reason]) {
          td.className = "evo-why";
          td.style.color = REASON[r.reason].color;
          if (r.detail) td.title = r.detail;
        }
        tr.appendChild(td);
      });
      var cell = el("td", "g-cell");
      var track = el("div", "g-track");
      track.style.width = axis.width + "px";
      SFGantt.paintGrid(track, gridLns);
      if (statusDate) {
        var sd = Date.parse(statusDate);
        if (!isNaN(sd)) {
          var line = el("div", "g-status");
          line.style.left = axis.x(sd) + "px";
          track.appendChild(line);
        }
      }
      if (r.start && r.finish) {
        var x1 = axis.x(Date.parse(r.start));
        var w = Math.max(2, axis.x(Date.parse(r.finish)) - x1);
        var bar = el("div", "g-bar " + barClass(r));
        bar.style.left = x1 + "px";
        bar.style.width = w + "px";
        var rc = r.reason && REASON[r.reason];
        bar.title = "U" + r.uid + " · " + r.name + " — " + (r.kind || "on path") +
          ", " + fmtDate(r.start) + " → " + fmtDate(r.finish) +
          (r.percent_complete != null ? ", " + r.percent_complete + "%" : "") +
          (rc ? " (" + rc.label + (r.detail ? ": " + r.detail : "") + ")" : "");
        track.appendChild(bar);
        if (r.durBadge) {
          var badge = el("span", "evo-durbadge", "▲");
          badge.style.left = (x1 + w + 3) + "px";
          badge.title = "duration changed in this version";
          track.appendChild(badge);
        }
        if (showDates) {
          barLabel(track, axis, x1 - 3, "s", r.start);
          barLabel(track, axis, x1 + w + (r.durBadge ? 14 : 3), "f", r.finish);
        }
      }
      cell.appendChild(track);
      SFGantt.paintNonwork(cell, axis); // continuous weekend/holiday shading over the full row
      tr.appendChild(cell);
      tbody.appendChild(tr);
    });
    if (!tbody.children.length) {
      var none = document.createElement("tr");
      none.appendChild(el("td", "muted", "No activities match the filters."));
      tbody.appendChild(none);
    }
    table.appendChild(tbody);
    scroll.appendChild(table);
    if (window.SFColResize) SFColResize.attach(table, "evolution"); // drag-to-resize columns
    lastFrozenWidth = SFGantt.freezeColumns(table) || lastFrozenWidth; // frozen data columns
    // scrolling to the pane's right edge extends the locked axis (unlimited right scroll)
    SFGantt.attachEdgeExtend(scroll, function () { extraRightDays += 60; render(); });
    // the a11y "Data" table mirrors the frame (assistive tech + the tile Data toggle)
    if (window.SFA11y) {
      scroll.appendChild(
        SFA11y.table(
          "Critical path this version",
          ["UID", "Name", "Status", "Start", "Finish", "%"],
          rows.map(function (r) {
            return [
              "U" + r.uid, r.name, r.kind || "on path",
              fmtDate(r.start), fmtDate(r.finish),
              r.percent_complete != null ? r.percent_complete + "%" : "",
            ];
          })
        )
      );
    }
    return scroll;
  }

  function carry(r, extra) {
    var o = {
      uid: r.uid, name: r.name, start: r.start, finish: r.finish,
      percent_complete: r.percent_complete, duration: r.duration, complete: r.complete,
      tier: r.tier,
    };
    for (var k in extra) o[k] = extra[k];
    return o;
  }
  function currentRows(snap) {
    return snap.critical_rows.map(function (r) {
      return carry(r, {
        kind: r.entered ? "entered" : "stayed",
        durBadge: r.duration_changed, reason: r.entered ? r.reason : null, detail: r.detail,
      });
    });
  }
  function leftRows(snap) {
    return snap.left_rows.map(function (r) {
      return carry(r, { kind: "left", durBadge: false, reason: r.reason, detail: r.detail });
    });
  }
  function visible(rows) { return hideDone ? rows.filter(function (r) { return !r.complete; }) : rows; }

  function setOf(arr) { var o = {}; (arr || []).forEach(function (u) { o[u] = true; }); return o; }

  // filter-by-path: scope the rows by the active mode (applied to both the critical rows and
  // the "left the path" ghost rows)
  function applyFilter(rows, snap) {
    if (filterMode === "movement") return rows.filter(function (r) { return moveSet[r.kind]; });
    if (filterMode === "search") {
      var q = searchText.trim().toLowerCase();
      if (!q) return rows;
      return rows.filter(function (r) {
        return String(r.uid).indexOf(q) >= 0 || String(r.name || "").toLowerCase().indexOf(q) >= 0;
      });
    }
    if (filterMode === "driving") {
      var dset = setOf(snap.path_to_target);
      return rows.filter(function (r) { return dset[r.uid]; });
    }
    if (filterMode === "version") {
      var vsnap = data.snapshots[filterVersion];
      var cset = setOf(vsnap ? vsnap.critical : []);
      return rows.filter(function (r) { return cset[r.uid]; });
    }
    return rows;  // "none"
  }

  function filterNote(snap) {
    if (filterMode === "driving") {
      return focusUid == null ? "Set a Focus UID above to use the driving-path filter."
        : "Showing the chain that drives UID " + focusUid + " (its predecessors on the path).";
    }
    if (filterMode === "version") {
      var v = data.snapshots[filterVersion];
      return v ? "Showing version “" + v.label + "”'s critical path tracked across every frame." : "";
    }
    return "";
  }

  function render() {
    if (window.SFChecklist) SFChecklist.close(); // rebuilding discards any open popup
    var snap = data.snapshots[index];
    document.getElementById("evoLabel").textContent =
      (index + 1) + " / " + data.snapshots.length + " — " + snap.label +
      (snap.status_date ? " (data date " + snap.status_date + ")" : "");
    box.innerHTML = "";
    box.appendChild(callout(snap));
    box.appendChild(legend());
    if (focusUid != null) {
      var onPath = snap.critical_rows.some(function (r) { return r.uid === focusUid; });
      box.appendChild(el("p", onPath ? "ev-focus-on" : "muted",
        onPath ? "Focus UID " + focusUid + " is on this version's critical path (highlighted)."
               : "Focus UID " + focusUid + " is not on this version's critical path."));
    }
    var noteEl = document.getElementById("evoFilterNote");
    if (noteEl) noteEl.textContent = filterNote(snap);

    var crit = applyFilter(visible(currentRows(snap)), snap);
    var total = snap.critical_rows.length;
    box.appendChild(el("h3", null, "Critical path — " + crit.length +
      (crit.length !== total ? " of " + total : "") + " activities"));
    box.appendChild(gantt(crit, snap.label, snap.status_date));
    var leftV = applyFilter(visible(leftRows(snap)), snap);
    if (leftV.length) {
      box.appendChild(el("h3", null, "Left the critical path (" + leftV.length + ") — where they were, and why"));
      // ghost rows are drawn at their PRIOR-version position — cite that version's file
      var priorLabel = index > 0 ? data.snapshots[index - 1].label : snap.label;
      box.appendChild(gantt(leftV, priorLabel, snap.status_date));
    }
  }

  function step(delta) {
    index = (index + delta + data.snapshots.length) % data.snapshots.length;
    render();
  }

  // zoom = pixels-per-day like every other Gantt; pan scrolls the pane; reset re-fits the page
  function currentFitPx() {
    var days = Math.max(1, (fullHi + extraRightDays * DAY - fullLo) / DAY);
    var avail = Math.max(240, (box.clientWidth || 1100) - (lastFrozenWidth || 430) - 18);
    return avail / days;
  }
  function zoom(factor) {
    var base = pxZoom && pxZoom > 0 ? pxZoom : currentFitPx();
    pxZoom = Math.min(40, Math.max(0.02, base * factor));
    render();
  }
  function pan(frac) {
    var pane = box.querySelector(".gantt-scroll");
    if (pane) pane.scrollLeft += Math.round(pane.clientWidth * frac);
  }
  function resetZoom() { pxZoom = null; extraRightDays = 0; render(); }
  function stopAuto() {
    if (timer) { clearInterval(timer); timer = null; }
    document.getElementById("evoPlay").textContent = "▶ Auto-play";
  }
  function toggleAuto() {
    if (timer) { stopAuto(); return; }
    // A2: honor prefers-reduced-motion — advance one frame, don't auto-flip on a timer
    if (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      step(1); return;
    }
    document.getElementById("evoPlay").textContent = "⏸ Stop";
    timer = setInterval(function () { step(1); }, 1800);
  }

  var tgt = box.getAttribute("data-target");
  var tierMode = box.getAttribute("data-tier") || "off";
  fetch("/api/evolution?tier=" + encodeURIComponent(tierMode) +
        (tgt ? "&target=" + encodeURIComponent(tgt) : ""))
    .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); })
    .then(function (d) {
      data = d;
      focusUid = (d.target == null) ? null : Number(d.target);
      var lo = 0, hi = 1;
      if (d.axis && d.axis.min && d.axis.max) {
        lo = Date.parse(d.axis.min); hi = Date.parse(d.axis.max);
        if (!(hi > lo)) hi = lo + 30 * DAY;
        var pad = (hi - lo) * 0.04;
        lo -= pad; hi += pad;
      }
      fullLo = lo; fullHi = hi;  // the locked full axis, identical in every frame
      render();
      function on(id, fn) { var n = document.getElementById(id); if (n) n.addEventListener("click", fn); }
      on("prevEvo", function () { stopAuto(); step(-1); });
      on("nextEvo", function () { stopAuto(); step(1); });
      on("evoPlay", toggleAuto);
      on("evoZoomIn", function () { zoom(1.6); });
      on("evoZoomOut", function () { zoom(1 / 1.6); });
      on("evoPanL", function () { pan(-0.5); });
      on("evoPanR", function () { pan(0.5); });
      on("evoZoomReset", resetZoom);
      var hd = document.getElementById("evoHideDone");
      if (hd) hd.addEventListener("change", function () { hideDone = hd.checked; render(); });
      // MS-Project "dates on bars" (parity with the Activities Gantt — ADR-0186)
      var bd = document.getElementById("evoBarDates");
      if (bd) bd.addEventListener("change", render);
      // the Timescale dialog's OK repaints the frame with the new tiers/size/shading
      window.addEventListener("sf-timescale", function () { if (data) render(); });

      // filter-by-path controls: a mode selector that toggles its sub-control
      var verSel = document.getElementById("evoFilterVersion");
      if (verSel) {
        d.snapshots.forEach(function (s, i) {
          var o = document.createElement("option");
          o.value = i; o.textContent = s.label;
          verSel.appendChild(o);
        });
        verSel.addEventListener("change", function () { filterVersion = Number(verSel.value); render(); });
      }
      var modeSel = document.getElementById("evoFilterMode");
      var moveBox = document.getElementById("evoFilterMovement");
      var textBox = document.getElementById("evoFilterText");
      function showSub() {
        if (verSel) verSel.style.display = filterMode === "version" ? "" : "none";
        if (moveBox) moveBox.style.display = filterMode === "movement" ? "" : "none";
        if (textBox) textBox.style.display = filterMode === "search" ? "" : "none";
      }
      if (modeSel) modeSel.addEventListener("change", function () {
        filterMode = modeSel.value; showSub(); render();
      });
      Array.prototype.forEach.call(document.querySelectorAll(".evoMove"), function (cb) {
        cb.addEventListener("change", function () { moveSet[cb.value] = cb.checked; render(); });
      });
      if (textBox) textBox.addEventListener("input", function () { searchText = textBox.value; render(); });
    })
    .catch(function () { box.textContent = "Failed to load the path-evolution data."; });
})();
