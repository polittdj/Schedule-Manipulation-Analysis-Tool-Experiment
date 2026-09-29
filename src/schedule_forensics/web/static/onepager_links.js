// onepager_links.js — the operator's LOGIC LINKS on both One-Pager slides (ADR-0539).
//
// Two jobs, shared by onepager.js and onepager_compare.js:
//  1. PAINT the links the server routed (reports/onepager_links.py) — each one a halo in the
//     canvas colour, the shaft, the layout's own arrowhead and, for SS / FF / SF, its type tag —
//     ABOVE the items (so a leg that must cross a bar or a label reads as crossing it) and BELOW
//     the red data-date line. Geometry is never computed here, only painted, exactly as the .pptx
//     export paints the same points (reports/pptx.py _logic_links).
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
    var layer = el("g", { class: "op-links-layer" });
    links.forEach(function (ln) {
      var g = el("g", { class: "op-link", "data-pred": ln.pred, "data-succ": ln.succ, "data-kind": ln.kind });
      g.appendChild(el("title", {}, ln.pred_name + " → " + ln.succ_name + " (" + ln.kind + ")"));
      g.appendChild(el("polyline", { points: points(ln.shaft), class: "op-link-halo" }));
      g.appendChild(el("polyline", { points: points(ln.shaft), class: "op-link-line" }));
      g.appendChild(el("polygon", { points: points(ln.head), class: "op-link-head" }));
      if (ln.tag) {
        g.appendChild(el("text", {
          x: ln.tag_x, y: ln.tag_y, "text-anchor": ln.tag_anchor, class: "op-link-tag",
          style: "font-size:" + ln.tag_pt + "px",
        }, ln.tag));
      }
      layer.appendChild(g);
    });
    // beneath the data-date line (SFGantt.dataDateLine's .ch-dd), above everything else
    var dd = svg.querySelector(".ch-dd");
    var before = dd;
    while (before && before.parentNode !== svg) before = before.parentNode;
    if (before) svg.insertBefore(layer, before);
    else svg.appendChild(layer);
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
    return layer;
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

  window.SFOnePagerLinks = { paint: paint, wire: wire };
})();
