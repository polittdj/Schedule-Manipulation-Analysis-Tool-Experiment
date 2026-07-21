// Node harness for SFLegend's STABLE-SCOPE path (ADR-0276, phase 3): charts whose svg is rebuilt
// every animation frame (performance.js / cei.js) draw the legend INSIDE that svg, so the
// smallest-containing ancestor would be the transient svg and the hidden set would die on redraw.
// Those charts mark their persistent host with data-series-scope; scopeFor must return that host, and
// a redraw (a real, firing MutationObserver) must re-hide the freshly drawn series. This complements
// legend_toggle_harness.mjs (which covers the trend.js legend-OUTSIDE-svg fallback). Exit 0 = pass.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const src = readFileSync(
  join(here, "../../../src/schedule_forensics/web/static/legend_toggle.js"),
  "utf8",
);

let failures = 0;
function check(label, cond) {
  if (!cond) { failures += 1; console.error(`FAIL ${label}`); }
  else console.log(`ok ${label}`);
}

function El(tag, attrs, ns) {
  const a = attrs || {};
  const el = {
    tag,
    namespaceURI: ns || "http://www.w3.org/1999/xhtml",
    attrs: { ...a },
    children: [],
    parentNode: null,
    style: {},
    classList: {
      _s: new Set(),
      add(c) { this._s.add(c); }, remove(c) { this._s.delete(c); },
      toggle(c, on) { if (on) this._s.add(c); else this._s.delete(c); },
      contains(c) { return this._s.has(c); },
    },
    getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; },
    setAttribute(k, v) { this.attrs[k] = String(v); },
    appendChild(c) {
      c.parentNode = this;
      this.children.push(c);
      // fire any observer watching this node or an ancestor (subtree childList) — models the real
      // MutationObserver the module attaches, so a redraw actually re-applies the hidden set.
      let n = this;
      while (n) { if (n._obs) n._obs.forEach((o) => o._fire()); n = n.parentNode; }
      return c;
    },
    set textContent(v) {
      if (v === "" || v === null) { this.children.forEach((c) => (c.parentNode = null)); this.children = []; }
      this._text = v;
    },
    get textContent() { return this._text || ""; },
    _matches(sel) {
      return sel.split(",").some((oneRaw) => {
        const m = oneRaw.trim().match(/^\[([a-z-]+)\]$/);
        return m ? m[1] in this.attrs : false;
      });
    },
    _walk(out) { for (const c of this.children) { out.push(c); c._walk(out); } },
    querySelector(sel) { const r = []; this._walk(r); return r.find((e) => e._matches(sel)) || null; },
    querySelectorAll(sel) { const r = []; this._walk(r); return r.filter((e) => e._matches(sel)); },
    closest(sel) { let n = this; while (n) { if (n._matches && n._matches(sel)) return n; n = n.parentNode; } return null; },
    click() { docClick({ target: this }); },
  };
  return el;
}

let docClickHandler = null;
function docClick(ev) { if (docClickHandler) docClickHandler(ev); }
globalThis.MutationObserver = function (cb) {
  return {
    _cb: cb,
    _target: null,
    observe(t) { this._target = t; if (!t._obs) t._obs = []; t._obs.push(this); },
    disconnect() { if (this._target && this._target._obs) { const i = this._target._obs.indexOf(this); if (i >= 0) this._target._obs.splice(i, 1); } },
    _fire() { this._cb(); },
  };
};
globalThis.window = globalThis;
globalThis.document = { addEventListener(evName, fn) { if (evName === "click") docClickHandler = fn; } };

new Function(src)(); // boot → installs the delegated click listener + window.SFLegend

const SVG = "http://www.w3.org/2000/svg";

// host (stable, marked data-series-scope) > svg (rebuilt each frame) > [series + legend]. redraw()
// wipes the svg and builds a fresh one exactly like frame()/render() do.
function makeChart(k1, k2) {
  const host = El("div", { "data-series-scope": "1" });
  function build() {
    const svg = El("svg", {}, SVG);
    const s1 = El("path", { "data-series": k1 }, SVG);
    const s2 = El("path", { "data-series": k2 }, SVG);
    const g1 = El("g", { "data-series-toggle": k1 }, SVG);
    const g2 = El("g", { "data-series-toggle": k2 }, SVG);
    const all = El("g", { "data-series-all": "1" }, SVG);
    svg.appendChild(s1); svg.appendChild(s2); svg.appendChild(g1); svg.appendChild(g2); svg.appendChild(all);
    host.appendChild(svg);
    return { svg, s1, s2, g1, g2, all };
  }
  let parts = build();
  return { host, get parts() { return parts; }, redraw() { host.textContent = ""; parts = build(); } };
}

const A = makeChart("Tasks", "Milestones");
const B = makeChart("Tasks", "Milestones"); // same keys, different marked host → independent

// scopeFor of a legend item INSIDE the svg must resolve to the STABLE marked host, not the svg
check("scopeFor(item-in-svg) resolves to the marked host", window.SFLegend.scopeFor(A.parts.g1) === A.host);
check("the resolved scope is NOT the transient svg", window.SFLegend.scopeFor(A.parts.g1) !== A.parts.svg);

// click hides the series; a same-key series in the other marked host is unaffected
A.parts.g1.click();
check("clicking a legend entry hides its series", A.parts.s1.style.display === "none");
check("the other series in the same chart stays visible", A.parts.s2.style.display === "");
check("a same-key series in another marked host is unaffected", B.parts.s1.style.display !== "none");

// THE load-bearing part: a full svg replacement (animation frame) must keep the series hidden, via
// the firing observer re-applying the hidden set to the freshly drawn element.
A.redraw();
check("after an svg-replacing redraw the fresh series stays hidden", A.parts.s1.style.display === "none");
check("the untouched series is visible after redraw", A.parts.s2.style.display === "");

// show it back through the (new) legend entry, then all/none over the marked host
A.parts.g1.click();
check("clicking again restores the series across the redraw", A.parts.s1.style.display === "");
A.parts.all.click();
check("all/none hides every series in the marked host", A.parts.s1.style.display === "none" && A.parts.s2.style.display === "none");
check("all/none survives a redraw too", (function () { A.redraw(); return A.parts.s1.style.display === "none" && A.parts.s2.style.display === "none"; })());
A.parts.all.click();
check("all/none shows every series again", A.parts.s1.style.display === "" && A.parts.s2.style.display === "");

if (failures) { console.error(`${failures} failure(s)`); process.exit(1); }
console.log("all SFLegend stable-scope checks passed");
