/* Schedule Forensics — MS-Project-style draggable column resizing for the Gantt grids. Vendored,
 * dependency-free, air-gap-safe. window.SFColResize.attach(table, key) puts a drag handle on every
 * data-column header; dragging widens/narrows just that column (the data reflows: names wrap, the
 * fixed columns clip). The scalable timeline column (.g-head) is left alone. Widths persist per
 * `key` across re-renders (filter / zoom / save) so a resize isn't lost when the grid rebuilds.
 */
"use strict";

window.SFColResize = (function () {
  var store = {}; // key -> { colIndex: widthPx }

  function setWidth(th, w) {
    th.style.width = w + "px";
    th.style.minWidth = w + "px";
    th.style.maxWidth = w + "px";
  }

  function attach(table, key) {
    if (!table) return;
    var head = table.querySelector("thead tr");
    if (!head) return;
    var saved = store[key] || (store[key] = {});
    var ths = Array.prototype.slice.call(head.children);
    // snapshot current rendered widths BEFORE switching to fixed layout, then pin every column so
    // dragging one never reflows the others (the standard resizable-table technique)
    var widths = ths.map(function (th, i) {
      return saved[i] || Math.round(th.getBoundingClientRect().width);
    });
    ths.forEach(function (th, i) {
      // the scalable timeline column (.g-head) must NEVER be pinned: its width is the zoom
      // (px/day x span) and pinning the first render's width leaves thousands of px of dead
      // scroll space after Fit/zoom-out (operator 2026-07-08)
      if (th.classList.contains("g-head")) return;
      saved[i] = widths[i];
      setWidth(th, widths[i]);
    });
    table.style.tableLayout = "fixed";
    table.classList.add("col-resizable");
    // Size the scalable timeline column (.g-head) to its own content. It is intentionally never
    // PINNED in the `store` above — a stored width goes stale after zoom/Fit (the dead-scroll-space
    // bug). But under table-layout:fixed an UNSIZED column does not grow to its content; it only
    // gets leftover space, so the timeline collapses: the bars are clipped by the track's
    // overflow:hidden (INVISIBLE) and the table never exceeds the pane (nothing to SCROLL right
    // into). Set it FRESH here every attach (not in `store`) from the inner scale/track's own px
    // width (zoom x span), so the column always matches the current zoom without persisting a
    // stale value. Fixes every Gantt that routes through here (analysis / path / sra grid / …).
    ths.forEach(function (th) {
      if (!th.classList.contains("g-head")) return;
      var inner = th.firstElementChild; // buildTierScale's .g-scale carries style width:<axis.width>px
      var w = inner ? (parseFloat(inner.style.width) || inner.scrollWidth) : th.scrollWidth;
      if (w > 0) { th.style.width = w + "px"; th.style.minWidth = w + "px"; th.style.maxWidth = w + "px"; }
    });

    // Chromium does not honor top/right/bottom (or % height) on an absolutely-positioned child
    // of a table cell — sticky OR relative. Measured on every frozen Gantt header (WP1,
    // 2026-08-31): the grip laid out 7px x 0px at the cell's static content position, so no
    // pointer could ever hit it and drag-to-resize was dead on arrival. Explicit measured
    // geometry works (a px height sticks), so size the grip from the cell box and correct the
    // residual static-position offset by measurement. Re-run for existing grips on every
    // attach — the header re-lays-out as fonts settle and columns resize.
    function sizeGrip(handle, th) {
      var thH = th.offsetHeight;
      if (!(thH > 0)) return;
      handle.style.height = thH + "px";
      var r = handle.getBoundingClientRect();
      var tr = th.getBoundingClientRect();
      var dy = r.top - tr.top;
      var dx = r.left - (tr.right - r.width);
      if (dy) handle.style.top = ((parseFloat(handle.style.top) || 0) - dy) + "px";
      if (dx) handle.style.left = ((parseFloat(handle.style.left) || 0) - dx) + "px";
    }

    ths.forEach(function (th, i) {
      if (th.classList.contains("g-head")) return; // the timeline column keeps its scalable width
      var existing = th.querySelector(".col-rsz");
      if (existing) {
        sizeGrip(existing, th);
        return;
      }
      th.style.position = "relative";
      var handle = document.createElement("div");
      handle.className = "col-rsz";
      handle.title = "Drag to resize column";
      handle.addEventListener("click", function (e) { e.stopPropagation(); }); // not a header sort
      handle.addEventListener("pointerdown", function (e) {
        e.preventDefault();
        e.stopPropagation();
        var startX = e.clientX;
        var startW = th.getBoundingClientRect().width;
        try { handle.setPointerCapture(e.pointerId); } catch (err) { /* older browsers */ }
        function move(ev) {
          var w = Math.max(28, Math.round(startW + (ev.clientX - startX)));
          setWidth(th, w);
          saved[i] = w;
        }
        function up() {
          handle.removeEventListener("pointermove", move);
          handle.removeEventListener("pointerup", up);
          try { handle.releasePointerCapture(e.pointerId); } catch (err) { /* ignore */ }
          // a resize shifts every later column's left edge — re-pin the frozen columns to match
          if (window.SFGantt && window.SFGantt.freezeColumns) window.SFGantt.freezeColumns(table);
          sizeGrip(handle, th); // …and re-seat the grip on the column's new right edge
        }
        handle.addEventListener("pointermove", move);
        handle.addEventListener("pointerup", up);
      });
      th.appendChild(handle);
      sizeGrip(handle, th);
    });
  }

  return { attach: attach };
})();
