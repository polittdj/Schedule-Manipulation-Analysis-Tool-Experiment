// onepager_links.js — the operator's LOGIC LINKS on both One-Pager slides (ADR-0539).
//
// Two jobs, shared by onepager.js and onepager_compare.js:
//  1. PAINT the links the server routed (reports/onepager_links.py) in the Console z-order
//     (ADR-0543): lanes and grid → every link's SHAFT → the items (bars, diamonds, ghosts, tags
//     and their haloed labels) → every link's ARROWHEAD and type tag → the red data-date line →
//     the legend → the pick rings. A shaft runs UNDER whatever bar or name it passes, so the
//     item stays readable and no route is ever "flagged"; the head and its tag sit over the
//     items. Geometry is never computed here, only painted, exactly as the .pptx export paints
//     the same points in the same order (reports/pptx.py _link_shafts / _link_heads).
//  2. PICK two items by clicking them: the first click fills the page's "From" select, the second
//     its "To" select, and both are ringed and tagged FROM / TO on the slide. The selects ARE the
//     form — they work with no script at all, and they are the keyboard path — so this only saves
//     hunting through two long lists. Nothing is posted from here: the operator presses "Add
//     logic link".
//
// Strict CSP (script-src 'self'): no inline handlers; everything is attached here.
(function () {
  "use strict";
  var SVG = "http://www.w3.org/2000/svg";
  function el(tag, attrs, text) {
    var n = document.createElementNS(SVG, tag);
    for (var k in attrs) if (attrs[k] !== null && attrs[k] !== undefined) n.setAttribute(k, attrs[k]);
    if (text !== null && text !== undefined) n.textContent = text;
    return n;
  }
  function points(a) {
    return a.map(function (p) { return p[0] + "," + p[1]; }).join(" ");
  }

  // ── 1. paint ──
  function paint(svg, L) {
    var links = L.links || [];
    var shafts = el("g", { class: "op-links-layer" }), heads = el("g", { class: "op-link-heads" });
    links.forEach(function (ln) {
      var name = ln.pred_name + " → " + ln.succ_name + " (" + ln.kind + ")";
      var g = el("g", { class: "op-link", "data-pred": ln.pred, "data-succ": ln.succ, "data-kind": ln.kind });
      g.appendChild(el("title", {}, name));
      g.appendChild(el("polyline", { points: points(ln.shaft), class: "op-link-line" }));
      shafts.appendChild(g);
      var h = el("g", { class: "op-link-arrow", "data-pred": ln.pred, "data-succ": ln.succ, "data-kind": ln.kind });
      h.appendChild(el("title", {}, name));
      h.appendChild(el("polygon", { points: points(ln.head), class: "op-link-head" }));
      if (ln.tag) { // haloed like the labels: a stroke in the slide's ground, 0.42 x its size
        h.appendChild(el("text", {
          x: ln.tag_x, y: ln.tag_y, "text-anchor": ln.tag_anchor, class: "op-link-tag",
          style: "font-size:" + ln.tag_pt + "px;stroke-width:" + 0.42 * ln.tag_pt + "px",
        }, ln.tag));
      }
      heads.appendChild(h);
    });
    // the shafts go UNDER the first item, the heads OVER the last one (and so under the
    // data-date line, which the painters draw right after the items)
    var items = svg.querySelectorAll(".op-item, .opc-item");
    if (items.length) {
      svg.insertBefore(shafts, items[0]);
      svg.insertBefore(heads, items[items.length - 1].nextSibling);
    } else {
      svg.appendChild(shafts);
      svg.appendChild(heads);
    }
    // the legend's "Logic link" symbol: its label is painted by the page's own legend loop
    (L.legend || []).forEach(function (e) {
      if (e.kind !== "link") return;
      var cy = e.y - 2.5, g = el("g", { class: "op-legend-link" });
      g.appendChild(el("line", { x1: e.x, y1: cy, x2: e.x + 7.4, y2: cy, class: "op-link-line" }));
      g.appendChild(el("polygon", {
        points: (e.x + 10) + "," + cy + " " + (e.x + 7.4) + "," + (cy - 1.3) + " " + (e.x + 7.4) + "," + (cy + 1.3),
        class: "op-link-head",
      }));
      svg.appendChild(g);
    });
    return shafts;
  }

  // ── 2. pick two items ──
  // ONE delegated listener on the slide's HOST (#opHost / #opcHost): it survives ⛶ ENLARGE and a
  // repaint, which replaces the SVG. The pick is shown by SHAPE and TEXT, never colour alone: a
  // dashed ring tagged FROM, a solid ring tagged TO (in two themes the focus and accent hues equal
  // the warning hue). The rings are an overlay, hidden in print. Clicking the From item again
  // un-picks it; a click after a full pair starts a new one.
  function ring(svg, g, tag) {
    var shape = g.querySelector(".op-bar, .op-diamond");
    if (!shape || !shape.getBBox) return;
    var b = shape.getBBox(), pad = 1.6, layer = svg.querySelector("g.op-pick");
    if (!layer) { layer = el("g", { class: "op-pick" }); svg.appendChild(layer); }
    layer.appendChild(el("rect", {
      x: b.x - pad, y: b.y - pad, width: b.width + 2 * pad, height: b.height + 2 * pad, rx: 1.5,
      class: "op-pick-ring op-pick-" + tag.toLowerCase(),
    }));
    layer.appendChild(el("text", { x: b.x - pad, y: b.y - pad - 1, class: "op-pick-tag" }, tag));
  }
  function wire(host, prefix) {
    var from = document.getElementById(prefix + "LinkFrom"),
      to = document.getElementById(prefix + "LinkTo"),
      hint = document.getElementById(prefix + "LinkHint");
    if (!host || !from || !to) return;
    function svg() { return host.querySelector("svg"); }
    function label(sel) {
      var o = sel.options[sel.selectedIndex];
      return o && o.value ? o.getAttribute("title") || o.textContent : "";
    }
    function has(sel, value) {
      for (var i = 0; i < sel.options.length; i++) if (sel.options[i].value === value) return true;
      return false;
    }
    function mark() {
      var s = svg();
      if (!s) return;
      s.classList.add("op-pickable");
      var old = s.querySelector("g.op-pick");
      if (old) old.parentNode.removeChild(old);
      Array.prototype.forEach.call(s.querySelectorAll("[data-key]"), function (g) {
        var k = g.getAttribute("data-key");
        if (k && k === from.value) ring(s, g, "FROM");
        if (k && k === to.value) ring(s, g, "TO");
      });
      if (!hint) return;
      if (from.value && to.value) hint.textContent = "From " + label(from) + " to " + label(to) + " — choose the type and press Add logic link.";
      else if (from.value) hint.textContent = "From " + label(from) + " — now pick the successor.";
      else hint.textContent = "";
    }
    host.addEventListener("click", function (ev) {
      var g = ev.target && ev.target.closest ? ev.target.closest("[data-key]") : null;
      var key = g && g.getAttribute("data-key");
      if (!key || !has(from, key)) return; // not an item a link may join (e.g. REMOVED)
      if (key === from.value && !to.value) {
        from.value = "";
      } else if (!from.value || to.value) {
        from.value = key;
        to.value = "";
      } else {
        to.value = key;
      }
      mark();
    });
    from.addEventListener("change", mark);
    to.addEventListener("change", mark);
    mark();
  }

  // ── 3. land clear of a sticky header ──
  // An add / remove lands on #opLinks / #opcLinks, where its result renders. The stylesheet's
  // scroll-margin clears no header; daylight's page header is a STICKY top bar whose height
  // follows its wrapping nav (224-458 px measured), so the block — result and all — landed under
  // it (review UIP-1). On landing, measure a sticky / fixed header spanning the top of the page
  // (never the dark views' left rail) and land the block just below it.
  function land() {
    var id = (location.hash || "").slice(1);
    if (id !== "opLinks" && id !== "opcLinks") return;
    var block = document.getElementById(id), head = document.querySelector("header");
    if (!block || !head) return;
    var pos = getComputedStyle(head).position, r = head.getBoundingClientRect();
    if ((pos !== "sticky" && pos !== "fixed") || r.width < window.innerWidth / 2) return;
    block.style.scrollMarginTop = Math.ceil(r.height) + 12 + "px";
    block.scrollIntoView({ block: "start" });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", land);
  else land();

  window.SFOnePagerLinks = { paint: paint, wire: wire };
})();
