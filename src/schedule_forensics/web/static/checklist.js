/* Schedule Forensics — MS-Project-style column filter dropdowns.
 *
 * A dependency-free, fully local checklist filter: a button that opens a popup listing the
 * distinct values of a column as checkboxes, with a search box and Select-all / Clear links.
 * Replaces the old substring filter inputs (grid) and single-tier <select>s. Exposed as
 * window.SFChecklist so app.js (the /analysis grid + trace tier) and path.js (the /path tier)
 * can reuse one implementation. Nothing leaves the machine — no CDN, no external fetch.
 *
 * SFChecklist.filter(opts) -> a DOM node to mount in a header / control cell.
 *   opts.values    : [string]  distinct, already-formatted values to list
 *   opts.selected  : Set|null   currently-selected values (null = all selected = no filter)
 *   opts.label     : string     button base label (e.g. "Filter", "Tier")
 *   opts.title     : string     button tooltip
 *   opts.onChange  : fn(Set|null)  called with the new selection (null when ALL are selected,
 *                                  i.e. the column is unfiltered; an empty Set hides every row)
 */
"use strict";

(function () {
  function el(tag, attrs, kids) {
    var n = document.createElement(tag);
    for (var k in attrs || {}) {
      if (k === "text") n.textContent = attrs[k];
      else if (k === "class") n.className = attrs[k];
      else n.setAttribute(k, attrs[k]);
    }
    (kids || []).forEach(function (c) { n.appendChild(c); });
    return n;
  }

  var openPopup = null; // only one popup open at a time
  function closeOpen() {
    if (openPopup) { openPopup.style.display = "none"; openPopup = null; }
  }
  // clicking anywhere outside, pressing Escape, or scrolling closes the open popup (it is
  // position:fixed so it cannot follow a scroll — close it rather than let it drift)
  document.addEventListener("click", closeOpen);
  document.addEventListener("keydown", function (e) { if (e.key === "Escape") closeOpen(); });
  window.addEventListener("scroll", closeOpen, true);
  window.addEventListener("resize", closeOpen);

  function filter(opts) {
    var values = opts.values.slice();
    var label = opts.label || "Filter";
    var sel = opts.selected ? new Set(opts.selected) : new Set(values); // start: all selected
    // a saved selection may name values no longer present; keep only the live ones
    sel.forEach(function (v) { if (values.indexOf(v) < 0) sel.delete(v); });

    var wrap = el("span", { class: "sf-filter" });
    var btn = el("button", { type: "button", class: "sf-filter-btn", title: opts.title || "Filter this column" });
    var popup = el("div", { class: "sf-filter-pop" });
    popup.style.display = "none";
    popup.addEventListener("click", function (e) { e.stopPropagation(); });

    function active() { return sel.size !== values.length; } // a strict subset = filtered
    function refreshBtn() {
      btn.textContent = label + (active() ? " (" + sel.size + ")" : "") + " ▾";
      btn.className = "sf-filter-btn" + (active() ? " on" : "");
    }
    function emit() {
      refreshBtn();
      opts.onChange(active() ? new Set(sel) : null);
    }

    var search = el("input", { type: "text", class: "sf-filter-search", placeholder: "search…" });
    var allLink = el("button", { type: "button", class: "sf-link", text: "All" });
    var noneLink = el("button", { type: "button", class: "sf-link", text: "None" });
    var list = el("div", { class: "sf-filter-list" });
    var rows = [];

    values.forEach(function (v) {
      var cb = el("input", { type: "checkbox" });
      cb.checked = sel.has(v);
      cb.addEventListener("change", function () {
        if (cb.checked) sel.add(v); else sel.delete(v);
        emit();
      });
      var lab = el("label", { class: "sf-filter-item" }, [
        cb, document.createTextNode(" " + (v === "" ? "(blank)" : v)),
      ]);
      list.appendChild(lab);
      rows.push({ v: v, lab: lab, cb: cb });
    });

    function visibleRows() {
      return rows.filter(function (r) { return r.lab.style.display !== "none"; });
    }
    search.addEventListener("input", function () {
      var q = search.value.trim().toLowerCase();
      rows.forEach(function (r) {
        r.lab.style.display = (!q || r.v.toLowerCase().indexOf(q) >= 0) ? "" : "none";
      });
    });
    // Select-all / Clear act on the rows currently VISIBLE (so "search + All" is a power move)
    allLink.addEventListener("click", function () {
      visibleRows().forEach(function (r) { r.cb.checked = true; sel.add(r.v); });
      emit();
    });
    noneLink.addEventListener("click", function () {
      visibleRows().forEach(function (r) { r.cb.checked = false; sel.delete(r.v); });
      emit();
    });

    popup.appendChild(search);
    popup.appendChild(el("div", { class: "sf-filter-head" }, [allLink, noneLink]));
    popup.appendChild(list);

    btn.addEventListener("click", function (e) {
      e.stopPropagation();
      var wasOpen = popup.style.display !== "none";
      closeOpen();
      if (wasOpen) return;
      // position:fixed off the button rect so the popup escapes the grid's overflow clipping
      var r = btn.getBoundingClientRect();
      popup.style.position = "fixed";
      popup.style.top = Math.round(r.bottom + 2) + "px";
      popup.style.left = Math.round(r.left) + "px";
      popup.style.display = "block";
      openPopup = popup;
      search.value = "";
      rows.forEach(function (rr) { rr.lab.style.display = ""; });
      search.focus();
    });

    refreshBtn();
    wrap.appendChild(btn);
    wrap.appendChild(popup);
    return wrap;
  }

  window.SFChecklist = { filter: filter, close: closeOpen };
})();
