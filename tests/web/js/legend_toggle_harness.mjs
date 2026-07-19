// Node-driven unit harness for the SFLegend series-toggle module (ADR-0276).
//
// Boots legend_toggle.js against a minimal DOM stub, then drives its delegated click handler to
// assert: a legend click hides/shows the matching series within its own scope; scopes are
// independent; show-all/none flips every series; and — the load-bearing part for animated charts —
// re-applying after a redraw keeps the hidden set. Exit 0 = all assertions hold.
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

// ---- a tiny DOM good enough for the module: elements know their attrs, children, style, closest,
// classList, and querySelectorAll over the subtree. Matching is limited to the selectors the module
// uses: "[data-series]", "[data-series-toggle]", "[data-series-all]", and the comma union.
function El(tag, attrs) {
  const a = attrs || {};
  const el = {
    tag,
    attrs: { ...a },
    children: [],
    parentNode: null,
    style: {},
    classList: {
      _s: new Set(),
      add(c) { this._s.add(c); },
      remove(c) { this._s.delete(c); },
      toggle(c, on) { if (on) this._s.add(c); else this._s.delete(c); },
      contains(c) { return this._s.has(c); },
    },
    getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; },
    setAttribute(k, v) { this.attrs[k] = String(v); },
    appendChild(c) { c.parentNode = this; this.children.push(c); return c; },
    _matches(sel) {
      return sel.split(",").some((oneRaw) => {
        const one = oneRaw.trim();
        const m = one.match(/^\[([a-z-]+)\]$/);
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
  return { observe() {}, disconnect() {}, _cb: cb };
};
globalThis.window = globalThis;
globalThis.document = {
  addEventListener(evName, fn) { if (evName === "click") docClickHandler = fn; },
};

new Function(src)(); // boot → installs the delegated click listener + window.SFLegend

// ---- build two independent charts, each: a scope with a legend (2 toggles + an all control) and
// two series elements tagged data-series.
function makeChart(k1, k2) {
  const scope = El("div"); // the ".chart" wrap
  const svg = El("svg");
  const s1 = El("polyline", { "data-series": k1 });
  const s2 = El("polyline", { "data-series": k2 });
  svg.appendChild(s1); svg.appendChild(s2);
  const legend = El("div");
  const i1 = El("span", { "data-series-toggle": k1 });
  const i2 = El("span", { "data-series-toggle": k2 });
  const all = El("button", { "data-series-all": "1" });
  legend.appendChild(i1); legend.appendChild(i2); legend.appendChild(all);
  scope.appendChild(svg); scope.appendChild(legend);
  return { scope, s1, s2, i1, i2, all };
}

const A = makeChart("Tasks", "Milestones");
const B = makeChart("Tasks", "Milestones"); // same keys, different chart → must stay independent

// 1. click a legend entry hides that series (and only within its own scope)
A.i1.click();
check("clicking a legend entry hides its series", A.s1.style.display === "none");
check("the other series in the same chart stays visible", A.s2.style.display === "");
check("a same-key series in ANOTHER chart is unaffected", B.s1.style.display !== "none");
check("the toggled entry reflects aria-pressed=false", A.i1.getAttribute("aria-pressed") === "false");
check("the toggled entry gets the legend-off class", A.i1.classList.contains("legend-off"));

// 2. clicking again shows it back
A.i1.click();
check("clicking again restores the series", A.s1.style.display === "");
check("aria-pressed returns to true", A.i1.getAttribute("aria-pressed") === "true");

// 3. show-all/none: nothing hidden → hide all; again → show all
A.all.click();
check("all/none hides every series when none were hidden", A.s1.style.display === "none" && A.s2.style.display === "none");
A.all.click();
check("all/none shows every series when some were hidden", A.s1.style.display === "" && A.s2.style.display === "");

// 4. animation redraw persistence: hide a series, then simulate a frame redraw that REPLACES the
// series element with a fresh (unstyled) one, then re-apply — the fresh element must be hidden too.
B.i2.click();
check("series hidden before redraw", B.s2.style.display === "none");
const fresh = El("polyline", { "data-series": "Milestones" }); // a new frame's element, display=""
B.scope.children[0].appendChild(fresh); // add into the svg
window.SFLegend.apply(B.scope); // the MutationObserver would call this on a real redraw
check("a re-drawn series element inherits the hidden state", fresh.style.display === "none");

if (failures) { console.error(`${failures} failure(s)`); process.exit(1); }
console.log("all SFLegend toggle checks passed");
