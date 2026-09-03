/* Schedule Forensics — chart accessibility helpers (Section 508 / WCAG 1.1.1).
 *
 * Two dependency-free, local-only helpers shared by the SVG chart scripts:
 *   • SFA11y.label(svg, name) — give a `role="img"` chart a real accessible NAME (a <title>
 *     first child + aria-label), so a screen reader announces what the graphic is instead of a
 *     nameless "graphic".
 *   • SFA11y.table(caption, headers, rows) — build a visually-hidden (`.sr-only`) data table from
 *     the same numbers the chart draws, so assistive tech can READ the values (the chart stays
 *     visual for sighted users). headers: [str]; rows: [[cell, …]] (first cell is the row header).
 *
 * Nothing leaves the machine — no CDN, no external fetch.
 */
"use strict";

(function () {
  var NS = "http://www.w3.org/2000/svg";

  function label(svg, name) {
    if (!svg || !name) return;
    svg.setAttribute("role", "img");
    svg.setAttribute("aria-label", name);
    var title = document.createElementNS(NS, "title");
    title.textContent = name;
    if (svg.firstChild) svg.insertBefore(title, svg.firstChild);
    else svg.appendChild(title);
  }

  function table(caption, headers, rows) {
    var tbl = document.createElement("table");
    tbl.className = "sr-only";
    var cap = document.createElement("caption");
    cap.textContent = caption;
    tbl.appendChild(cap);
    var thead = document.createElement("thead");
    var htr = document.createElement("tr");
    headers.forEach(function (h) {
      var th = document.createElement("th");
      th.setAttribute("scope", "col");
      th.textContent = h;
      htr.appendChild(th);
    });
    thead.appendChild(htr);
    tbl.appendChild(thead);
    var tbody = document.createElement("tbody");
    rows.forEach(function (r) {
      var tr = document.createElement("tr");
      r.forEach(function (cell, i) {
        var node = document.createElement(i === 0 ? "th" : "td");
        if (i === 0) node.setAttribute("scope", "row");
        node.textContent = cell === null || cell === undefined ? "" : String(cell);
        tr.appendChild(node);
      });
      tbody.appendChild(tr);
    });
    tbl.appendChild(tbody);
    return tbl;
  }

  window.SFA11y = { label: label, table: table };
})();
