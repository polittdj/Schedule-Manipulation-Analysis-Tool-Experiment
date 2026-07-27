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

    ths.forEach(function (th, i) {
      if (th.classList.contains("g-head")) return; // the timeline column keeps its scalable width
      if (th.querySelector(".col-rsz")) return;
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
        }
        handle.addEventListener("pointermove", move);
        handle.addEventListener("pointerup", up);
      });
      th.appendChild(handle);
    });
  }

  return { attach: attach };
})();
