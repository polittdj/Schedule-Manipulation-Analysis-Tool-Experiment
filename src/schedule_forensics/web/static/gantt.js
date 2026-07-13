/* Schedule Forensics — shared Microsoft-Project-style Gantt timeline primitives.
 *
 * Operator: "Make the Gantt mirror Microsoft Project on all pages — the three-tier timeline
 * (Year / Quarter / Month), the gridlines, the WBS indentation, zoom." This is the single
 * implementation of that timeline header + gridlines, so every HTML Gantt on the site (the
 * activity grid, the driving-path trace, the path workspace, the corridor animation) reads
 * identically. Dependency-free, air-gap-safe (no CDN). window.SFGantt.
 *
 * The contract is a tiny "axis" object: { t0, t1, width, x(ms) -> px } where t0/t1 are epoch
 * milliseconds spanning the chart and x() maps a timestamp to a pixel offset. Each page keeps
 * its own axis construction (zoom = pixels-per-day differs per view) and only swaps its old
 * single-tier header for buildTierScale() and adds gridLines() down each track.
 */
"use strict";

window.SFGantt = (function () {
  var DAY_MS = 86400000;
  var MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

  function el(tag, attrs) {
    var node = document.createElement(tag);
    if (attrs) {
      Object.keys(attrs).forEach(function (k) {
        if (k === "text") node.textContent = attrs[k];
        else if (k === "class") node.className = attrs[k];
        else node.setAttribute(k, attrs[k]);
      });
    }
    return node;
  }

  // The operator's date format, everywhere a Gantt shows a date: "2026-02-25" (or an ISO
  // datetime) -> "02/25/2026", zero-padded, never a time-of-day. Parses the ISO parts directly
  // (no Date construction) so there is no timezone shift. Returns "" for anything that is not
  // an ISO date, so callers can fall back to the raw value. Data stays ISO; format at render.
  function fmtMDY(iso) {
    var m = /^(\d{4})-(\d\d)-(\d\d)(?:[T ].*)?$/.exec(String(iso == null ? "" : iso));
    return m ? m[2] + "/" + m[3] + "/" + m[1] : "";
  }

  // Year / Quarter / Month bands across the axis, each spanning [period-start, next-start) in
  // pixels. Narrow bands collapse their label (a quarter to "Q1", a month to a single letter)
  // exactly like Microsoft Project's timeline does as you zoom out.
  function timeTiers(axis) {
    function bands(startOf, advance, label) {
      var out = [];
      var cur = new Date(axis.t0);
      startOf(cur);
      var guard = 0;
      while (cur.getTime() <= axis.t1 && guard++ < 6000) {
        var next = new Date(cur);
        advance(next);
        var left = axis.x(cur.getTime());
        var right = axis.x(next.getTime());
        var w = right - left;
        if (right > 0 && left < axis.width) {
          out.push({ left: Math.max(0, left), width: Math.max(1, w), label: label(cur, w) });
        }
        cur.setTime(next.getTime());
      }
      return out;
    }
    var years = bands(
      function (d) { d.setUTCMonth(0, 1); d.setUTCHours(0, 0, 0, 0); },
      function (d) { d.setUTCFullYear(d.getUTCFullYear() + 1); },
      function (d) { return String(d.getUTCFullYear()); }
    );
    var quarters = bands(
      function (d) { d.setUTCMonth(Math.floor(d.getUTCMonth() / 3) * 3, 1); d.setUTCHours(0, 0, 0, 0); },
      function (d) { d.setUTCMonth(d.getUTCMonth() + 3); },
      function (d, w) {
        return w < 34 ? "Q" + (Math.floor(d.getUTCMonth() / 3) + 1)
          : "Qtr " + (Math.floor(d.getUTCMonth() / 3) + 1) + " " + d.getUTCFullYear();
      }
    );
    var months = bands(
      function (d) { d.setUTCDate(1); d.setUTCHours(0, 0, 0, 0); },
      function (d) { d.setUTCMonth(d.getUTCMonth() + 1); },
      function (d, w) { return w < 22 ? MONTHS[d.getUTCMonth()][0] : MONTHS[d.getUTCMonth()]; }
    );
    return { years: years, quarters: quarters, months: months };
  }

  // The stacked timescale header element (Microsoft Project timeline). `baseClass` is the
  // page's own scale class (so its width/flex rules still apply); `anchorIso`, when given,
  // draws the data-date / now line through the header. When the SFTimescale module is loaded
  // (the MS-Project Timescale dialog, operator 2026-07-08) the tiers/units/labels/count/align/
  // tick-lines/fiscal-year/separator all come from its configuration; without it the header
  // falls back to the original fixed Year/Quarter/Month stack.
  function buildTierScale(axis, baseClass, anchorIso) {
    var scale = el("div", { class: baseClass + " g-scale-tiered", style: "width:" + axis.width + "px" });
    var ts = window.SFTimescale;
    if (ts) {
      ts.axisHint(axis); // the dialog's preview mirrors the page's real span
      var stack = ts.tiers(axis);
      var n = stack.rows.length;
      scale.classList.add("g-scale-rows-" + n);
      if (!stack.separator) scale.classList.add("g-scale-nosep");
      stack.rows.forEach(function (row, i) {
        // reuse the yr/qtr/mo row styling top-down so fonts/weights read like MS Project
        var cls = i === 0 ? "yr" : i === n - 1 ? "mo" : "qtr";
        var tierEl = el("div", { class: "g-tier g-tier-" + cls + (row.ticks ? "" : " g-tier-noticks") });
        tierEl.style.top = (i * 18) + "px";
        row.bands.forEach(function (b) {
          tierEl.appendChild(el("div", {
            class: "g-band" + (b.warn ? " g-band-warn" : ""), title: b.label, text: b.label,
            style: "left:" + b.left + "px;width:" + b.width + "px;text-align:" + (b.align || "center"),
          }));
        });
        scale.appendChild(tierEl);
      });
    } else {
      var tiers = timeTiers(axis);
      [["yr", tiers.years], ["qtr", tiers.quarters], ["mo", tiers.months]].forEach(function (t) {
        var row = el("div", { class: "g-tier g-tier-" + t[0] });
        t[1].forEach(function (b) {
          row.appendChild(el("div", {
            class: "g-band", title: b.label, text: b.label,
            style: "left:" + b.left + "px;width:" + b.width + "px",
          }));
        });
        scale.appendChild(row);
      });
    }
    if (anchorIso) {
      var a = Date.parse(anchorIso);
      if (!isNaN(a)) scale.appendChild(el("div", { class: "pv-now", style: "left:" + axis.x(a) + "px" }));
    }
    return scale;
  }

  // Vertical gridlines down a chart, lined up with the header bands (MS-Project gridlines).
  // With SFTimescale loaded they follow the configured tiers (light at the bottom tier's
  // boundaries, heavier up the stack); the fallback is the original month/quarter/year set.
  function gridLines(axis) {
    if (window.SFTimescale) return window.SFTimescale.gridBoundaries(axis);
    var lines = [];
    var d = new Date(axis.t0);
    d.setUTCDate(1); d.setUTCHours(0, 0, 0, 0);
    var guard = 0;
    while (d.getTime() <= axis.t1 && guard++ < 6000) {
      var left = axis.x(d.getTime());
      if (left >= 0 && left <= axis.width) {
        var m = d.getUTCMonth();
        var cls = m === 0 ? "g-grid g-grid-yr" : m % 3 === 0 ? "g-grid g-grid-qtr" : "g-grid";
        lines.push({ left: left, cls: cls });
      }
      d.setUTCMonth(d.getUTCMonth() + 1);
    }
    return lines;
  }

  // Non-working-time shading (the dialog's fourth tab): delegate to SFTimescale, which shades the
  // CELL (full row height) so the bands are continuous down the column — callers pass the <td>
  // cell (after appending the track), not the inner track. No-op when the module is absent/off.
  function paintNonwork(cell, axis) {
    if (window.SFTimescale) window.SFTimescale.decorateCell(cell, axis);
  }

  // Append month/quarter/year gridline divs into a track element (small convenience used by the
  // HTML Gantts so each track carries the same vertical rules as the header).
  function paintGrid(track, lines) {
    (lines || []).forEach(function (g) {
      track.appendChild(el("div", { class: g.cls, style: "left:" + g.left + "px" }));
    });
  }

  // MS-Project frozen columns: pin every data column (all but the final, scalable timeline column)
  // to the left edge so the data stays visible while the wide timeline scrolls left↔right. The
  // rendered header widths give each column's cumulative left offset; we set position:sticky + that
  // offset on the column's header, filter-row and body cells (the CSS gives them an opaque canvas
  // background + a freeze line). Returns the total frozen width (px) so a caller can size the
  // remaining timeline to exactly fill the page. Idempotent — safe to re-run after a body repaint
  // or a column resize. Works whether the body rows live in a <tbody> or are bare <tr> children.
  // PRECONDITION (audit L8): left offsets come from header offsetWidth, which is stable only
  // because SFColResize.attach pins explicit widths (table-layout:fixed) BEFORE this runs. If
  // that ordering ever changes, offsets drift on content reflow — keep attach() first.
  function freezeColumns(table) {
    if (!table) return 0;
    var headRow = table.querySelector("thead tr");
    if (!headRow) return 0;
    var headCells = headRow.children;
    var frozen = headCells.length - 1; // the last column is the scalable timeline — it must scroll
    if (frozen < 1) return 0;
    var offsets = [];
    var acc = 0;
    for (var i = 0; i < frozen; i++) {
      offsets.push(acc);
      acc += headCells[i].offsetWidth;
    }
    var rows = table.rows; // every row: the header rows, the filter row, and all body rows
    for (var r = 0; r < rows.length; r++) {
      var cells = rows[r].children;
      for (var c = 0; c < frozen && c < cells.length; c++) {
        var cell = cells[c];
        // skip redundant style writes (audit M7): on a ~1700-row grid most cells already carry
        // the correct sticky offset after a repaint, so only touch the DOM when a value changes.
        var leftPx = offsets[c] + "px";
        if (cell.style.position !== "sticky") cell.style.position = "sticky";
        if (cell.style.left !== leftPx) cell.style.left = leftPx;
        cell.classList.add("sf-frozen-col"); // idempotent
        if (c === frozen - 1) cell.classList.add("sf-frozen-last");
        else cell.classList.remove("sf-frozen-last");
      }
    }
    return acc;
  }

  // Always-visible bottom scrollbar (operator 2026-07-09: "have the slider bar at the bottom
  // visible while the user is using the gantt"). A tall Gantt scroll pane hides its native
  // horizontal scrollbar at the very bottom of its content, so an analyst reading rows near
  // the top has to scroll all the way down to reach it. This attaches a proxy horizontal
  // scrollbar that sticks to the BOTTOM OF THE VIEWPORT while any part of the pane is on
  // screen, mirroring (and driving) the pane's scrollLeft. Idempotent per pane; the proxy
  // hides itself when the pane needs no horizontal scroll or is off-screen. Applied through
  // the same SFGantt layer every page's Gantt already uses, so all of them inherit it.
  function stickyScrollbar(pane) {
    if (!pane || pane._sfSticky) return;
    pane._sfSticky = true;
    var bar = el("div", { class: "sf-sticky-xscroll" });
    var inner = el("div", { class: "sf-sticky-xscroll-inner" });
    bar.appendChild(inner);
    document.body.appendChild(bar);
    var syncing = false;
    function measure() {
      inner.style.width = pane.scrollWidth + "px";
      bar.style.height = pane.scrollWidth > pane.clientWidth + 1 ? "" : "0";
    }
    function place() {
      var rect = pane.getBoundingClientRect();
      var vh = window.innerHeight || document.documentElement.clientHeight;
      // show the proxy whenever the pane overflows horizontally and is on screen — the pane's
      // own bottom scrollbar sits far below in a tall Gantt, so the proxy keeps a reachable
      // slider at the viewport bottom "while the user is using the gantt" (operator ask). Hide
      // only when there's nothing to scroll or the pane is entirely off screen.
      var needs = pane.scrollWidth > pane.clientWidth + 1;
      var onScreen = rect.top < vh - 15 && rect.bottom > 0;
      if (!needs || !onScreen) { bar.style.display = "none"; return; }
      bar.style.display = "block";
      bar.style.left = rect.left + "px";
      bar.style.width = Math.min(rect.width, (window.innerWidth || rect.width)) + "px";
    }
    function fromPane() {
      if (syncing) return;
      syncing = true; bar.scrollLeft = pane.scrollLeft; syncing = false;
    }
    function fromBar() {
      if (syncing) return;
      syncing = true; pane.scrollLeft = bar.scrollLeft; syncing = false;
    }
    pane.addEventListener("scroll", fromPane, { passive: true });
    bar.addEventListener("scroll", fromBar, { passive: true });
    window.addEventListener("scroll", place, { passive: true });
    window.addEventListener("resize", function () { measure(); place(); }, { passive: true });
    // re-measure when the pane's content changes size (zoom, filter, repaint)
    if (window.ResizeObserver) {
      var ro = new ResizeObserver(function () { measure(); place(); });
      ro.observe(pane);
      if (pane.firstElementChild) ro.observe(pane.firstElementChild);
    }
    measure();
    place();
    pane._sfStickyRefresh = function () { measure(); place(); };
  }

  // Attach the sticky scrollbar to every standard Gantt scroll pane on the page (called on load
  // by app.js / the page scripts; safe to call repeatedly — each pane is decorated once).
  function attachStickyScrollbars(root) {
    var panes = (root || document).querySelectorAll(
      "#grid, .gantt-scroll, .path-view, .sra-grid-scroll"
    );
    Array.prototype.forEach.call(panes, stickyScrollbar);
  }

  /* -------- unlimited right scroll (operator 2026-07-10, ADR-0187) --------------------
   * "Click the arrow on the right and have it continue to scroll — not be limited." When a
   * Gantt pane is scrolled to its right edge, ask the page to EXTEND its time axis so the
   * scrollbar keeps going into future time instead of stopping at the last bar. The page's
   * callback grows its axis by some days and re-renders; the helper restores the scroll
   * position so the view doesn't jump. Idempotent per pane. Fires only when the pane
   * actually overflows (a fill-to-page Gantt has no scrollbar, so nothing to extend). */
  function attachEdgeExtend(pane, onExtend) {
    if (!pane || pane._sfEdgeExtend) return;
    pane._sfEdgeExtend = true;
    var busy = false;
    pane.addEventListener("scroll", function () {
      if (busy) return;
      if (pane.scrollWidth <= pane.clientWidth + 2) return; // nothing scrollable
      if (pane.scrollLeft + pane.clientWidth < pane.scrollWidth - 2) return; // not at the edge
      busy = true;
      var keep = pane.scrollLeft;
      onExtend();
      window.requestAnimationFrame(function () {
        pane.scrollLeft = keep;
        busy = false;
        if (pane._sfStickyRefresh) pane._sfStickyRefresh(); // proxy scrollbar re-measures
      });
    }, { passive: true });
  }

  /* -------- column mover (operator 2026-07-10): click a data-column header's grip and move
   * the column left/right. Works on EVERY .gantt-grid table with zero per-page wiring: the
   * grip dispatches a cancelable "sf-colmove" CustomEvent {index, dir} on the table so a page
   * that owns a column model (the Activities grid's field list) can reorder its model and
   * re-render; if nobody preventDefault()s, the cells are moved in the DOM directly.
   * The timeline column (.g-head) never moves and columns never cross it. -------- */
  function moveTableColumn(table, index, dir) {
    var to = index + dir;
    var rows = table.rows;
    if (to < 0) return;
    for (var r = 0; r < rows.length; r++) {
      var cells = rows[r].cells;
      if (index >= cells.length || to >= cells.length) continue;
      var a = cells[index], b = cells[to];
      if (!a || !b) continue;
      if (a.classList.contains("g-head") || b.classList.contains("g-head")) return;
      if (dir < 0) a.parentNode.insertBefore(a, b);
      else a.parentNode.insertBefore(b, a);
    }
  }
  function closeColMenu() {
    var open = document.querySelector(".sf-colmove-menu");
    if (open) open.parentNode.removeChild(open);
  }
  function openColMenu(th, table) {
    closeColMenu();
    var index = Array.prototype.indexOf.call(th.parentNode.cells, th);
    var menu = el("div", { class: "sf-colmove-menu", role: "menu" });
    [["◀ Move left", -1], ["Move right ▶", 1]].forEach(function (m) {
      var btn = el("button", { type: "button", text: m[0] });
      btn.addEventListener("click", function (ev) {
        ev.stopPropagation();
        var evt;
        try {
          evt = new CustomEvent("sf-colmove", {
            bubbles: true, cancelable: true, detail: { index: index, dir: m[1], th: th },
          });
        } catch (e) { evt = null; }
        var doDefault = !evt || table.dispatchEvent(evt);
        if (doDefault) moveTableColumn(table, index, m[1]);
        closeColMenu();
      });
      menu.appendChild(btn);
    });
    var rect = th.getBoundingClientRect();
    menu.style.left = rect.left + window.scrollX + "px";
    menu.style.top = rect.bottom + window.scrollY + 2 + "px";
    document.body.appendChild(menu);
    setTimeout(function () {
      document.addEventListener("click", function once() {
        closeColMenu();
        document.removeEventListener("click", once);
      });
    }, 0);
  }
  function attachColumnMovers(root) {
    var tables = (root || document).querySelectorAll("table.gantt-grid");
    Array.prototype.forEach.call(tables, function (table) {
      var head = table.tHead && table.tHead.rows[0];
      if (!head) return;
      Array.prototype.forEach.call(head.cells, function (th) {
        if (th._sfColMove || th.classList.contains("g-head")) return;
        th._sfColMove = true;
        var grip = el("span", { class: "sf-colgrip", title: "Move this column left / right" });
        grip.textContent = "↔";
        grip.addEventListener("click", function (ev) {
          ev.stopPropagation(); // never trigger the header's sort
          openColMenu(th, table);
        });
        th.appendChild(grip);
      });
    });
  }

  /* -------- left-button column DRAG (operator item 4): grab a data-column header and drag it
   * left/right to reorder. Reuses the same "sf-colmove" plumbing as the ↔ grip menu, but carries
   * an absolute target index {index, to, dir} so a multi-column move is one event (one re-render);
   * a page that owns a column model reorders + repaints, else the DOM cells are moved directly.
   * The timeline column (.g-head) never moves and columns never cross it. The ↔ menu stays as a
   * click fallback. Works on EVERY .gantt-grid with no per-page wiring. -------- */
  function moveTableColumnTo(table, from, to) {
    var dir = to > from ? 1 : -1, i = from;
    while (i !== to) {
      moveTableColumn(table, i, dir);
      i += dir;
    }
  }
  function clearDropHints(head) {
    Array.prototype.forEach.call(head.cells, function (c) {
      c.classList.remove("sf-col-drop");
    });
  }
  function attachColumnDrag(root) {
    var tables = (root || document).querySelectorAll("table.gantt-grid");
    Array.prototype.forEach.call(tables, function (table) {
      var head = table.tHead && table.tHead.rows[0];
      if (!head) return;
      Array.prototype.forEach.call(head.cells, function (th) {
        if (th._sfColDrag || th.classList.contains("g-head")) return;
        th._sfColDrag = true;
        th.setAttribute("draggable", "true");
        th.addEventListener("dragstart", function (ev) {
          var idx = Array.prototype.indexOf.call(th.parentNode.cells, th);
          if (ev.dataTransfer) {
            ev.dataTransfer.setData("text/sf-col", String(idx));
            ev.dataTransfer.effectAllowed = "move";
          }
          th.classList.add("sf-col-dragging");
        });
        th.addEventListener("dragend", function () {
          th.classList.remove("sf-col-dragging");
          clearDropHints(head);
        });
        th.addEventListener("dragover", function (ev) {
          if (th.classList.contains("g-head")) return; // never drop onto the timeline
          ev.preventDefault();
          if (ev.dataTransfer) ev.dataTransfer.dropEffect = "move";
          clearDropHints(head);
          th.classList.add("sf-col-drop");
        });
        th.addEventListener("dragleave", function () {
          th.classList.remove("sf-col-drop");
        });
        th.addEventListener("drop", function (ev) {
          ev.preventDefault();
          clearDropHints(head);
          var from = ev.dataTransfer ? parseInt(ev.dataTransfer.getData("text/sf-col"), 10) : NaN;
          var to = Array.prototype.indexOf.call(th.parentNode.cells, th);
          if (isNaN(from) || from < 0 || from === to) return;
          var evt = null;
          try {
            evt = new CustomEvent("sf-colmove", {
              bubbles: true, cancelable: true,
              detail: { index: from, to: to, dir: to > from ? 1 : -1, th: th },
            });
          } catch (e) { evt = null; }
          var doDefault = !evt || table.dispatchEvent(evt);
          if (doDefault) moveTableColumnTo(table, from, to);
        });
      });
    });
  }

  return {
    DAY_MS: DAY_MS, MONTHS: MONTHS, el: el, fmtMDY: fmtMDY,
    timeTiers: timeTiers, buildTierScale: buildTierScale,
    gridLines: gridLines, paintGrid: paintGrid, paintNonwork: paintNonwork,
    freezeColumns: freezeColumns,
    stickyScrollbar: stickyScrollbar, attachStickyScrollbars: attachStickyScrollbars,
    attachEdgeExtend: attachEdgeExtend,
    moveTableColumn: moveTableColumn, moveTableColumnTo: moveTableColumnTo,
    attachColumnMovers: attachColumnMovers, attachColumnDrag: attachColumnDrag,
  };
})();

// Auto-init the always-visible bottom scrollbar on every standard Gantt pane, including panes
// the async page scripts build after load (a MutationObserver catches them). One decoration per
// pane (idempotent), so every Gantt across the tool inherits it with no per-page wiring.
(function () {
  "use strict";
  function boot() {
    if (!window.SFGantt) return;
    SFGantt.attachStickyScrollbars(document);
    SFGantt.attachColumnMovers(document);
    SFGantt.attachColumnDrag(document);
    if (window.MutationObserver) {
      var obs = new MutationObserver(function () {
        SFGantt.attachStickyScrollbars(document);
        SFGantt.attachColumnMovers(document);
        SFGantt.attachColumnDrag(document);
      });
      obs.observe(document.body, { childList: true, subtree: true });
    }
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
